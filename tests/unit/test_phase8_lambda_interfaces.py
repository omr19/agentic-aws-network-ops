"""Offline unit tests for the deployment-facing Lambda interfaces."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agentic_aws_network_ops.approval.lambda_interface import (
    ApprovalLambdaError,
    handle_approval_event,
)
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.lambda_interface import (
    RemediationLambdaError,
    handle_remediation_event,
)
from agentic_aws_network_ops.remediation.manifest import RemediationSpec

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
PRINCIPAL = "arn:aws:iam::000000000000:user/approved-operator"


def approval_event() -> dict[str, object]:
    return {
        "operation": "approve",
        "proposal_id": str(uuid4()),
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "a" * 64,
        "action": "restore_security_group_ingress",
        "resource": "${destination_security_group_id}",
        "remediation_operation": "AuthorizeSecurityGroupIngress",
        "approver_principal": PRINCIPAL,
    }


def test_approval_interface_persists_only_structured_decisions() -> None:
    repository = InMemoryApprovalRepository()
    result = handle_approval_event(
        approval_event(),
        service=ApprovalService(repository, {PRINCIPAL}),
        now=NOW,
    )
    assert result["decision"] == "APPROVED"
    with pytest.raises(ApprovalLambdaError):
        handle_approval_event(
            {"message": "yes"},
            service=ApprovalService(repository, {PRINCIPAL}),
            now=NOW,
        )


class RecordingExecutor:
    def __init__(self) -> None:
        self.spec: RemediationSpec | None = None

    def execute(
        self, *, spec: RemediationSpec, request: object, execution_id: str, now: datetime
    ) -> dict[str, object]:
        self.spec = spec
        return {"status": "completed", "execution_id": execution_id}


def test_remediation_interface_resolves_manifest_and_never_accepts_aws_fields() -> None:
    executor = RecordingExecutor()
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "nacl_rule",
        "approval_id": str(uuid4()),
        "request_hash": "b" * 64,
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    result = handle_remediation_event(
        {"action": "restore_network_acl_entry", "request": request, "execution_id": str(uuid4())},
        executor=executor,
        now=NOW,
    )
    assert result["status"] == "completed"
    assert executor.spec is not None
    assert executor.spec.nacl_rule_number == 100
    with pytest.raises(RemediationLambdaError):
        handle_remediation_event(
            {
                "action": "restore_network_acl_entry",
                "request": request,
                "execution_id": str(uuid4()),
                "resource": "attacker",
            },
            executor=executor,
            now=NOW,
        )


def test_remediation_interface_rejects_dns_and_unknown_actions() -> None:
    executor = RecordingExecutor()
    request = {"scenario_id": "peering_routes_dns"}
    with pytest.raises(RemediationLambdaError):
        handle_remediation_event(
            {"action": "restore_peering_dns", "request": request, "execution_id": str(uuid4())},
            executor=executor,
            now=NOW,
        )
