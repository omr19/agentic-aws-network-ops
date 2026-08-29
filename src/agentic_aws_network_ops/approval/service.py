"""Local-only structured human approval service for Phase 8."""

from __future__ import annotations

from collections.abc import Mapping, Set
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from .repository import ApprovalRepository, ConsumeResult

SCHEMA_VERSION = "1.0.0"
APPROVAL_TTL = timedelta(minutes=5)
APPROVAL_OPERATIONS = frozenset({"approve", "deny"})
ACTIONS = frozenset(
    {
        "restore_security_group_ingress",
        "restore_vpc_peering_route",
        "restore_network_acl_entry",
    }
)
REMEDIATION_OPERATIONS = frozenset(
    {
        "AuthorizeSecurityGroupIngress",
        "CreateRoute",
        "ReplaceRoute",
        "ReplaceNetworkAclEntry",
    }
)


class ApprovalServiceError(ValueError):
    """Raised for malformed, unauthorized, expired, or replayed approval operations."""


class ApprovalService:
    """Validate and persist explicit approval decisions without executing remediation."""

    def __init__(self, repository: ApprovalRepository, authorized_approvers: Set[str]) -> None:
        self._repository = repository
        self._authorized_approvers = frozenset(authorized_approvers)

    def submit(
        self,
        payload: Mapping[str, Any],
        *,
        now: datetime,
    ) -> dict[str, Any]:
        """Persist one explicit approve/deny operation; never invokes an execution adapter."""

        self._validate_payload(payload, now=now)
        approval = {
            "schema_version": SCHEMA_VERSION,
            "approval_id": payload["approval_id"],
            "proposal_id": payload["proposal_id"],
            "correlation_id": payload["correlation_id"],
            "policy_session_id": payload["policy_session_id"],
            "request_hash": payload["request_hash"],
            "action": payload["action"],
            "resource": payload["resource"],
            "operation": payload["remediation_operation"],
            "approver_principal": payload["approver_principal"],
            "decision": "APPROVED" if payload["operation"] == "approve" else "DENIED",
            "approved_at": _timestamp(now),
            "expires_at": _timestamp(now + APPROVAL_TTL),
            "consumed": False,
            "execution_id": None,
            "execution_status": "PENDING",
        }
        self._repository.save(approval)
        return approval

    def consume(
        self,
        *,
        approval_id: str,
        execution_id: str,
        now: datetime,
    ) -> ConsumeResult:
        """Atomically claim an approval or return a deterministic replay/binding outcome."""

        _uuid(approval_id, "approval_id")
        _uuid(execution_id, "execution_id")
        result = self._repository.consume(approval_id, execution_id, now)
        if result.status in {"NOT_FOUND", "NOT_APPROVED", "EXPIRED", "REPLAY_DIFFERENT_EXECUTION"}:
            raise ApprovalServiceError(f"approval consumption denied: {result.status}")
        return result

    def record_execution_result(
        self,
        *,
        approval_id: str,
        execution_id: str,
        result: Mapping[str, Any],
    ) -> None:
        _uuid(approval_id, "approval_id")
        _uuid(execution_id, "execution_id")
        self._repository.record_execution_result(approval_id, execution_id, result)

    def _validate_payload(self, payload: Mapping[str, Any], *, now: datetime) -> None:
        expected = {
            "operation",
            "proposal_id",
            "approval_id",
            "correlation_id",
            "policy_session_id",
            "request_hash",
            "action",
            "resource",
            "remediation_operation",
            "approver_principal",
        }
        if set(payload) != expected:
            raise ApprovalServiceError("structured approval fields are required exactly")
        if payload["operation"] not in APPROVAL_OPERATIONS:
            raise ApprovalServiceError("operation must be explicit approve or deny")
        for field in ("proposal_id", "approval_id", "correlation_id", "policy_session_id"):
            _uuid(payload[field], field)
        if not isinstance(payload["request_hash"], str) or len(payload["request_hash"]) != 64:
            raise ApprovalServiceError("request_hash must be a SHA-256 hex string")
        try:
            int(payload["request_hash"], 16)
        except (TypeError, ValueError) as error:
            raise ApprovalServiceError("request_hash must be a SHA-256 hex string") from error
        if payload["action"] not in ACTIONS:
            raise ApprovalServiceError("action is unsupported")
        if payload["remediation_operation"] not in REMEDIATION_OPERATIONS:
            raise ApprovalServiceError("remediation operation is unsupported")
        if not isinstance(payload["resource"], str) or not payload["resource"]:
            raise ApprovalServiceError("resource must be non-empty")
        principal = payload["approver_principal"]
        if principal not in self._authorized_approvers:
            raise ApprovalServiceError("approver principal is unauthorized")
        if now.tzinfo is None:
            raise ApprovalServiceError("now must be timezone-aware")


def _uuid(value: object, field: str) -> None:
    if not isinstance(value, str):
        raise ApprovalServiceError(f"{field} must be a UUID")
    try:
        UUID(value)
    except ValueError as error:
        raise ApprovalServiceError(f"{field} must be a UUID") from error


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
