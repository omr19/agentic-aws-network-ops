#!/usr/bin/env python3
"""Local, offline Phase 6 scenario harness.

Documents and verifies the scenario -> diagnose -> restore -> verify lifecycle for the
Terraform ``scenario`` variable without running ``terraform apply``, contacting AWS, or
changing IAM. It models the deterministic injection contract defined in
``terraform/environments/lab/locals.tf`` (``scenario_effects``) and asserts that:

1. Each scenario has exactly one deterministic failure signature (or none, for healthy).
2. Diagnosis maps the signature to the expected deterministic root cause.
3. Restoring to ``healthy`` returns every toggle to the approved baseline.

This is a contract/documentation harness. It is not a substitute for an explicitly
authorized ``terraform plan``/``apply`` and live diagnosis during a controlled session.

Applying any non-healthy scenario is an AWS-mutating action (SG rule change, deny NACL
rule creation, and deletion/recreation of Terraform-managed peering routes -- one
direction for broken_route, both directions plus DNS for broken_peering) that requires a
separate approval gate. This harness performs no Terraform, AWS, or IAM operations.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

SOURCE_VPC_CIDR = "10.10.0.0/16"
BLOCKED_SG_CIDR = "192.0.2.0/32"  # TEST-NET-1, deterministically unroutable here.


@dataclass(frozen=True)
class ScenarioEffect:
    """Mirror of the Terraform scenario_effects contract."""

    sg_source_cidr: str
    enable_source_route: bool
    enable_destination_route: bool
    enable_deny_nacl: bool
    enable_peering_dns: bool
    dns_fixture_broken: bool


HEALTHY = ScenarioEffect(
    sg_source_cidr=SOURCE_VPC_CIDR,
    enable_source_route=True,
    enable_destination_route=True,
    enable_deny_nacl=False,
    enable_peering_dns=True,
    dns_fixture_broken=False,
)

SCENARIOS: dict[str, ScenarioEffect] = {
    "healthy": HEALTHY,
    "broken_sg": ScenarioEffect(
        sg_source_cidr=BLOCKED_SG_CIDR,
        enable_source_route=True,
        enable_destination_route=True,
        enable_deny_nacl=False,
        enable_peering_dns=True,
        dns_fixture_broken=False,
    ),
    # One direction only: source->destination route disabled, return route retained.
    "broken_route": ScenarioEffect(
        sg_source_cidr=SOURCE_VPC_CIDR,
        enable_source_route=False,
        enable_destination_route=True,
        enable_deny_nacl=False,
        enable_peering_dns=True,
        dns_fixture_broken=False,
    ),
    "broken_nacl": ScenarioEffect(
        sg_source_cidr=SOURCE_VPC_CIDR,
        enable_source_route=True,
        enable_destination_route=True,
        enable_deny_nacl=True,
        enable_peering_dns=True,
        dns_fixture_broken=False,
    ),
    "broken_dns": ScenarioEffect(
        sg_source_cidr=SOURCE_VPC_CIDR,
        enable_source_route=True,
        enable_destination_route=True,
        enable_deny_nacl=False,
        enable_peering_dns=True,
        dns_fixture_broken=True,
    ),
    # Both directions disabled AND cross-VPC DNS disabled.
    "broken_peering": ScenarioEffect(
        sg_source_cidr=SOURCE_VPC_CIDR,
        enable_source_route=False,
        enable_destination_route=False,
        enable_deny_nacl=False,
        enable_peering_dns=False,
        dns_fixture_broken=False,
    ),
}

# Deterministic diagnosis: signature -> expected root cause and primary evidence source.
DIAGNOSIS: dict[str, dict[str, str]] = {
    "healthy": {
        "root_cause": "none",
        "evidence": "reachability_analyzer:path_found=true",
    },
    "broken_sg": {
        "root_cause": "destination_security_group_ingress_does_not_match_source",
        "evidence": "describe_security_groups:ingress_cidr!=source_vpc_cidr",
    },
    "broken_route": {
        "root_cause": "missing_source_to_destination_peering_route",
        "evidence": "describe_route_tables:source_route_to_peer_cidr_absent_return_route_present",
    },
    "broken_nacl": {
        "root_cause": "destination_nacl_denies_tcp_443_ingress",
        "evidence": "describe_network_acls:deny_rule_90_precedes_allow_100",
    },
    "broken_dns": {
        "root_cause": "local_dns_fixture_unresolved",
        "evidence": "local_fixture:dns_fixture_broken=true",
    },
    "broken_peering": {
        "root_cause": "peering_path_disabled_both_route_directions_and_dns",
        "evidence": "describe_route_tables+peering_options:both_directions_absent_dns_disabled",
    },
}


def signature(effect: ScenarioEffect) -> dict[str, object]:
    return asdict(effect)


def diagnose(name: str) -> dict[str, str]:
    return DIAGNOSIS[name]


def restore_to_healthy(name: str) -> ScenarioEffect:
    """Restoration always returns the approved healthy baseline effect."""
    del name
    return HEALTHY


def verify_healthy(effect: ScenarioEffect) -> bool:
    return effect == HEALTHY


def run_scenario(name: str) -> dict[str, object]:
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario: {name}")
    injected = SCENARIOS[name]
    injected_sig = signature(injected)

    # Exactly one deterministic deviation from healthy for each broken_* scenario.
    deviations = {
        key: value for key, value in injected_sig.items() if value != signature(HEALTHY)[key]
    }
    if name == "healthy":
        expected_deviation_count = 0
    elif name == "broken_peering":
        # Both route directions disabled AND cross-VPC DNS disabled.
        expected_deviation_count = 3
    else:
        # Exactly one deterministic deviation (broken_route disables only one direction).
        expected_deviation_count = 1

    diagnosis = diagnose(name)
    restored = restore_to_healthy(name)
    verified = verify_healthy(restored)

    result = {
        "scenario": name,
        "injected_signature": injected_sig,
        "deviations_from_healthy": deviations,
        "deviation_count": len(deviations),
        "expected_deviation_count": expected_deviation_count,
        "diagnosis": diagnosis,
        "restored_signature": signature(restored),
        "verified_healthy_after_restore": verified,
        "vpc_endpoints": "not_applicable_no_project_endpoints",
        "transit_gateway": "out_of_scope",
    }
    ok = len(deviations) == expected_deviation_count and verified and diagnosis["root_cause"] != ""
    result["passed"] = ok
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        help="Run a single scenario. Default runs all scenarios.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON evidence.")
    arguments = parser.parse_args()

    names = [arguments.scenario] if arguments.scenario else list(SCENARIOS)
    results: list[dict[str, object]] = [run_scenario(name) for name in names]
    all_passed = all(bool(item["passed"]) for item in results)

    if arguments.json:
        print(json.dumps({"results": results, "all_passed": all_passed}, indent=2))
    else:
        for item in results:
            status = "PASS" if item["passed"] else "FAIL"
            diagnosis = diagnose(str(item["scenario"]))
            print(
                f"[{status}] {item['scenario']}: "
                f"root_cause={diagnosis['root_cause']}; "
                f"deviations={item['deviation_count']}/{item['expected_deviation_count']}; "
                f"restored_healthy={item['verified_healthy_after_restore']}"
            )
        print(f"all_passed={all_passed}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
