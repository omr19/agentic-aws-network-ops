"""Standard local Phase 8 Approval Lambda wrapper.

This module contains no AWS client. ``build_service`` is the replaceable
production adapter boundary and deliberately fails closed until configured.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from agentic_aws_network_ops.approval.lambda_interface import handle_approval_event
from agentic_aws_network_ops.approval.service import ApprovalService

from .phase8_common import (
    Phase8WrapperError,
    authenticated_principal,
    log_event,
    request_id,
    validate_approval_event,
)
from .phase8_runtime import RuntimeConfigurationError, build_approval_service


class ApprovalServiceFactory(Protocol):
    """Build an AWS-backed service for one authenticated invocation."""

    def __call__(self, *, principal: str, context: Any) -> ApprovalService: ...


class WrapperConfigurationError(Phase8WrapperError):
    """Raised when a live AWS adapter has not been explicitly configured."""


def build_service(*, principal: str, context: Any) -> ApprovalService:
    """Build the role-backed service from strict deployment configuration."""
    try:
        return build_approval_service(principal=principal, context=context)
    except RuntimeConfigurationError as error:
        raise WrapperConfigurationError(str(error)) from error


def _now() -> datetime:
    return datetime.now(UTC)


def dispatch(
    event: object,
    context: Any,
    *,
    service_factory: ApprovalServiceFactory = build_service,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate, bind identity, and dispatch one explicit approval decision."""
    request_id(context)
    payload = validate_approval_event(event)
    principal = authenticated_principal(context)
    payload["approver_principal"] = principal
    service = service_factory(principal=principal, context=context)
    if service is None:
        raise WrapperConfigurationError("ApprovalService factory returned no service")
    return handle_approval_event(payload, service=service, now=now or _now())


def handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint; all failures are raised and therefore fail closed."""
    request_id_value = request_id(context)
    started = time.perf_counter()
    payload: dict[str, Any] = {}
    try:
        result = dispatch(event, context, service_factory=build_service)
    except Exception:
        log_event(
            "phase8_approval_invocation",
            status="rejected",
            request_id_value=request_id_value,
            approval_id=payload.get("approval_id") if "payload" in locals() else None,
            correlation_id=payload.get("correlation_id") if "payload" in locals() else None,
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        raise
    log_event(
        "phase8_approval_invocation",
        status="accepted",
        request_id_value=request_id_value,
        approval_id=result.get("approval_id"),
        correlation_id=result.get("correlation_id"),
        decision=result.get("decision"),
        duration_ms=(time.perf_counter() - started) * 1000,
    )
    return result
