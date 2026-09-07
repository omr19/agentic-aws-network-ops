"""Deployment-facing remediation Lambda contract using the immutable manifest."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

from .manifest import RemediationSpec, resolve_manifest
from .workflow import RemediationContractError


class RemediationLambdaError(ValueError):
    """Raised when a remediation Lambda event is outside the closed contract."""


class RemediationExecutor(Protocol):
    def execute(
        self,
        *,
        spec: RemediationSpec,
        request: Mapping[str, Any],
        execution_id: str,
        now: datetime,
    ) -> dict[str, Any]: ...


SUPPORTED_ACTIONS = frozenset(
    {
        "restore_security_group_ingress",
        "restore_vpc_peering_route",
        "restore_network_acl_entry",
    }
)


def handle_remediation_event(
    event: Mapping[str, Any],
    *,
    executor: RemediationExecutor,
    now: datetime,
) -> dict[str, Any]:
    """Resolve all AWS fields from the manifest and invoke one injected executor.

    Production code should supply an executor that performs preflight, approval
    consumption, exactly one allowlisted EC2 write, result persistence, and READ
    verification. This interface deliberately contains no boto3 or AWS calls.
    """

    expected = {"action", "request", "execution_id"}
    if set(event) != expected:
        raise RemediationLambdaError("event fields must be exactly action, request, execution_id")
    action = event["action"]
    request = event["request"]
    execution_id = event["execution_id"]
    if not isinstance(action, str) or action not in SUPPORTED_ACTIONS:
        raise RemediationLambdaError("action is unsupported")
    if not isinstance(request, Mapping):
        raise RemediationLambdaError("request must be a structured mapping")
    request_fields = {
        "schema_version",
        "scenario_id",
        "approval_id",
        "request_hash",
        "correlation_id",
        "policy_session_id",
    }
    if set(request) != request_fields:
        raise RemediationLambdaError("request fields must be the closed remediation request")
    if not isinstance(execution_id, str) or not execution_id:
        raise RemediationLambdaError("execution_id must be a non-empty string")
    try:
        spec = resolve_manifest(action, str(request.get("scenario_id")))
        return executor.execute(spec=spec, request=request, execution_id=execution_id, now=now)
    except (ValueError, RemediationContractError) as error:
        raise RemediationLambdaError(str(error)) from error
