"""Sanitized local observability events for observable execution metadata only."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Mapping
from typing import Any

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

SCHEMA_VERSION = "1.0.0"
REDACTION_POLICY = "allowlist-v1"
_DEFAULT_ENVIRONMENT = "local"
_EVENT_NAME = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_STATUS = re.compile(r"^[a-z][a-z0-9_.-]{1,31}$")
_IDENTIFIER = re.compile(r"^.{1,256}$")
_ERROR_CLASS = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]{0,127}$")
_ACTION = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_DECISION = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
_EVIDENCE = frozenset({"complete", "partial", "none", "unknown"})


class ObservabilityEventError(ValueError):
    """Raised when an event cannot satisfy the sanitized observability contract."""


def _required_text(value: str, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not value or pattern.fullmatch(value) is None:
        raise ObservabilityEventError(f"{field} is invalid")
    return value


def _optional_identifier(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field, _IDENTIFIER)


def _optional_safe(value: str | None, field: str, pattern: re.Pattern[str]) -> str | None:
    if not isinstance(value, str) or value == "":
        return None
    return _required_text(value, field, pattern)


def build_event(
    event_name: str,
    *,
    status: str,
    correlation_id: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    tool_call_id: str | None = None,
    approval_id: str | None = None,
    execution_id: str | None = None,
    verification_id: str | None = None,
    duration_ms: float | None = None,
    error_class: str | None = None,
    region: str | None = None,
    environment: str | None = None,
    tool_name: str | None = None,
    action: str | None = None,
    decision: str | None = None,
    evidence_completeness: str | None = None,
    write_performed: bool | None = None,
    **untrusted: Any,
) -> dict[str, Any]:
    """Build one allowlisted event without accepting payloads or exception messages."""
    if untrusted:
        raise ObservabilityEventError("event contains fields outside the sanitized allowlist")
    environment_value = environment or os.getenv("AGENTIC_ENVIRONMENT") or _DEFAULT_ENVIRONMENT
    event: dict[str, Any] = {
        "event_name": _required_text(event_name, "event_name", _EVENT_NAME),
        "schema_version": SCHEMA_VERSION,
        "status": _required_text(status, "status", _STATUS),
        "environment": _required_text(
            environment_value,
            "environment",
            re.compile(r"^[a-z][a-z0-9_-]{0,31}$"),
        ),
        "redaction_policy": REDACTION_POLICY,
    }
    identifiers = {
        "correlation_id": correlation_id,
        "session_id": session_id,
        "request_id": request_id,
        "tool_call_id": tool_call_id,
        "approval_id": approval_id,
        "execution_id": execution_id,
        "verification_id": verification_id,
        "region": region,
    }
    for field, value in identifiers.items():
        safe_value = _optional_identifier(value, field)
        if safe_value is not None:
            event[field] = safe_value
    if duration_ms is not None:
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, (int, float)):
            raise ObservabilityEventError("duration_ms is invalid")
        if duration_ms < 0:
            raise ObservabilityEventError("duration_ms is invalid")
        event["duration_ms"] = round(float(duration_ms), 3)
    safe_error = _optional_safe(error_class, "error_class", _ERROR_CLASS)
    if safe_error is not None:
        event["error_class"] = safe_error
    for field, value in {
        "tool_name": tool_name,
        "action": action,
        "decision": decision,
    }.items():
        safe_value = _optional_safe(value, field, _ACTION if field != "tool_name" else _EVENT_NAME)
        if safe_value is not None:
            event[field] = safe_value
    if evidence_completeness is not None:
        if evidence_completeness not in _EVIDENCE:
            raise ObservabilityEventError("evidence_completeness is invalid")
        event["evidence_completeness"] = evidence_completeness
    if write_performed is not None:
        if not isinstance(write_performed, bool):
            raise ObservabilityEventError("write_performed is invalid")
        event["write_performed"] = write_performed
    return event


def emit_event(logger: logging.Logger, event_name: str, **fields: Any) -> dict[str, Any]:
    """Build and emit a sanitized event; arbitrary fields are rejected, not serialized."""
    allowed = {
        "status",
        "correlation_id",
        "session_id",
        "request_id",
        "tool_call_id",
        "approval_id",
        "execution_id",
        "verification_id",
        "duration_ms",
        "error_class",
        "region",
        "environment",
        "tool_name",
        "action",
        "decision",
        "evidence_completeness",
        "write_performed",
    }
    if set(fields) - allowed:
        raise ObservabilityEventError("event contains fields outside the sanitized allowlist")
    event = build_event(event_name, **fields)
    logger.info(json.dumps(event, sort_keys=True, separators=(",", ":")))
    return event


def emit_exception(
    logger: logging.Logger, event_name: str, error: BaseException, **fields: Any
) -> dict[str, Any]:
    """Emit only an exception class, never an exception message or traceback payload."""
    return emit_event(logger, event_name, error_class=type(error).__name__, **fields)


def parse_event(record: str) -> Mapping[str, Any]:
    """Parse a log record for offline tests without relaxing producer sanitization."""
    value = json.loads(record)
    if not isinstance(value, dict):
        raise ObservabilityEventError("observability record must be an object")
    return value
