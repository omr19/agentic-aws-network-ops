"""Security boundary tests for the local Phase 8 remediation workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agentic_aws_network_ops.remediation.workflow import (
    InMemoryApprovalStore,
    RemediationContractError,
    create_proposal,
    execute,
    record_approval,
    request_hash,
)


def test_diagnostic_action_names_are_not_supported_by_write_workflow() -> None:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "security_group_rule",
        "approval_id": str(uuid4()),
        "request_hash": "",
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    request["request_hash"] = request_hash(request)
    with pytest.raises(RemediationContractError, match="unsupported"):
        create_proposal(
            request=request,
            action="describe_route_tables",
            evidence=[],
            proposed_at=datetime.now(UTC),
        )


def test_natural_language_or_unrecorded_approval_cannot_execute() -> None:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": "nacl_rule",
        "approval_id": str(uuid4()),
        "request_hash": "",
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    request["request_hash"] = request_hash(request)
    proposal = create_proposal(
        request=request,
        action="restore_network_acl_entry",
        evidence=[{"fact": "deny rule observed"}],
        proposed_at=datetime.now(UTC),
    )

    class Adapter:
        calls = 0

        def execute(self, proposal: object) -> dict[str, object]:
            self.calls += 1
            return {}

    adapter = Adapter()
    with pytest.raises(RemediationContractError):
        execute(
            request=request,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=datetime.now(UTC),
            store=InMemoryApprovalStore({}),
            adapter=adapter,
        )
    assert adapter.calls == 0


def test_approval_store_requires_explicit_recorded_decision() -> None:
    store = InMemoryApprovalStore({})
    assert store.approvals == {}
    with pytest.raises(RemediationContractError, match="approver"):
        record_approval(
            proposal={"proposal_id": str(uuid4())},
            approver_principal="",
            approved=True,
            approved_at=datetime.now(UTC),
            store=store,
        )
