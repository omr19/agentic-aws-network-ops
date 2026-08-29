"""Deterministic unit tests for proposal, approval, execution, and verification."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from agentic_aws_network_ops.remediation.workflow import (
    InMemoryApprovalStore,
    RemediationContractError,
    create_proposal,
    execute,
    record_approval,
    request_hash,
    verify,
)

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


def make_request(scenario: str = "security_group_rule") -> dict[str, str]:
    request = {
        "schema_version": "1.0.0",
        "scenario_id": scenario,
        "approval_id": str(uuid4()),
        "request_hash": "",
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
    }
    request["request_hash"] = request_hash(request)
    return request


def make_proposal(request: Mapping[str, object]) -> dict[str, object]:
    return create_proposal(
        request=request,
        action="restore_security_group_ingress",
        region="eu-west-1",
        resource="destination-security-group",
        operation="AuthorizeSecurityGroupIngress",
        parameters={"protocol": "tcp", "port": 443, "source_cidr": "10.10.0.0/16"},
        evidence=[{"fact": "The approved ingress rule is absent."}],
        expected_result="TCP/443 ingress is restored.",
        proposed_at=NOW,
    )


class FakeAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, proposal: object) -> dict[str, object]:
        self.calls += 1
        return {"status": "completed", "write_performed": True}


class FakeVerifier:
    def verify(self, proposal: object) -> dict[str, object]:
        return {"status": "verified", "remediation_fact": "Rule is present."}


def approve(
    request: dict[str, str],
    proposal: dict[str, object],
    store: InMemoryApprovalStore,
    decision: bool = True,
) -> None:
    record_approval(
        proposal=proposal,
        approver_principal="human@example",
        approved=decision,
        approved_at=NOW,
        store=store,
    )


def test_proposal_does_not_execute() -> None:
    store = InMemoryApprovalStore({})
    adapter = FakeAdapter()
    proposal = make_proposal(make_request())
    assert proposal["action"] == "restore_security_group_ingress"
    assert adapter.calls == 0
    assert store.approvals == {}


def test_missing_approval_denies_without_write() -> None:
    request = make_request()
    proposal = make_proposal(request)
    adapter = FakeAdapter()
    with pytest.raises(RemediationContractError, match="approval is required"):
        execute(
            request=request,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=NOW,
            store=InMemoryApprovalStore({}),
            adapter=adapter,
        )
    assert adapter.calls == 0


def test_denial_produces_no_write() -> None:
    request = make_request()
    proposal = make_proposal(request)
    store = InMemoryApprovalStore({})
    approve(request, proposal, store, decision=False)
    adapter = FakeAdapter()
    with pytest.raises(RemediationContractError, match="does not permit"):
        execute(
            request=request,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=NOW,
            store=store,
            adapter=adapter,
        )
    assert adapter.calls == 0


def test_wrong_correlation_id_is_denied_without_write() -> None:
    request = make_request()
    proposal = make_proposal(request)
    store = InMemoryApprovalStore({})
    approve(request, proposal, store)
    wrong = dict(request, correlation_id=str(uuid4()))
    wrong["request_hash"] = request_hash(wrong)
    adapter = FakeAdapter()
    with pytest.raises(RemediationContractError):
        execute(
            request=wrong,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=NOW,
            store=store,
            adapter=adapter,
        )
    assert adapter.calls == 0


def test_expired_approval_is_denied_without_write() -> None:
    request = make_request()
    proposal = make_proposal(request)
    store = InMemoryApprovalStore({})
    approve(request, proposal, store)
    adapter = FakeAdapter()
    with pytest.raises(RemediationContractError, match="expired"):
        execute(
            request=request,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=NOW + timedelta(minutes=5),
            store=store,
            adapter=adapter,
        )
    assert adapter.calls == 0


def test_approval_replay_is_denied_and_only_one_write_occurs() -> None:
    request = make_request()
    proposal = make_proposal(request)
    store = InMemoryApprovalStore({})
    approve(request, proposal, store)
    adapter = FakeAdapter()
    execute(
        request=request,
        proposal=proposal,
        execution_id=str(uuid4()),
        now=NOW,
        store=store,
        adapter=adapter,
    )
    with pytest.raises(RemediationContractError, match="already consumed"):
        execute(
            request=request,
            proposal=proposal,
            execution_id=str(uuid4()),
            now=NOW,
            store=store,
            adapter=adapter,
        )
    assert adapter.calls == 1


def test_unsupported_action_and_malformed_request_are_rejected() -> None:
    request = make_request()
    malformed: dict[str, object] = {**request, "unexpected": True}
    with pytest.raises(RemediationContractError, match="exactly"):
        make_proposal(malformed)
    with pytest.raises(RemediationContractError, match="unsupported"):
        create_proposal(
            request=request,
            action="execute_arbitrary_aws",
            region="eu-west-1",
            resource="anything",
            operation="DeleteRoute",
            parameters={"route_table_id": "rtb"},
            evidence=[],
            expected_result="bad",
            proposed_at=NOW,
        )


def test_verification_is_separate_and_bound_to_correlation() -> None:
    request = make_request()
    proposal = make_proposal(request)
    store = InMemoryApprovalStore({})
    approve(request, proposal, store)
    result = execute(
        request=request,
        proposal=proposal,
        execution_id=str(uuid4()),
        now=NOW,
        store=store,
        adapter=FakeAdapter(),
    )
    verified = verify(proposal=proposal, execution_result=result, verifier=FakeVerifier())
    assert verified["status"] == "verified"
    with pytest.raises(RemediationContractError, match="correlation_id"):
        verify(
            proposal=proposal,
            execution_result=dict(result, correlation_id=str(uuid4())),
            verifier=FakeVerifier(),
        )
