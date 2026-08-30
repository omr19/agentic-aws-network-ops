"""Standard local Phase 8 Remediation Lambda wrapper.

The wrapper owns request/context validation. The injected executor owns the
AWS-backed approval lookup/atomic consume, preflight, one allowlisted write,
persistence, and independent read verification. No AWS client is created here.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from agentic_aws_network_ops.remediation.lambda_interface import (
    RemediationExecutor,
    handle_remediation_event,
)
from agentic_aws_network_ops.remediation.workflow import validate_request

from .phase8_common import (
    Phase8WrapperError,
    authenticated_principal,
    log_event,
    request_id,
    validate_remediation_event,
)
from .phase8_runtime import RuntimeConfigurationError, build_remediation_executor


class RemediationExecutorFactory(Protocol):
    """Build an executor that fails closed without a matching approval record."""

    def __call__(self, *, principal: str, context: Any) -> RemediationExecutor: ...


class WrapperConfigurationError(Phase8WrapperError):
    """Raised when a live AWS adapter has not been explicitly configured."""


def build_executor(*, principal: str, context: Any) -> RemediationExecutor:
    """Build the role-backed executor from strict deployment configuration."""
    try:
        return cast(
            RemediationExecutor,
            build_remediation_executor(principal=principal, context=context),
        )
    except RuntimeConfigurationError as error:
        raise WrapperConfigurationError(str(error)) from error


def _now() -> datetime:
    return datetime.now(UTC)


def dispatch(
    event: object,
    context: Any,
    *,
    executor_factory: RemediationExecutorFactory = build_executor,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate context/request bindings and dispatch through the frozen manifest."""
    request_id(context)
    payload = validate_remediation_event(event)
    principal = authenticated_principal(context)
    request = payload["request"]
    try:
        validate_request(request)
    except ValueError as error:
        raise Phase8WrapperError("remediation request binding is invalid") from error
    executor = executor_factory(principal=principal, context=context)
    if executor is None:
        raise WrapperConfigurationError("RemediationExecutor factory returned no executor")
    return handle_remediation_event(payload, executor=executor, now=now or _now())


def handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint; absent context or approval is a failed invocation."""
    request_id_value = request_id(context)
    payload: dict[str, Any] = {}
    try:
        payload = validate_remediation_event(event)
        result = dispatch(event, context, executor_factory=build_executor)
    except Exception:
        request = payload.get("request", {})
        log_event(
            "phase8_remediation_invocation",
            status="rejected",
            request_id_value=request_id_value,
            approval_id=request.get("approval_id"),
            correlation_id=request.get("correlation_id"),
            execution_id=payload.get("execution_id"),
            action=payload.get("action"),
        )
        raise
    request = payload["request"]
    log_event(
        "phase8_remediation_invocation",
        status="accepted",
        request_id_value=request_id_value,
        approval_id=request.get("approval_id"),
        correlation_id=request.get("correlation_id"),
        execution_id=payload.get("execution_id"),
        action=payload.get("action"),
    )
    return result
