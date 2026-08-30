"""Security tests for Phase 9 observability redaction and boundary separation."""

from __future__ import annotations

import logging

import pytest

from agentic_aws_network_ops.shared.observability import (
    ObservabilityEventError,
    emit_event,
    emit_exception,
)


def test_observability_allowlist_rejects_secret_like_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(ObservabilityEventError):
        emit_event(
            logging.getLogger("security-test"),
            "diagnostic_tool_call",
            status="success",
            correlation_id="corr-1",
            tool_arguments={"access_key": "not-for-logs"},
        )
    assert "not-for-logs" not in caplog.text


def test_exception_logging_never_serializes_message_or_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("security-test")
    with caplog.at_level(logging.INFO):
        emit_exception(
            logger,
            "remediation_failure",
            RuntimeError("secret request payload and credentials"),
            status="failure",
            correlation_id="corr-1",
        )

    assert "secret request payload" not in caplog.text
    assert "credentials" not in caplog.text
    assert "RuntimeError" in caplog.text
    assert "traceback" not in caplog.text.lower()
