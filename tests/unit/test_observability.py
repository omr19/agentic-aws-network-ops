"""Offline behavior tests for the Phase 9 observability foundation."""

from __future__ import annotations

import json
import logging
from uuid import uuid4

import pytest

from agentic_aws_network_ops.adapters import approval_lambda
from agentic_aws_network_ops.adapters.phase8_identity import handoff_verified_iam_principal
from agentic_aws_network_ops.agent.runtime import FixedToolSelector, Runtime
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.shared.boundaries import (
    GatewayReadRequest,
    GatewayReadResponse,
    RuntimeRequest,
)
from agentic_aws_network_ops.shared.observability import emit_event


class FakeGateway:
    def invoke(self, request: GatewayReadRequest) -> GatewayReadResponse:
        result = {
            "tool": request.tool,
            "status": "success",
            "correlation_id": request.correlation_id,
            "evidence_completeness": "complete",
        }
        return GatewayReadResponse.accepted_result(request, result)


def test_runtime_to_mcp_sequence_preserves_identifiers(caplog: pytest.LogCaptureFixture) -> None:
    correlation_id = str(uuid4())
    session_id = str(uuid4())
    request = RuntimeRequest("diagnose", correlation_id, session_id, "eu-west-1")
    runtime = Runtime(
        FixedToolSelector("describe_vpcs", {"schema_version": "1.0.0"}), FakeGateway()
    )

    with caplog.at_level(logging.INFO):
        response = runtime.handle(request)

    assert response.accepted
    events = [json.loads(record.message) for record in caplog.records]
    assert [event["event_name"] for event in events] == [
        "runtime_request",
        "mcp_tool_call",
        "mcp_tool_call",
        "runtime_request",
    ]
    assert {event["correlation_id"] for event in events} == {correlation_id}
    assert {event["session_id"] for event in events} == {session_id}
    assert events[1]["tool_call_id"] == events[2]["tool_call_id"] == events[3]["tool_call_id"]
    assert events[2]["status"] == "success"


def test_denied_approval_emits_safe_decision_event(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    principal = "arn:aws:iam::000000000000:user/operator"
    context = handoff_verified_iam_principal(aws_request_id="request-1", principal=principal)
    event = {
        "operation": "deny",
        "proposal_id": str(uuid4()),
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "a" * 64,
        "action": "restore_security_group_ingress",
        "resource": "secret-resource-reference",
        "remediation_operation": "AuthorizeSecurityGroupIngress",
    }
    service = ApprovalService(InMemoryApprovalRepository(), {principal})
    monkeypatch.setattr(approval_lambda, "build_service", lambda **_: service)

    with caplog.at_level(logging.INFO):
        result = approval_lambda.handler(event, context)

    records = [json.loads(record.message) for record in caplog.records]
    record = records[-1]
    assert result["decision"] == "DENIED"
    assert record["event_name"] == "phase8_approval_invocation"
    assert record["decision"] == "DENIED"
    assert record["correlation_id"] == event["correlation_id"]
    assert "secret-resource-reference" not in caplog.text


def test_failure_event_contains_class_not_exception_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        emit_event(
            logging.getLogger("test-observability"),
            "tool_failure",
            status="failure",
            error_class="TimeoutError",
            correlation_id="corr-1",
            duration_ms=12.5,
        )

    record = json.loads(caplog.records[-1].message)
    assert record["error_class"] == "TimeoutError"
    assert "exception message" not in caplog.text
