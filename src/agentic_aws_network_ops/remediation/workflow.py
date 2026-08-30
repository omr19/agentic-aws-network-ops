"""Local-only approval-gated remediation workflow.

This module does not call AWS, Terraform, IAM, or deployment tooling. It models the
proposal, explicit approval, single-use consumption, execution result, and READ
verification boundaries for the narrow Phase 8 remediation contract.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final, Protocol
from uuid import UUID, uuid4

from .manifest import DEFAULT_MANIFEST, RemediationSpec, resolve_manifest

SCHEMA_VERSION: Final = "1.0.0"

APPROVAL_TTL: Final = timedelta(minutes=5)
SUPPORTED_ACTIONS: Final = frozenset(
    {
        "restore_security_group_ingress",
        "restore_vpc_peering_route",
        "restore_network_acl_entry",
    }
)
SUPPORTED_SCENARIOS: Final = frozenset(
    {"security_group_rule", "route_table_entry", "nacl_rule", "peering_routes_dns"}
)


class RemediationContractError(ValueError):
    """Raised when a local remediation contract or boundary is invalid."""


class ApprovalStore(Protocol):
    def save(self, approval: dict[str, Any]) -> None: ...

    def get(self, approval_id: str) -> dict[str, Any] | None: ...

    def consume(self, approval_id: str, execution_id: str) -> bool: ...


class ExecutionAdapter(Protocol):
    def execute(self, proposal: Mapping[str, Any]) -> dict[str, Any]: ...


class VerificationAdapter(Protocol):
    def verify(self, proposal: Mapping[str, Any]) -> dict[str, Any]: ...


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def request_hash(request: Mapping[str, Any]) -> str:
    """Return the stable SHA-256 hash of a request without its supplied hash."""

    unsigned = {key: value for key, value in request.items() if key != "request_hash"}
    return hashlib.sha256(_canonical_json(unsigned).encode()).hexdigest()


def _uuid(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise RemediationContractError(f"{field} must be a UUID")
    try:
        UUID(value)
    except ValueError as error:
        raise RemediationContractError(f"{field} must be a UUID") from error
    return value


def _required_string(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise RemediationContractError(f"{field} must be a non-empty string")
    return value


def validate_request(request: Mapping[str, Any]) -> None:
    """Validate the model-controlled request and reject arbitrary AWS parameters."""

    expected = {
        "schema_version",
        "scenario_id",
        "approval_id",
        "request_hash",
        "correlation_id",
        "policy_session_id",
    }
    if set(request) != expected:
        raise RemediationContractError("request fields must exactly match the remediation contract")
    if request.get("schema_version") != SCHEMA_VERSION:
        raise RemediationContractError("schema_version must be 1.0.0")
    if request.get("scenario_id") not in SUPPORTED_SCENARIOS:
        raise RemediationContractError("scenario_id is unsupported")
    _uuid(request.get("approval_id"), "approval_id")
    _uuid(request.get("correlation_id"), "correlation_id")
    _uuid(request.get("policy_session_id"), "policy_session_id")
    supplied_hash = _required_string(request, "request_hash")
    if supplied_hash != request_hash(request):
        raise RemediationContractError("request_hash does not match the canonical request")


def _validate_action_parameters(action: str, operation: str, parameters: Mapping[str, Any]) -> None:
    allowed: dict[str, tuple[str, ...]] = {
        "restore_security_group_ingress": ("AuthorizeSecurityGroupIngress",),
        "restore_vpc_peering_route": ("CreateRoute", "ReplaceRoute"),
        "restore_network_acl_entry": ("ReplaceNetworkAclEntry",),
    }
    if operation not in allowed[action]:
        raise RemediationContractError("operation is not supported for action")
    expected_keys = {
        "restore_security_group_ingress": {
            "protocol",
            "from_port",
            "to_port",
            "cidr_ip",
        },
        "restore_vpc_peering_route": {
            "route_table_id",
            "destination_cidr",
            "vpc_peering_connection_id",
        },
        "restore_network_acl_entry": {
            "rule_number",
            "egress",
            "protocol",
            "from_port",
            "to_port",
            "cidr_block",
            "rule_action",
        },
    }[action]
    if set(parameters) != expected_keys:
        raise RemediationContractError("arbitrary remediation parameters are unsupported")
    if action == "restore_security_group_ingress" and dict(parameters) != {
        "protocol": "tcp",
        "from_port": 443,
        "to_port": 443,
        "cidr_ip": "10.10.0.0/16",
    }:
        raise RemediationContractError(
            "security-group parameters are outside the approved manifest"
        )
    if action == "restore_network_acl_entry" and dict(parameters) != {
        "rule_number": 100,
        "egress": False,
        "protocol": "tcp",
        "from_port": 443,
        "to_port": 443,
        "cidr_block": "10.10.0.0/16",
        "rule_action": "allow",
    }:
        raise RemediationContractError("NACL parameters are outside the approved manifest")
    if action == "restore_vpc_peering_route":
        if parameters.get("destination_cidr") not in {"10.10.0.0/16", "10.20.0.0/16"}:
            raise RemediationContractError("route destination is outside the approved manifest")
        if not all(
            isinstance(parameters.get(key), str) and parameters[key]
            for key in ("route_table_id", "vpc_peering_connection_id")
        ):
            raise RemediationContractError("route identifiers must be non-empty strings")


def create_proposal(
    *,
    request: Mapping[str, Any],
    action: str,
    evidence: list[Mapping[str, Any]],
    proposed_at: datetime,
    manifest: Mapping[str, RemediationSpec] | None = None,
) -> dict[str, Any]:
    """Create a proposal from the immutable manifest; no caller AWS fields are accepted."""

    validate_request(request)
    try:
        spec = resolve_manifest(action, str(request["scenario_id"]))
    except ValueError as error:
        raise RemediationContractError(str(error)) from error
    if manifest is not None and manifest is not DEFAULT_MANIFEST:
        raise RemediationContractError("manifest override is not permitted")
    if proposed_at.tzinfo is None:
        raise RemediationContractError("proposed_at must be timezone-aware")
    return {
        "schema_version": SCHEMA_VERSION,
        "proposal_id": str(uuid4()),
        "approval_id": request["approval_id"],
        "correlation_id": request["correlation_id"],
        "policy_session_id": request["policy_session_id"],
        "scenario_id": spec.scenario_id,
        "action": spec.action,
        "region": spec.region,
        "resource": spec.resource_id,
        "operation": spec.operation,
        "parameters": dict(spec.parameters()),
        "evidence": [dict(item) for item in evidence],
        "expected_result": spec.expected_post_state,
        "required_tags": dict(spec.required_tags.as_dict()),
        "request_hash": request["request_hash"],
        "proposed_at": proposed_at.isoformat().replace("+00:00", "Z"),
    }


def record_approval(
    *,
    proposal: Mapping[str, Any],
    approver_principal: str,
    approved: bool,
    approved_at: datetime,
    store: ApprovalStore,
) -> dict[str, Any]:
    """Record an explicit approval or denial; natural language is not accepted."""

    if not approver_principal or approved not in {True, False}:
        raise RemediationContractError("approver and explicit boolean decision are required")
    if approved_at.tzinfo is None:
        raise RemediationContractError("approved_at must be timezone-aware")
    approval = {
        "schema_version": SCHEMA_VERSION,
        "approval_id": proposal["approval_id"],
        "correlation_id": proposal["correlation_id"],
        "policy_session_id": proposal["policy_session_id"],
        "proposal_id": proposal["proposal_id"],
        "request_hash": proposal["request_hash"],
        "action": proposal["action"],
        "resource": proposal["resource"],
        "operation": proposal["operation"],
        "approver_principal": approver_principal,
        "decision": "APPROVED" if approved else "DENIED",
        "approved_at": approved_at.isoformat().replace("+00:00", "Z"),
        "expires_at": (approved_at + APPROVAL_TTL).isoformat().replace("+00:00", "Z"),
        "consumed": False,
        "execution_id": None,
        "execution_status": "PENDING",
    }
    store.save(approval)
    return approval


def execute(
    *,
    request: Mapping[str, Any],
    proposal: Mapping[str, Any],
    execution_id: str,
    now: datetime,
    store: ApprovalStore,
    adapter: ExecutionAdapter,
) -> dict[str, Any]:
    """Consume a matching approval once, then invoke only the injected local adapter."""

    validate_request(request)
    _uuid(execution_id, "execution_id")
    if proposal.get("request_hash") != request["request_hash"]:
        raise RemediationContractError("proposal does not match request hash")
    if proposal.get("correlation_id") != request["correlation_id"]:
        raise RemediationContractError("proposal correlation_id does not match request")
    if proposal.get("policy_session_id") != request["policy_session_id"]:
        raise RemediationContractError("proposal policy_session_id does not match request")
    approval = store.get(request["approval_id"])
    if approval is None:
        raise RemediationContractError("explicit approval is required before execution")
    if approval.get("decision") != "APPROVED":
        raise RemediationContractError("approval decision does not permit execution")
    if approval.get("correlation_id") != request["correlation_id"]:
        raise RemediationContractError("approval correlation_id does not match request")
    if approval.get("policy_session_id") != request["policy_session_id"]:
        raise RemediationContractError("approval policy_session_id does not match request")
    if approval.get("request_hash") != request["request_hash"]:
        raise RemediationContractError("approval request_hash does not match request")
    expires_at = datetime.fromisoformat(str(approval["expires_at"]).replace("Z", "+00:00"))
    if now >= expires_at:
        raise RemediationContractError("approval has expired")
    if not store.consume(request["approval_id"], execution_id):
        raise RemediationContractError("approval was already consumed or unavailable")
    result = dict(adapter.execute(proposal))
    result.update(
        {
            "schema_version": SCHEMA_VERSION,
            "execution_id": execution_id,
            "correlation_id": request["correlation_id"],
            "approval_id": request["approval_id"],
            "status": result.get("status", "completed"),
            "write_performed": bool(result.get("write_performed", True)),
            "terraform_drift": True,
            "reconciliation_required": True,
        }
    )
    return result


def verify(
    *,
    proposal: Mapping[str, Any],
    execution_result: Mapping[str, Any],
    verifier: VerificationAdapter,
) -> dict[str, Any]:
    """Run the separate injected READ verification adapter and preserve its result."""

    if execution_result.get("correlation_id") != proposal.get("correlation_id"):
        raise RemediationContractError("verification correlation_id does not match proposal")
    result = dict(verifier.verify(proposal))
    result.update(
        {
            "schema_version": SCHEMA_VERSION,
            "correlation_id": proposal["correlation_id"],
            "execution_id": execution_result["execution_id"],
            "status": result.get("status", "verified"),
            "remediation_fact": result.get("remediation_fact", "verification completed"),
        }
    )
    return result


@dataclass
class InMemoryApprovalStore:
    """Deterministic test-only approval store; not a production persistence adapter."""

    approvals: dict[str, dict[str, Any]]

    def save(self, approval: dict[str, Any]) -> None:
        approval_id = str(approval["approval_id"])
        self.approvals[approval_id] = dict(approval)

    def get(self, approval_id: str) -> dict[str, Any] | None:
        value = self.approvals.get(approval_id)
        return dict(value) if value else None

    def consume(self, approval_id: str, execution_id: str) -> bool:
        approval = self.approvals.get(approval_id)
        if approval is None or approval.get("consumed"):
            return False
        approval["consumed"] = True
        approval["execution_id"] = execution_id
        approval["execution_status"] = "EXECUTING"
        return True
