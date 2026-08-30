"""Offline mocked tests for the Phase 8 standard Lambda wrappers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agentic_aws_network_ops.adapters import approval_lambda, remediation_lambda
from agentic_aws_network_ops.adapters.phase8_common import Phase8WrapperError
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.workflow import request_hash

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
PRINCIPAL = "arn:aws:iam::000000000000:user/approved-operator"


class Context(SimpleNamespace):
    aws_request_id: str
    authenticated_principal: str


def context(principal: str = PRINCIPAL) -> Context:
    return Context(aws_request_id="request-123", authenticated_principal=principal)


def approval_event(principal: str = PRINCIPAL) -> dict[str, str]:
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
        "approver_principal": principal,
    }


def remediation_event() -> dict[str, object]:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "nacl_rule",
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    request["request_hash"] = request_hash(request)
    return {
        "action": "restore_network_acl_entry",
        "request": request,
        "execution_id": str(uuid4()),
    }


def test_approval_handler_uses_context_identity_and_replaceable_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = approval_event()
    repository = InMemoryApprovalRepository()
    service = ApprovalService(repository, {PRINCIPAL})
    captured: dict[str, object] = {}

    def factory(*, principal: str, context: object) -> ApprovalService:
        captured.update(principal=principal, context=context)
        return service

    monkeypatch.setattr(approval_lambda, "build_service", factory)
    result = approval_lambda.handler(event, context())

    assert result["decision"] == "APPROVED"
    assert captured["principal"] == PRINCIPAL


def test_approval_handler_rejects_missing_or_mismatched_identity() -> None:
    event = approval_event()
    with pytest.raises(Phase8WrapperError):
        approval_lambda.dispatch(event, SimpleNamespace(aws_request_id="request-123"), now=NOW)
    with pytest.raises(Phase8WrapperError):
        approval_lambda.dispatch(
            event,
            context("arn:aws:iam::000000000000:user/different"),
            service_factory=lambda **_: ApprovalService(InMemoryApprovalRepository(), {PRINCIPAL}),
            now=NOW,
        )


def test_approval_handler_rejects_unverified_client_context_identity() -> None:
    event = approval_event()
    untrusted_context = SimpleNamespace(
        aws_request_id="request-123",
        client_context=SimpleNamespace(custom={"authenticated_principal": PRINCIPAL}),
    )
    with pytest.raises(Phase8WrapperError):
        approval_lambda.dispatch(event, untrusted_context, now=NOW)


    event = approval_event()
    event["unexpected_field"] = "redacted-value"
    with pytest.raises(Phase8WrapperError):
        approval_lambda.dispatch(
            event,
            context(),
            service_factory=lambda **_: pytest.fail("adapter must not be called"),
            now=NOW,
        )


class RecordingExecutor:
    def __init__(self) -> None:
        self.principal: str | None = None
        self.called = False

    def execute(
        self, *, spec: object, request: object, execution_id: str, now: datetime
    ) -> dict[str, object]:
        self.called = True
        return {
            "status": "completed",
            "write_performed": False,
            "execution_id": execution_id,
        }


def test_remediation_handler_preserves_binding_and_manifest_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = remediation_event()
    executor = RecordingExecutor()
    captured: dict[str, object] = {}

    def factory(*, principal: str, context: object) -> RecordingExecutor:
        captured.update(principal=principal, context=context)
        return executor

    monkeypatch.setattr(remediation_lambda, "build_executor", factory)
    result = remediation_lambda.handler(event, context())

    assert result["status"] == "completed"
    assert executor.called
    assert captured["principal"] == PRINCIPAL


def test_remediation_handler_fails_closed_without_approval_binding() -> None:
    event = remediation_event()
    request = event["request"]
    assert isinstance(request, dict)
    request["approval_id"] = "not-a-uuid"
    with pytest.raises(Phase8WrapperError):
        remediation_lambda.dispatch(
            event,
            context(),
            executor_factory=lambda **_: pytest.fail("executor must not be called"),
            now=NOW,
        )


def test_default_adapters_fail_closed_without_aws_configuration() -> None:
    with pytest.raises(approval_lambda.WrapperConfigurationError):
        approval_lambda.dispatch(approval_event(), context(), now=NOW)
    with pytest.raises(remediation_lambda.WrapperConfigurationError):
        remediation_lambda.dispatch(remediation_event(), context(), now=NOW)


def test_logs_are_structured_and_do_not_contain_request_secrets(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    event = approval_event()
    event["request_hash"] = "redacted-hash-value"
    repository = InMemoryApprovalRepository()
    monkeypatch.setattr(
        approval_lambda,
        "build_service",
        lambda **_: ApprovalService(repository, {PRINCIPAL}),
    )
    with pytest.raises(Phase8WrapperError):
        approval_lambda.handler(event, context())
    records = [json.loads(record.message) for record in caplog.records]
    assert records[-1]["status"] == "rejected"
    assert "redacted-hash-value" not in caplog.text
    assert "resource" not in records[-1]
