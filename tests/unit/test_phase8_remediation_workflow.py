"""Deterministic parameterized tests for the Phase 8 remediation workflow."""

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
ACTION_CASES = [
    pytest.param(
        "security_group_rule",
        "restore_security_group_ingress",
        "AuthorizeSecurityGroupIngress",
        {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_ip": "10.10.0.0/16"},
        id="security-group-ingress",
    ),
    pytest.param(
        "route_table_entry",
        "restore_vpc_peering_route",
        "CreateRoute",
        {
            "route_table_id": "rtb-source",
            "destination_cidr": "10.20.0.0/16",
            "vpc_peering_connection_id": "pcx-project",
        },
        id="peering-route",
    ),
    pytest.param(
        "nacl_rule",
        "restore_network_acl_entry",
        "ReplaceNetworkAclEntry",
        {
            "rule_number": 100,
            "egress": False,
            "protocol": "tcp",
            "from_port": 443,
            "to_port": 443,
            "cidr_block": "10.10.0.0/16",
            "rule_action": "allow",
        },
        id="network-acl-entry",
    ),
]


def make_request(scenario: str) -> dict[str, str]:
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


def make_proposal(request: Mapping[str, object], action: str) -> dict[str, object]:
    return create_proposal(
        request=request,
        action=action,
        evidence=[{"fact": "The approved corrective state is absent."}],
        proposed_at=NOW,
    )


class FakeAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, proposal: object) -> dict[str, object]:
        self.calls += 1
        return {"status": "completed", "write_performed": True}


class FakeVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, proposal: object) -> dict[str, object]:
        self.calls += 1
        return {"status": "verified", "remediation_fact": "Approved state is present."}


class FailingVerifier:
    def __init__(self, *, raises: bool) -> None:
        self.calls = 0
        self.raises = raises

    def verify(self, proposal: object) -> dict[str, object]:
        del proposal
        self.calls += 1
        if self.raises:
            raise TimeoutError("injected verification timeout")
        return {"status": "failed", "remediation_fact": "Approved state is absent."}


def approve(
    proposal: dict[str, object], store: InMemoryApprovalStore, decision: bool = True
) -> None:
    record_approval(
        proposal=proposal,
        approver_principal="human@example",
        approved=decision,
        approved_at=NOW,
        store=store,
        authorized_approvers={"human@example"},
    )


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_proposal_creation_has_no_write_side_effect(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    store = InMemoryApprovalStore({})
    adapter = FakeAdapter()
    proposal = make_proposal(make_request(scenario), action)
    assert proposal["action"] == action
    assert adapter.calls == 0
    assert store.approvals == {}


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_missing_approval_is_denied_without_adapter_call(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
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


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_explicit_denial_causes_no_adapter_call(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
    store = InMemoryApprovalStore({})
    approve(proposal, store, decision=False)
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


@pytest.mark.parametrize("binding_field", ["correlation_id", "policy_session_id", "request_hash"])
@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_wrong_binding_is_denied_without_adapter_call(
    binding_field: str,
    scenario: str,
    action: str,
    operation: str,
    parameters: dict[str, object],
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
    store = InMemoryApprovalStore({})
    approve(proposal, store)
    wrong = dict(request)
    wrong[binding_field] = str(uuid4())
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


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_expired_approval_is_denied_without_adapter_call(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
    store = InMemoryApprovalStore({})
    approve(proposal, store)
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


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_approval_replay_performs_at_most_one_write(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
    store = InMemoryApprovalStore({})
    approve(proposal, store)
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


@pytest.mark.parametrize("scenario,action,operation,parameters", ACTION_CASES)
def test_successful_execution_has_separate_bound_verification_and_drift(
    scenario: str, action: str, operation: str, parameters: dict[str, object]
) -> None:
    request = make_request(scenario)
    proposal = make_proposal(request, action)
    store = InMemoryApprovalStore({})
    approve(proposal, store)
    adapter = FakeAdapter()
    result = execute(
        request=request,
        proposal=proposal,
        execution_id=str(uuid4()),
        now=NOW,
        store=store,
        adapter=adapter,
    )
    verifier = FakeVerifier()
    verified = verify(proposal=proposal, execution_result=result, verifier=verifier)
    assert result["terraform_drift"] is True
    assert result["reconciliation_required"] is True
    assert verified["status"] == "verified"
    assert verifier.calls == 1
    assert adapter.calls == 1
    with pytest.raises(RemediationContractError, match="correlation_id"):
        verify(
            proposal=proposal,
            execution_result=dict(result, correlation_id=str(uuid4())),
            verifier=verifier,
        )


@pytest.mark.parametrize("raises", [False, True], ids=["failed-result", "exception"])
def test_verification_failure_is_preserved_without_a_second_write(raises: bool) -> None:
    request = make_request("security_group_rule")
    proposal = make_proposal(request, "restore_security_group_ingress")
    store = InMemoryApprovalStore({})
    approve(proposal, store)
    adapter = FakeAdapter()
    execution_result = execute(
        request=request,
        proposal=proposal,
        execution_id=str(uuid4()),
        now=NOW,
        store=store,
        adapter=adapter,
    )
    verifier = FailingVerifier(raises=raises)

    if raises:
        with pytest.raises(TimeoutError, match="injected verification timeout"):
            verify(
                proposal=proposal,
                execution_result=execution_result,
                verifier=verifier,
            )
    else:
        result = verify(
            proposal=proposal,
            execution_result=execution_result,
            verifier=verifier,
        )
        assert result["status"] == "failed"
        assert result["remediation_fact"] == "Approved state is absent."
    assert verifier.calls == 1
    assert adapter.calls == 1


def test_peering_dns_and_caller_supplied_aws_fields_are_not_supported() -> None:
    request = make_request("peering_routes_dns")
    with pytest.raises(RemediationContractError, match="unsupported remediation"):
        make_proposal(request, "restore_vpc_peering_route")

    request = make_request("security_group_rule")
    with pytest.raises(TypeError):
        create_proposal(  # type: ignore[call-arg]
            request=request,
            action="restore_security_group_ingress",
            evidence=[],
            proposed_at=NOW,
            resource="arbitrary-security-group",
        )

    request = make_request("route_table_entry")
    with pytest.raises(TypeError):
        create_proposal(  # type: ignore[call-arg]
            request=request,
            action="restore_vpc_peering_route",
            evidence=[],
            proposed_at=NOW,
            parameters={"destination_cidr": "0.0.0.0/0"},
        )

    request = make_request("nacl_rule")
    with pytest.raises(TypeError):
        create_proposal(  # type: ignore[call-arg]
            request=request,
            action="restore_network_acl_entry",
            evidence=[],
            proposed_at=NOW,
            operation="DeleteNetworkAclEntry",
        )
