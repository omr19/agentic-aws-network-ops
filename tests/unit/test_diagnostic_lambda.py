"""Tests for the thin diagnostic Lambda adapter."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from agentic_aws_network_ops.adapters import diagnostic_lambda

FIXTURE = Path(__file__).parents[1] / "fixtures/events/diagnostic-describe-vpcs.json"


class FakeService:
    def execute(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool": tool,
            "status": "success",
            "correlation_id": payload["correlation_id"],
            "evidence_completeness": "complete",
        }


class RejectingFakeService:
    def execute(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        del payload
        return {
            "tool": tool,
            "status": "invalid_request",
            "correlation_id": "invalid-request",
            "evidence_completeness": "none",
        }


def test_handler_delegates_and_emits_sanitized_structured_log(
    monkeypatch: Any, caplog: Any
) -> None:
    monkeypatch.setattr(diagnostic_lambda, "build_service", lambda region: FakeService())
    event = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with caplog.at_level(logging.INFO):
        result = diagnostic_lambda.handler(event, None)
    record = json.loads(caplog.records[-1].message)
    assert result["status"] == "success"
    assert record["event_name"] == "diagnostic_tool_call"
    assert record["schema_version"] == "1.0.0"
    assert record["redaction_policy"] == "allowlist-v1"
    assert record["correlation_id"] == "corr-test-0001"
    assert record["evidence_completeness"] == "complete"
    assert record["status"] == "success"
    assert record["tool_name"] == "describe_vpcs"
    assert record["duration_ms"] >= 0


def test_handler_rejects_malformed_event_and_logs_only_safe_metadata(
    monkeypatch: Any, caplog: Any
) -> None:
    monkeypatch.setattr(diagnostic_lambda, "build_service", lambda region: RejectingFakeService())
    with caplog.at_level(logging.INFO):
        result = diagnostic_lambda.handler({"arguments": "not-an-object"}, None)
    record = json.loads(caplog.records[-1].message)
    assert result["status"] == "invalid_request"
    assert record["correlation_id"] == "invalid-request"
    assert "not-an-object" not in caplog.text
