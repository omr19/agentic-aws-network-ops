"""Offline unit tests for structured Phase 8 approval persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService, ApprovalServiceError

NOW = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
AUTHORIZED = "arn:aws:iam::000000000000:user/approved-operator"


def payload(operation: str = "approve", **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "operation": operation,
        "proposal_id": str(uuid4()),
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "a" * 64,
        "action": "restore_security_group_ingress",
        "resource": "destination-security-group",
        "remediation_operation": "AuthorizeSecurityGroupIngress",
        "approver_principal": AUTHORIZED,
    }
    value.update(overrides)
    return value


def service() -> tuple[ApprovalService, InMemoryApprovalRepository]:
    repository = InMemoryApprovalRepository()
    return ApprovalService(repository, {AUTHORIZED}), repository


def test_explicit_approval_and_denial_are_persisted() -> None:
    approval_service, repository = service()
    approved = approval_service.submit(payload(), now=NOW)
    denied = approval_service.submit(payload("deny"), now=NOW)
    assert approved["decision"] == "APPROVED"
    assert denied["decision"] == "DENIED"
    assert approved["expires_at"] == "2026-09-03T12:05:00Z"
    assert approved["consumed"] is False
    assert approved["execution_id"] is None
    assert repository.get(str(approved["approval_id"])) == approved


def test_natural_language_and_unstructured_input_are_rejected() -> None:
    approval_service, _ = service()
    with pytest.raises(ApprovalServiceError):
        approval_service.submit({"message": "yes"}, now=NOW)
    with pytest.raises(ApprovalServiceError, match="explicit approve or deny"):
        approval_service.submit(payload(operation="yes"), now=NOW)


@pytest.mark.parametrize(
    "field, value",
    [
        ("proposal_id", "not-a-uuid"),
        ("approval_id", "not-a-uuid"),
        ("correlation_id", "not-a-uuid"),
        ("policy_session_id", "not-a-uuid"),
        ("request_hash", "changed"),
        ("action", "unsupported_action"),
        ("resource", ""),
        ("remediation_operation", "DeleteRoute"),
    ],
)
def test_changed_or_mismatched_binding_is_rejected(field: str, value: str) -> None:
    approval_service, _ = service()
    with pytest.raises(ApprovalServiceError):
        approval_service.submit(payload(**{field: value}), now=NOW)


def test_unauthorized_approver_identity_is_rejected() -> None:
    approval_service, _ = service()
    with pytest.raises(ApprovalServiceError, match="unauthorized"):
        approval_service.submit(payload(approver_principal="arn:unauthorized"), now=NOW)


def test_atomic_consumption_records_execution_and_rejects_duplicate_execution() -> None:
    approval_service, repository = service()
    approval = approval_service.submit(payload(), now=NOW)
    approval_id = str(approval["approval_id"])
    execution_id = str(uuid4())
    claimed = approval_service.consume(approval_id=approval_id, execution_id=execution_id, now=NOW)
    replay = approval_service.consume(approval_id=approval_id, execution_id=execution_id, now=NOW)
    assert claimed.status == "CLAIMED"
    assert replay.status == "REPLAY_SAME_EXECUTION"
    assert repository.get(approval_id)["execution_id"] == execution_id  # type: ignore[index]
    with pytest.raises(ApprovalServiceError, match="REPLAY_DIFFERENT_EXECUTION"):
        approval_service.consume(approval_id=approval_id, execution_id=str(uuid4()), now=NOW)


def test_expired_and_denied_approvals_cannot_be_consumed() -> None:
    approval_service, _ = service()
    expired = approval_service.submit(payload(), now=NOW - timedelta(minutes=5))
    with pytest.raises(ApprovalServiceError, match="EXPIRED"):
        approval_service.consume(
            approval_id=str(expired["approval_id"]), execution_id=str(uuid4()), now=NOW
        )
    denied = approval_service.submit(payload("deny"), now=NOW)
    with pytest.raises(ApprovalServiceError, match="NOT_APPROVED"):
        approval_service.consume(
            approval_id=str(denied["approval_id"]), execution_id=str(uuid4()), now=NOW
        )


def test_execution_result_is_persisted_only_for_claiming_execution() -> None:
    approval_service, repository = service()
    approval = approval_service.submit(payload(), now=NOW)
    approval_id = str(approval["approval_id"])
    execution_id = str(uuid4())
    approval_service.consume(approval_id=approval_id, execution_id=execution_id, now=NOW)
    result = {"status": "COMPLETED", "write_performed": True}
    approval_service.record_execution_result(
        approval_id=approval_id, execution_id=execution_id, result=result
    )
    stored = repository.get(approval_id)
    assert stored["execution_status"] == "COMPLETED"  # type: ignore[index]
    assert stored["execution_result"] == result  # type: ignore[index]
    with pytest.raises(ValueError, match="does not own"):
        approval_service.record_execution_result(
            approval_id=approval_id, execution_id=str(uuid4()), result=result
        )
