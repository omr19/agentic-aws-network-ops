"""Shared fail-closed helpers for the local Phase 8 Lambda wrappers."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Any
from uuid import UUID

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

UUID_FIELDS = ("proposal_id", "approval_id", "correlation_id", "policy_session_id")
ACTIONS = frozenset(
    {
        "restore_security_group_ingress",
        "restore_vpc_peering_route",
        "restore_network_acl_entry",
    }
)
APPROVAL_OPERATIONS = frozenset({"approve", "deny"})
REMEDIATION_OPERATIONS = frozenset(
    {
        "AuthorizeSecurityGroupIngress",
        "CreateRoute",
        "ReplaceRoute",
        "CreateRouteOrReplaceRoute",
        "ReplaceNetworkAclEntry",
    }
)
REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "approval_id",
        "request_hash",
        "correlation_id",
        "policy_session_id",
    }
)


class Phase8WrapperError(ValueError):
    """Raised when a wrapper cannot establish a trusted, valid invocation."""


def require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Phase8WrapperError(f"{name} must be a structured object")
    return value


def require_exact_fields(payload: Mapping[str, Any], expected: frozenset[str], name: str) -> None:
    if set(payload) != expected:
        raise Phase8WrapperError(f"{name} fields are outside the closed contract")


def require_string(payload: Mapping[str, Any], field: str, *, nonempty: bool = True) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or (nonempty and not value):
        raise Phase8WrapperError(f"{field} must be a non-empty string")
    return value


def require_uuid(payload: Mapping[str, Any], field: str) -> str:
    value = require_string(payload, field)
    try:
        UUID(value)
    except ValueError as error:
        raise Phase8WrapperError(f"{field} must be a UUID") from error
    return value


def require_hash(payload: Mapping[str, Any], field: str = "request_hash") -> str:
    value = require_string(payload, field)
    if re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise Phase8WrapperError(f"{field} must be a lowercase SHA-256 hex string")
    return value


def authenticated_principal(context: Any) -> str:
    """Extract only the principal from the typed verified-IAM handoff context.

    Standard direct Lambda context, arbitrary attributes, event fields, and
    ``ClientContext.custom`` values are not authentication evidence and fail
    closed. A separate IAM/SigV4 ingress adapter must construct the typed
    context after authenticating the caller.
    """

    from .phase8_identity import TrustedApprovalInvocationContext

    if not isinstance(context, TrustedApprovalInvocationContext):
        raise Phase8WrapperError("trusted IAM/SigV4 invocation context is required")
    return context.principal


def request_id(context: Any) -> str:
    value = getattr(context, "aws_request_id", None)
    if not isinstance(value, str) or not value:
        raise Phase8WrapperError("Lambda invocation request ID is required")
    return value


def log_event(event_name: str, *, status: str, request_id_value: str, **safe_fields: Any) -> None:
    """Emit only identifiers/status fields; never serialize the request or exception."""

    safe = {
        "event": event_name,
        "status": status,
        "aws_request_id": request_id_value,
        **{
            key: value
            for key, value in safe_fields.items()
            if key in {"approval_id", "correlation_id", "execution_id", "action", "decision"}
            and isinstance(value, (str, type(None)))
        },
    }
    LOGGER.info(json.dumps(safe, sort_keys=True))


def validate_approval_event(event: object) -> dict[str, Any]:
    payload = dict(require_mapping(event, "approval event"))
    expected = frozenset(
        {
            "operation",
            "proposal_id",
            "approval_id",
            "correlation_id",
            "policy_session_id",
            "request_hash",
            "action",
            "resource",
            "remediation_operation",
        }
    )
    require_exact_fields(payload, expected, "approval event")
    if payload["operation"] not in APPROVAL_OPERATIONS:
        raise Phase8WrapperError("operation must be approve or deny")
    for field in UUID_FIELDS:
        require_uuid(payload, field)
    require_hash(payload)
    if payload["action"] not in ACTIONS:
        raise Phase8WrapperError("action is unsupported")
    require_string(payload, "resource")
    if payload["remediation_operation"] not in REMEDIATION_OPERATIONS:
        raise Phase8WrapperError("remediation operation is unsupported")
    return payload


def validate_remediation_event(event: object) -> dict[str, Any]:
    payload = dict(require_mapping(event, "remediation event"))
    require_exact_fields(
        payload, frozenset({"action", "request", "execution_id"}), "remediation event"
    )
    if payload["action"] not in ACTIONS:
        raise Phase8WrapperError("action is unsupported")
    request = dict(require_mapping(payload["request"], "remediation request"))
    require_exact_fields(request, REQUEST_FIELDS, "remediation request")
    if request["schema_version"] != "1.0.0":
        raise Phase8WrapperError("schema_version must be 1.0.0")
    if request["scenario_id"] not in {
        "security_group_rule",
        "route_table_entry",
        "nacl_rule",
        "peering_routes_dns",
    }:
        raise Phase8WrapperError("scenario_id is unsupported")
    for field in ("approval_id", "correlation_id", "policy_session_id"):
        require_uuid(request, field)
    require_hash(request)
    require_uuid(payload, "execution_id")
    payload["request"] = request
    return payload
