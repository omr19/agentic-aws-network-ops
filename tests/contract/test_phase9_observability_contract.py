"""Contract tests for the versioned Phase 9 observability event."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, ValidationError  # type: ignore[import-untyped]

from agentic_aws_network_ops.shared.observability import (
    ObservabilityEventError,
    build_event,
)

SCHEMA = Path(__file__).parents[2] / "schemas/observability/observability-event.schema.json"


def test_shared_event_matches_versioned_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    event = build_event(
        "verification",
        status="success",
        correlation_id=str(uuid4()),
        session_id=str(uuid4()),
        request_id="request-1",
        tool_call_id=str(uuid4()),
        approval_id=str(uuid4()),
        execution_id=str(uuid4()),
        verification_id=str(uuid4()),
        duration_ms=4.25,
        region="eu-west-1",
        environment="local",
        evidence_completeness="complete",
    )
    Draft202012Validator(schema).validate(event)


def test_schema_rejects_unallowlisted_payload_fields() -> None:
    event = build_event("diagnostic_tool_call", status="success", correlation_id="corr-1")
    event["prompt"] = "hidden request"
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(event)


def test_helper_rejects_arbitrary_fields_before_logging() -> None:
    with pytest.raises(ObservabilityEventError, match="allowlist"):
        build_event(
            "tool_call",
            status="success",
            correlation_id="corr-1",
            unexpected_field="redacted-value",
        )
