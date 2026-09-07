"""Deterministic policy-contract tests for the separated Phase 5 identities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]
IAM_ROOT = ROOT / "iam/phase5"

EXPECTED_DIAGNOSTIC_ACTIONS = {
    "cloudwatch:GetMetricStatistics",
    "ec2:DescribeNetworkAcls",
    "ec2:DescribeNetworkInsightsAnalyses",
    "ec2:DescribeRouteTables",
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeSubnets",
    "ec2:DescribeVpcEndpoints",
    "ec2:DescribeVpcs",
    "logs:GetQueryResults",
    "logs:StartQuery",
}
FORBIDDEN_DIAGNOSTIC_ACTIONS = {
    "ec2:AcceptVpcPeeringConnection",
    "ec2:CreateNetworkInsightsPath",
    "ec2:CreateRoute",
    "ec2:ModifyNetworkInterfaceAttribute",
    "ec2:RevokeSecurityGroupIngress",
    "ec2:StartNetworkInsightsAnalysis",
    "ec2:StopInstances",
    "ec2:TerminateInstances",
    "iam:PassRole",
    "lambda:InvokeFunction",
    "sts:AssumeRole",
}


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((IAM_ROOT / name).read_text(encoding="utf-8")))


def allowed_actions(policy: dict[str, Any]) -> set[str]:
    actions: set[str] = set()
    for statement in policy["Statement"]:
        if statement["Effect"] != "Allow":
            continue
        value = statement["Action"]
        actions.update([value] if isinstance(value, str) else value)
    return actions


def normalized_statements(policy: dict[str, Any]) -> set[str]:
    return {
        json.dumps(statement, sort_keys=True)
        for statement in policy["Statement"]
        if statement["Effect"] == "Allow"
    }


def test_three_execution_identities_have_separate_trust_contracts() -> None:
    expected_principals = {
        "runtime-trust.json": "bedrock-agentcore.amazonaws.com",
        "gateway-trust.json": "bedrock-agentcore.amazonaws.com",
        "diagnostic-trust.json": "lambda.amazonaws.com",
    }
    for filename, principal in expected_principals.items():
        policy = load(filename)
        assert len(policy["Statement"]) == 1
        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        assert statement["Principal"] == {"Service": principal}
        assert statement["Action"] == "sts:AssumeRole"
        if filename != "diagnostic-trust.json":
            assert statement["Condition"] == {
                "StringEquals": {"aws:SourceAccount": "${account_id}"},
                "ArnLike": {"aws:SourceArn": "arn:aws:bedrock-agentcore:${region}:${account_id}:*"},
            }


def test_runtime_can_invoke_only_one_scoped_gateway() -> None:
    policy = load("runtime-permissions.json")
    assert allowed_actions(policy) == {"bedrock-agentcore:InvokeGateway"}
    assert normalized_statements(policy) == {
        json.dumps(
            {
                "Sid": "InvokeOnlyApprovedDiagnosticGateway",
                "Effect": "Allow",
                "Action": "bedrock-agentcore:InvokeGateway",
                "Resource": (
                    "arn:aws:bedrock-agentcore:${region}:${account_id}:gateway/${gateway_id}"
                ),
            },
            sort_keys=True,
        )
    }


def test_gateway_can_invoke_only_one_scoped_diagnostic_target() -> None:
    policy = load("gateway-permissions.json")
    assert allowed_actions(policy) == {"lambda:InvokeFunction"}
    assert normalized_statements(policy) == {
        json.dumps(
            {
                "Sid": "InvokeOnlyDiagnosticTarget",
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": (
                    "arn:aws:lambda:${region}:${account_id}:function:${diagnostic_function_name}"
                ),
            },
            sort_keys=True,
        )
    }


def test_diagnostic_policy_allows_exactly_the_required_evidence_actions() -> None:
    policy = load("diagnostic-read-permissions.json")
    assert allowed_actions(policy) == EXPECTED_DIAGNOSTIC_ACTIONS
    assert len(policy["Statement"]) == 3
    assert all(statement["Effect"] == "Allow" for statement in policy["Statement"])


def test_diagnostic_policy_has_zero_remediation_or_privilege_escalation_actions() -> None:
    actions = allowed_actions(load("diagnostic-read-permissions.json"))
    assert actions.isdisjoint(FORBIDDEN_DIAGNOSTIC_ACTIONS)
    assert not any(action.startswith(("iam:", "sts:", "lambda:")) for action in actions)
    assert not any("*" in action for action in actions)


def test_diagnostic_policy_scopes_region_and_project_log_group() -> None:
    statements = load("diagnostic-read-permissions.json")["Statement"]
    assert all(
        statement["Condition"] == {"StringEquals": {"aws:RequestedRegion": "${region}"}}
        for statement in statements
    )
    logs_statement = next(
        statement
        for statement in statements
        if statement["Sid"] == "StartOnlyProjectFlowLogQueries"
    )
    assert "${diagnostic_log_group_name}" in logs_statement["Resource"]
    assert logs_statement["Resource"] != "*"
    assert logs_statement["Action"] == "logs:StartQuery"
