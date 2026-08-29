"""Security boundary tests for the local Phase 8 approval service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService, ApprovalServiceError

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
PRINCIPAL = "arn:aws:iam::000000000000:user/approved-operator"


def valid_payload() -> dict[str, object]:
    return {
        "operation": "approve",
        "proposal_id": str(uuid4()),
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "b" * 64,
        "action": "restore_vpc_peering_route",
        "resource": "project-route-table",
        "remediation_operation": "CreateRoute",
        "approver_principal": PRINCIPAL,
    }


def test_service_accepts_only_closed_structured_input() -> None:
    service = ApprovalService(InMemoryApprovalRepository(), {PRINCIPAL})
    with pytest.raises(ApprovalServiceError):
        service.submit({"operation": "approve", "answer": "yes"}, now=NOW)
    malformed = valid_payload()
    malformed["execute"] = True
    with pytest.raises(ApprovalServiceError, match="exactly"):
        service.submit(malformed, now=NOW)


def test_duplicate_approval_id_is_not_overwritten() -> None:
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository, {PRINCIPAL})
    first = valid_payload()
    service.submit(first, now=NOW)
    second = dict(first, operation="deny")
    with pytest.raises(ValueError, match="already exists"):
        service.submit(second, now=NOW)
    assert repository.get(str(first["approval_id"]))["decision"] == "APPROVED"  # type: ignore[index]


def test_approval_service_has_no_execution_adapter_or_aws_dependency() -> None:
    service = ApprovalService(InMemoryApprovalRepository(), {PRINCIPAL})
    record = service.submit(valid_payload(), now=NOW)
    assert record["execution_id"] is None
    assert "boto3" not in type(service).__module__
