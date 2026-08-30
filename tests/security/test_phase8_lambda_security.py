"""Security tests for Phase 8 Lambda boundaries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from agentic_aws_network_ops.approval.lambda_interface import (
    ApprovalLambdaError,
    handle_approval_event,
)
from agentic_aws_network_ops.approval.repository import InMemoryApprovalRepository
from agentic_aws_network_ops.approval.service import ApprovalService
from agentic_aws_network_ops.remediation.lambda_interface import (
    RemediationLambdaError,
    handle_remediation_event,
)

NOW = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)


def test_approval_interface_cannot_execute_or_accept_extra_fields() -> None:
    event = {
        "operation": "approve",
        "proposal_id": str(uuid4()),
        "approval_id": str(uuid4()),
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "request_hash": "c" * 64,
        "action": "restore_vpc_peering_route",
        "resource": "route-table",
        "remediation_operation": "CreateRouteOrReplaceRoute",
        "approver_principal": "arn:aws:iam::000000000000:user/operator",
        "execute": True,
    }
    with pytest.raises(ApprovalLambdaError):
        handle_approval_event(
            event,
            service=ApprovalService(
                InMemoryApprovalRepository(), {cast(str, event["approver_principal"])}
            ),
            now=NOW,
        )


def test_remediation_interface_rejects_model_supplied_resource_and_parameters() -> None:
    request = {
        "scenario_id": "security_group_rule",
        "approval_id": str(uuid4()),
        "request_hash": "d" * 64,
        "correlation_id": str(uuid4()),
        "policy_session_id": str(uuid4()),
        "resource": "attacker-resource",
        "parameters": {"cidr_ip": "0.0.0.0/0"},
    }
    with pytest.raises(RemediationLambdaError):
        handle_remediation_event(
            {
                "action": "restore_security_group_ingress",
                "request": request,
                "execution_id": str(uuid4()),
            },
            executor=cast(Any, object()),
            now=NOW,
        )
