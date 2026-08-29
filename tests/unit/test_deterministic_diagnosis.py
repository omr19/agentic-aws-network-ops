"""Focused offline tests for deterministic Phase 7 diagnosis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_aws_network_ops.diagnostics.deterministic import diagnose

ROOT = Path(__file__).parents[2]
BASE = {
    "schema_version": "1.0.0",
    "correlation_id": "corr-phase7-0001",
    "observed_at": "2026-08-29T01:00:00Z",
    "region": "eu-west-1",
    "evidence_completeness": "complete",
}


def evidence(**parts: Any) -> dict[str, Any]:
    return {**BASE, **parts}


def reachability(path_found: bool | None, status: str = "succeeded", *codes: str) -> dict[str, Any]:
    return {"status": status, "path_found": path_found, "explanation_codes": list(codes)}


def fixture(name: str) -> dict[str, Any]:
    path = ROOT / "docs/evidence/phase-6" / f"{name}.json"
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_healthy_evidence_has_no_false_positive() -> None:
    result = diagnose(evidence(reachability=reachability(True)))
    assert result["status"] == "no_finding"
    assert result["data"]["classification"] == "healthy"
    assert result["data"]["root_cause"] is None
    assert result["data"]["recommendations"] == []


@pytest.mark.parametrize(
    ("classification", "root_cause", "configuration", "codes"),
    [
        (
            "security_group_mismatch",
            "destination_security_group_ingress_does_not_match_source",
            {
                "security_group": {
                    "expected_source_cidr": "10.10.0.0/16",
                    "observed_source_cidr": "192.0.2.0/32",
                }
            },
            ("ENI_SG_RULES_MISMATCH",),
        ),
        (
            "missing_route",
            "missing_source_to_destination_peering_route",
            {
                "routes": {
                    "source_to_destination_present": False,
                    "destination_to_source_present": True,
                }
            },
            ("NO_ROUTE_TO_DESTINATION",),
        ),
        (
            "nacl_restriction",
            "destination_nacl_denies_tcp_443_ingress",
            {"nacl": {"deny_rule_present": True, "deny_rule_number": 90}},
            ("SUBNET_ACL_RESTRICTION",),
        ),
        (
            "peering_path_dns_failure",
            "peering_path_disabled_both_route_directions_and_dns",
            {
                "peering": {
                    "connection_status": "active",
                    "source_to_destination_present": False,
                    "destination_to_source_present": False,
                    "requester_dns_resolution": False,
                    "accepter_dns_resolution": False,
                }
            },
            ("NO_ROUTE_TO_DESTINATION",),
        ),
    ],
)
def test_each_failure_class_is_deterministic(
    classification: str, root_cause: str, configuration: dict[str, Any], codes: tuple[str, ...]
) -> None:
    result = diagnose(
        evidence(reachability=reachability(False, "succeeded", *codes), configuration=configuration)
    )
    assert result["status"] == "unreachable"
    assert result["data"]["classification"] == classification
    assert result["data"]["root_cause"] == root_cause
    assert result["data"]["observed_facts"]
    assert result["data"]["recommendations"]
    assert not set(result["data"]["recommendations"]) & set(result["data"]["observed_facts"])


def test_tracked_phase6_fixture_is_usable_for_peering() -> None:
    summary = fixture("broken-peering")
    broken = summary["observed_broken_state"]
    result = diagnose(
        evidence(
            reachability={
                "status": "succeeded",
                "path_found": False,
                "explanation_codes": ["NO_ROUTE_TO_DESTINATION"],
            },
            configuration={
                "routes": {
                    "source_to_destination_present": broken["source_to_destination_routes_present"],
                    "destination_to_source_present": broken["destination_to_source_routes_present"],
                },
                "peering": {
                    "connection_status": broken["peering_status"],
                    "source_to_destination_present": False,
                    "destination_to_source_present": False,
                    "requester_dns_resolution": broken["requester_dns_resolution"],
                    "accepter_dns_resolution": broken["accepter_dns_resolution"],
                },
            },
        )
    )
    assert result["data"]["classification"] == "peering_path_dns_failure"


def test_incomplete_evidence_makes_no_root_cause_claim() -> None:
    result = diagnose(evidence(evidence_completeness="partial", reachability=reachability(False)))
    assert result["status"] == "no_finding"
    assert result["data"]["classification"] == "indeterminate"
    assert result["data"]["root_cause"] is None
    assert result["errors"][0]["code"] == "INCOMPLETE_EVIDENCE"


def test_conflicting_healthy_reachability_and_blocker_is_rejected() -> None:
    result = diagnose(
        evidence(
            reachability=reachability(True),
            configuration={"nacl": {"deny_rule_present": True, "deny_rule_number": 90}},
        )
    )
    assert result["status"] == "invalid_request"
    assert result["data"]["root_cause"] is None
    assert result["errors"][0]["code"] == "CONFLICTING_EVIDENCE"


def test_multiple_blockers_are_not_silently_selected() -> None:
    result = diagnose(
        evidence(
            reachability=reachability(False),
            configuration={
                "security_group": {
                    "expected_source_cidr": "10.10.0.0/16",
                    "observed_source_cidr": "192.0.2.0/32",
                },
                "nacl": {"deny_rule_present": True, "deny_rule_number": 90},
            },
        )
    )
    assert result["status"] == "invalid_request"
    assert result["errors"][0]["code"] == "CONFLICTING_EVIDENCE"


def test_repeated_runs_are_identical_except_no_generated_timestamp() -> None:
    input_evidence = evidence(
        reachability=reachability(False, "succeeded", "NO_ROUTE_TO_DESTINATION"),
        configuration={
            "routes": {
                "source_to_destination_present": False,
                "destination_to_source_present": True,
            }
        },
    )
    assert diagnose(input_evidence) == diagnose(input_evidence)


def normalized_from_summary(name: str) -> dict[str, Any]:
    summary = fixture(name)
    if name == "broken-sg":
        change = summary["terraform"]["injected_change"]
        return evidence(
            reachability={
                "status": "succeeded",
                "path_found": False,
                "explanation_codes": summary["reachability_analyzer"]["explanation_codes"],
            },
            configuration={
                "security_group": {
                    "expected_source_cidr": change["from"],
                    "observed_source_cidr": change["to"],
                }
            },
        )
    if name == "broken-route":
        return evidence(
            reachability={
                "status": "succeeded",
                "path_found": False,
                "explanation_codes": summary["reachability_analyzer"]["explanation_codes"],
            },
            configuration={
                "routes": {
                    "source_to_destination_present": False,
                    "destination_to_source_present": True,
                }
            },
        )
    if name == "broken-nacl":
        rule = summary["terraform"]["injected_change"]
        return evidence(
            reachability={
                "status": "succeeded",
                "path_found": False,
                "explanation_codes": summary["reachability_analyzer"]["broken_explanation_codes"],
            },
            configuration={
                "nacl": {"deny_rule_present": True, "deny_rule_number": rule["rule_number"]}
            },
        )
    if name == "broken-peering":
        broken = summary["observed_broken_state"]
        return evidence(
            reachability={
                "status": "succeeded",
                "path_found": False,
                "explanation_codes": summary["broken_analysis"]["explanation_codes"],
            },
            configuration={
                "peering": {
                    "connection_status": broken["peering_status"],
                    "source_to_destination_present": False,
                    "destination_to_source_present": False,
                    "requester_dns_resolution": broken["requester_dns_resolution"],
                    "accepter_dns_resolution": broken["accepter_dns_resolution"],
                }
            },
        )
    raise AssertionError(f"unsupported fixture: {name}")


@pytest.mark.parametrize(
    ("fixture_name", "expected_classification"),
    [
        ("broken-sg", "security_group_mismatch"),
        ("broken-route", "missing_route"),
        ("broken-nacl", "nacl_restriction"),
        ("broken-peering", "peering_path_dns_failure"),
    ],
)
def test_tracked_phase6_failure_fixtures_repeatably_map_to_classes(
    fixture_name: str, expected_classification: str
) -> None:
    normalized = normalized_from_summary(fixture_name)
    first = diagnose(normalized)
    second = diagnose(normalized)
    assert first == second
    assert first["data"]["classification"] == expected_classification
    assert first["data"]["root_cause"]
