"""Security tests proving callers cannot tamper with the remediation manifest."""

from __future__ import annotations

import pytest

from agentic_aws_network_ops.remediation.manifest import DEFAULT_MANIFEST, resolve_manifest
from agentic_aws_network_ops.remediation.workflow import (
    RemediationContractError,
    create_proposal,
    request_hash,
)


def make_request(scenario: str) -> dict[str, str]:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": scenario,
        "approval_id": "00000000-0000-4000-8000-000000000001",
        "request_hash": "",
        "correlation_id": "00000000-0000-4000-8000-000000000002",
        "policy_session_id": "00000000-0000-4000-8000-000000000003",
    }
    request["request_hash"] = request_hash(request)
    return request


def test_caller_cannot_replace_manifest_with_foreign_mapping() -> None:
    request = make_request("security_group_rule")
    with pytest.raises(RemediationContractError, match="override"):
        create_proposal(
            request=request,
            action="restore_security_group_ingress",
            evidence=[],
            proposed_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            manifest={
                "restore_security_group_ingress": DEFAULT_MANIFEST["restore_security_group_ingress"]
            },
        )


def test_manifest_does_not_expose_dns_or_delete_operations() -> None:
    assert "restore_peering_dns" not in DEFAULT_MANIFEST
    for spec in DEFAULT_MANIFEST.values():
        assert "Delete" not in spec.operation
        assert "Revoke" not in spec.operation
        assert spec.protocol == "tcp"
        assert (spec.from_port, spec.to_port) == (443, 443)


def test_workflow_resolves_resource_and_parameters_from_manifest() -> None:
    request = make_request("nacl_rule")
    proposal = create_proposal(
        request=request,
        action="restore_network_acl_entry",
        evidence=[],
        proposed_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    spec = resolve_manifest("restore_network_acl_entry", "nacl_rule")
    assert proposal["resource"] == spec.resource_id
    assert proposal["operation"] == spec.operation
    assert proposal["parameters"] == dict(spec.parameters())
    assert proposal["required_tags"] == dict(spec.required_tags.as_dict())
