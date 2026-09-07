"""Offline security tests for the trusted Phase 8 approver handoff."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentic_aws_network_ops.adapters import approval_lambda
from agentic_aws_network_ops.adapters.phase8_common import (
    Phase8WrapperError,
    authenticated_principal,
)
from agentic_aws_network_ops.adapters.phase8_identity import (
    TrustedApprovalInvocationContext,
    TrustedIdentityError,
    handoff_verified_iam_principal,
)
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService

PRINCIPAL = "arn:aws:iam::000000000000:user/approved-operator"
NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def approval_event() -> dict[str, str]:
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
    }


def test_verified_iam_handoff_returns_typed_context() -> None:
    context = handoff_verified_iam_principal(
        aws_request_id="request-123",
        principal=PRINCIPAL,
    )
    assert isinstance(context, TrustedApprovalInvocationContext)
    assert authenticated_principal(context) == PRINCIPAL


@pytest.mark.parametrize(
    "kwargs",
    [
        {"aws_request_id": "", "principal": PRINCIPAL},
        {"aws_request_id": "request-123", "principal": "not-an-arn"},
        {
            "aws_request_id": "request-123",
            "principal": "arn:aws:sts::000000000000:assumed-role/operator/session",
        },
    ],
)
def test_handoff_rejects_unverified_or_malformed_identity(kwargs: dict[str, str]) -> None:
    with pytest.raises(TrustedIdentityError):
        handoff_verified_iam_principal(**kwargs)


def test_arbitrary_context_attributes_and_client_context_cannot_establish_identity() -> None:
    forged = SimpleNamespace(
        aws_request_id="request-123",
        authenticated_principal=PRINCIPAL,
        client_context=SimpleNamespace(custom={"authenticated_principal": PRINCIPAL}),
    )
    with pytest.raises(Phase8WrapperError):
        authenticated_principal(forged)


def test_approval_event_identity_field_is_rejected_before_service_factory() -> None:
    event = approval_event()
    event["approver_principal"] = PRINCIPAL
    with pytest.raises(Phase8WrapperError):
        approval_lambda.dispatch(
            event,
            handoff_verified_iam_principal(
                aws_request_id="request-123",
                principal=PRINCIPAL,
            ),
            service_factory=lambda **_: pytest.fail("service must not be constructed"),
        )


def test_wrapper_injects_trusted_principal_into_persisted_approval() -> None:
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository, {PRINCIPAL})
    context = handoff_verified_iam_principal(
        aws_request_id="request-123",
        principal=PRINCIPAL,
    )
    result = approval_lambda.dispatch(
        approval_event(),
        context,
        service_factory=lambda **_: service,
        now=NOW,
    )
    record = repository.get(result["approval_id"])
    assert record is not None
    assert record["approver_principal"] == PRINCIPAL
