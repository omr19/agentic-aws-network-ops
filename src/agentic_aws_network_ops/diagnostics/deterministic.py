"""Pure deterministic diagnosis over normalized diagnostic evidence.

This module performs no AWS, Terraform, IAM, deployment, or remediation work. It
correlates an existing Reachability Analyzer result with normalized configuration
facts and returns observed facts separately from bounded recommendations.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

TOOL_NAME: Final = "deterministic_diagnosis"
SCHEMA_VERSION: Final = "1.0.0"

_FAILURES: Final = {
    "security_group_mismatch": (
        "destination_security_group_ingress_does_not_match_source",
        "Restore the destination TCP/443 ingress rule to the approved source CIDR.",
    ),
    "missing_route": (
        "missing_source_to_destination_peering_route",
        "Restore the missing peering route direction from the approved Terraform baseline.",
    ),
    "nacl_restriction": (
        "destination_nacl_denies_tcp_443_ingress",
        "Remove the temporary deny rule and preserve the approved NACL rule ordering.",
    ),
    "peering_path_dns_failure": (
        "peering_path_disabled_both_route_directions_and_dns",
        "Restore both peering route directions and re-enable cross-VPC DNS resolution.",
    ),
}


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _required_string(data: Mapping[str, object], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _required_bool(data: Mapping[str, object], field: str) -> bool:
    value = data.get(field)
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value


def _base_result(
    evidence: Mapping[str, object],
    *,
    status: str,
    completeness: str,
    facts: list[str],
    classification: str,
    root_cause: str | None,
    recommendations: list[str],
    limitations: list[str],
    errors: list[dict[str, object]],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "status": status,
        "correlation_id": str(evidence.get("correlation_id", "invalid-request")),
        "observed_at": str(evidence.get("observed_at", "")),
        "region": str(evidence.get("region", "unknown")),
        "authorization": {"decision": "allowed", "missing_actions": []},
        "evidence_completeness": completeness,
        "evidence": [{"source": "normalized_evidence", "fact": fact} for fact in facts],
        "limitations": limitations,
        "errors": errors,
        "data": {
            "classification": classification,
            "root_cause": root_cause,
            "observed_facts": facts,
            "recommendations": recommendations,
        },
    }


def _invalid(message: str, evidence: Mapping[str, object] | None = None) -> dict[str, Any]:
    source = evidence or {}
    return _base_result(
        source,
        status="invalid_request",
        completeness="none",
        facts=[],
        classification="indeterminate",
        root_cause=None,
        recommendations=[],
        limitations=["No network root cause can be concluded from invalid evidence."],
        errors=[{"code": "INVALID_NORMALIZED_EVIDENCE", "message": message, "retryable": False}],
    )


def diagnose(evidence: Mapping[str, object]) -> dict[str, Any]:
    """Return a deterministic diagnosis for one normalized evidence record.

    A root cause is emitted only when the reachability result is complete and the
    configuration facts provide exactly one supported failure signature. Conflicts and
    incomplete evidence return no root-cause claim.
    """

    try:
        schema_version = _required_string(evidence, "schema_version")
        if schema_version != SCHEMA_VERSION:
            raise ValueError("schema_version must be 1.0.0")
        _required_string(evidence, "correlation_id")
        _required_string(evidence, "region")
        _required_string(evidence, "observed_at")
        completeness = _required_string(evidence, "evidence_completeness")
        if completeness not in {"complete", "partial"}:
            raise ValueError("evidence_completeness must be complete or partial")
        reachability = _mapping(evidence.get("reachability"), "reachability")
        reachability_status = _required_string(reachability, "status")
        path_found = reachability.get("path_found")
        if path_found is not None and not isinstance(path_found, bool):
            raise ValueError("reachability.path_found must be boolean or null")
        explanations = reachability.get("explanation_codes", [])
        if not isinstance(explanations, list) or not all(
            isinstance(code, str) and code for code in explanations
        ):
            raise ValueError("reachability.explanation_codes must be a list of strings")
    except (TypeError, ValueError) as error:
        return _invalid(str(error), evidence)

    facts = [
        f"Reachability Analyzer status={reachability_status}; path_found={path_found}",
        f"Reachability Analyzer explanation codes={','.join(explanations) or 'none'}",
    ]
    if completeness != "complete" or reachability_status != "succeeded" or path_found is None:
        return _base_result(
            evidence,
            status="no_finding",
            completeness="partial",
            facts=facts,
            classification="indeterminate",
            root_cause=None,
            recommendations=[],
            limitations=[
                "No network root cause can be concluded from incomplete or in-progress evidence."
            ],
            errors=[
                {
                    "code": "INCOMPLETE_EVIDENCE",
                    "message": (
                        "A succeeded Reachability Analyzer result and complete "
                        "configuration evidence are required."
                    ),
                    "retryable": False,
                }
            ],
        )

    configuration = _mapping(evidence.get("configuration", {}), "configuration")
    blockers: list[tuple[str, str]] = []

    security_group = configuration.get("security_group")
    if security_group is not None:
        sg = _mapping(security_group, "configuration.security_group")
        expected = _required_string(sg, "expected_source_cidr")
        observed = _required_string(sg, "observed_source_cidr")
        if expected != observed:
            facts.append(f"Security-group source CIDR observed={observed}; expected={expected}")
            blockers.append(
                ("security_group_mismatch", "SG ingress CIDR differs from the approved source CIDR")
            )

    routes = configuration.get("routes")
    if routes is not None:
        route_data = _mapping(routes, "configuration.routes")
        source_present = _required_bool(route_data, "source_to_destination_present")
        destination_present = _required_bool(route_data, "destination_to_source_present")
        facts.append(
            f"Peering routes source_to_destination={source_present}; "
            f"destination_to_source={destination_present}"
        )
        if not source_present and destination_present:
            blockers.append(("missing_route", "Source-to-destination peering route is absent"))
        elif not source_present and not destination_present:
            facts.append("Both peering route directions are absent")

    nacl = configuration.get("nacl")
    if nacl is not None:
        nacl_data = _mapping(nacl, "configuration.nacl")
        deny_present = _required_bool(nacl_data, "deny_rule_present")
        if deny_present:
            rule_number = nacl_data.get("deny_rule_number")
            facts.append(f"NACL deny rule present={deny_present}; rule_number={rule_number}")
            blockers.append(
                ("nacl_restriction", "TCP/443 ingress is denied by the destination NACL")
            )

    peering = configuration.get("peering")
    if peering is not None:
        peering_data = _mapping(peering, "configuration.peering")
        connection_status = _required_string(peering_data, "connection_status")
        requester_dns = _required_bool(peering_data, "requester_dns_resolution")
        accepter_dns = _required_bool(peering_data, "accepter_dns_resolution")
        source_present = _required_bool(peering_data, "source_to_destination_present")
        destination_present = _required_bool(peering_data, "destination_to_source_present")
        facts.append(
            f"Peering status={connection_status}; DNS requester={requester_dns}; "
            f"accepter={accepter_dns}"
        )
        if (
            not source_present
            and not destination_present
            and not requester_dns
            and not accepter_dns
        ):
            blockers.append(
                ("peering_path_dns_failure", "Both peering routes and DNS resolution are disabled")
            )

    dns_fixture = configuration.get("dns_fixture")
    if dns_fixture is not None:
        fixture = _mapping(dns_fixture, "configuration.dns_fixture")
        local_only = _required_bool(fixture, "local_only")
        fixture_broken = _required_bool(fixture, "broken")
        facts.append(f"DNS fixture local_only={local_only}; broken={fixture_broken}")
        if fixture_broken and not local_only:
            return _invalid("A broken DNS fixture must be explicitly local_only", evidence)
        if fixture_broken:
            return _base_result(
                evidence,
                status="invalid_request",
                completeness="complete",
                facts=facts,
                classification="indeterminate",
                root_cause=None,
                recommendations=[],
                limitations=[
                    "The local DNS fixture is not an AWS failure class supported by this workflow."
                ],
                errors=[
                    {
                        "code": "UNSUPPORTED_ROOT_CAUSE",
                        "message": "DNS fixture evidence requires a dedicated local adapter.",
                        "retryable": False,
                    }
                ],
            )

    if path_found is True:
        if blockers:
            return _base_result(
                evidence,
                status="invalid_request",
                completeness="complete",
                facts=facts,
                classification="indeterminate",
                root_cause=None,
                recommendations=[],
                limitations=[
                    "Reachability Analyzer found a path while configuration "
                    "evidence claims a blocker."
                ],
                errors=[
                    {
                        "code": "CONFLICTING_EVIDENCE",
                        "message": (
                            "Healthy reachability conflicts with a blocking configuration fact."
                        ),
                        "retryable": False,
                    }
                ],
            )
        return _base_result(
            evidence,
            status="no_finding",
            completeness="complete",
            facts=facts,
            classification="healthy",
            root_cause=None,
            recommendations=[],
            limitations=[],
            errors=[],
        )

    if not blockers:
        return _base_result(
            evidence,
            status="no_finding",
            completeness="partial",
            facts=facts,
            classification="indeterminate",
            root_cause=None,
            recommendations=[],
            limitations=[
                "Reachability is unreachable, but no supported configuration blocker was observed."
            ],
            errors=[
                {
                    "code": "UNSUPPORTED_ROOT_CAUSE",
                    "message": "No supported root cause can be claimed from the supplied evidence.",
                    "retryable": False,
                }
            ],
        )

    # Both route directions absent is only the peering class when DNS is also explicitly off.
    if any(kind == "peering_path_dns_failure" for kind, _ in blockers):
        blockers = [
            blocker
            for blocker in blockers
            if blocker[0] == "peering_path_dns_failure" or blocker[0] != "missing_route"
        ]
    if len(blockers) != 1:
        return _base_result(
            evidence,
            status="invalid_request",
            completeness="complete",
            facts=facts,
            classification="indeterminate",
            root_cause=None,
            recommendations=[],
            limitations=[
                "Multiple independent blockers were observed; no single root cause was selected."
            ],
            errors=[
                {
                    "code": "CONFLICTING_EVIDENCE",
                    "message": "Evidence supports multiple failure classes.",
                    "retryable": False,
                }
            ],
        )

    classification = blockers[0][0]
    root_cause, recommendation = _FAILURES[classification]
    return _base_result(
        evidence,
        status="unreachable",
        completeness="complete",
        facts=facts,
        classification=classification,
        root_cause=root_cause,
        recommendations=[recommendation],
        limitations=[],
        errors=[],
    )
