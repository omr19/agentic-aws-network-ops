"""Local least-privilege tests for the future Phase 7 observability role."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]
POLICY_PATH = ROOT / "iam/phase7/observability-read-permissions.json"

EXPECTED_OBSERVABILITY_ACTIONS = {
    "cloudwatch:GetMetricData",
    "cloudwatch:GetMetricStatistics",
    "cloudwatch:ListMetrics",
    "ec2:DescribeFlowLogs",
    "ec2:DescribeInstances",
    "ec2:DescribeTags",
    "logs:DescribeLogGroups",
    "logs:GetQueryResults",
    "logs:StartQuery",
}
FORBIDDEN_OBSERVABILITY_ACTIONS = {
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:CreateNetworkInsightsPath",
    "ec2:CreateRoute",
    "ec2:DeleteNetworkAclEntry",
    "ec2:DeleteRoute",
    "ec2:ModifyNetworkInterfaceAttribute",
    "ec2:ReplaceNetworkAclEntry",
    "ec2:ReplaceRoute",
    "ec2:RevokeSecurityGroupIngress",
    "ec2:StartNetworkInsightsAnalysis",
    "ec2:StartInstances",
    "ec2:StopInstances",
    "ec2:TerminateInstances",
    "ec2:AcceptVpcPeeringConnection",
    "ec2:RejectVpcPeeringConnection",
    "iam:PassRole",
    "iam:CreateRole",
    "iam:AttachRolePolicy",
    "lambda:InvokeFunction",
    "sts:AssumeRole",
}


def load_policy() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(POLICY_PATH.read_text(encoding="utf-8")))


def allowed_actions(policy: dict[str, Any]) -> set[str]:
    actions: set[str] = set()
    for statement in policy["Statement"]:
        if statement["Effect"] != "Allow":
            continue
        value = statement["Action"]
        actions.update([value] if isinstance(value, str) else value)
    return actions


def test_observability_policy_allows_only_minimum_read_actions() -> None:
    policy = load_policy()
    assert allowed_actions(policy) == EXPECTED_OBSERVABILITY_ACTIONS
    assert all(statement["Effect"] == "Allow" for statement in policy["Statement"])
    assert len(policy["Statement"]) == 5


def test_observability_policy_explicitly_denies_privileged_and_write_actions() -> None:
    actions = allowed_actions(load_policy())
    assert actions.isdisjoint(FORBIDDEN_OBSERVABILITY_ACTIONS)
    assert not any(action.startswith(("iam:", "sts:", "lambda:")) for action in actions)
    assert not any(
        action.endswith(("CreateRoute", "ReplaceRoute", "StartInstances")) for action in actions
    )
    assert not any("*" in action for action in actions)


def test_observability_policy_scopes_region_and_supported_log_resources() -> None:
    statements = load_policy()["Statement"]
    assert all(
        statement["Condition"]["StringEquals"] == {"aws:RequestedRegion": "${region}"}
        for statement in statements
    )
    discovery = next(
        statement for statement in statements if statement["Sid"] == "DiscoverProjectLogGroups"
    )
    assert discovery["Resource"] == "*"
    assert discovery["Condition"]["StringLike"] == {
        "logs:LogGroupName": "/aws/vpc/flowlogs/${project_tag}/*"
    }
    query = next(
        statement
        for statement in statements
        if statement["Sid"] == "QueryOnlyProjectObservabilityLogs"
    )
    assert query["Resource"] == (
        "arn:aws:logs:${region}:${account_id}:log-group:${observability_log_group_name}:*"
    )


def test_observability_policy_does_not_modify_existing_identity_contracts() -> None:
    diagnostic = json.loads(
        (ROOT / "iam/phase5/diagnostic-read-permissions.json").read_text(encoding="utf-8")
    )
    runtime = json.loads((ROOT / "iam/phase5/runtime-permissions.json").read_text(encoding="utf-8"))
    assert allowed_actions(diagnostic) != allowed_actions(load_policy())
    assert allowed_actions(runtime).isdisjoint(allowed_actions(load_policy()))
