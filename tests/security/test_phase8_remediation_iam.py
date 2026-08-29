"""Offline least-privilege tests for the unattached Phase 8 WRITE policy fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]
POLICY_PATH = ROOT / "iam/phase8/remediation-write-permissions.json"
APPROVED_ACTIONS = {
    "ec2:AuthorizeSecurityGroupIngress",
    "ec2:CreateRoute",
    "ec2:ReplaceRoute",
    "ec2:ReplaceNetworkAclEntry",
}
PROHIBITED_ACTIONS = {
    "ec2:RevokeSecurityGroupIngress",
    "ec2:DeleteRoute",
    "ec2:DeleteNetworkAclEntry",
    "ec2:AcceptVpcPeeringConnection",
    "ec2:RejectVpcPeeringConnection",
    "ec2:ModifyVpcPeeringConnectionOptions",
    "ec2:CreateVpcPeeringConnection",
    "ec2:DeleteVpcPeeringConnection",
    "ec2:StartInstances",
    "ec2:StopInstances",
    "ec2:TerminateInstances",
    "ec2:CreateNatGateway",
    "ec2:DeleteNatGateway",
    "ec2:CreateInternetGateway",
    "ec2:AttachInternetGateway",
    "ec2:DetachInternetGateway",
    "ec2:DeleteInternetGateway",
    "ec2:CreateVpcEndpoint",
    "ec2:DeleteVpcEndpoints",
    "ec2:CreateTransitGateway",
    "ec2:DeleteTransitGateway",
    "ec2:CreateNetworkAcl",
    "ec2:DeleteNetworkAcl",
    "iam:PassRole",
    "iam:CreateRole",
    "iam:AttachRolePolicy",
    "lambda:InvokeFunction",
    "logs:CreateLogGroup",
    "ec2:CreateFlowLogs",
    "sts:AssumeRole",
}
REQUIRED_TAG_CONDITIONS = {
    "aws:ResourceTag/Project": "agentic-aws-network-ops",
    "aws:ResourceTag/Environment": "lab",
    "aws:ResourceTag/ManagedBy": "terraform",
}


def load_policy() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(POLICY_PATH.read_text(encoding="utf-8")))


def allowed_actions(policy: dict[str, Any]) -> set[str]:
    actions: set[str] = set()
    for statement in policy["Statement"]:
        assert statement["Effect"] == "Allow"
        value = statement["Action"]
        actions.update([value] if isinstance(value, str) else value)
    return actions


def test_policy_allows_exactly_the_approved_remediation_capabilities() -> None:
    policy = load_policy()
    assert allowed_actions(policy) == APPROVED_ACTIONS
    assert len(policy["Statement"]) == 3
    assert all(statement["Effect"] == "Allow" for statement in policy["Statement"])


def test_policy_denies_all_prohibited_actions_by_absence() -> None:
    actions = allowed_actions(load_policy())
    assert actions.isdisjoint(PROHIBITED_ACTIONS)
    assert not any(action.startswith(("iam:", "lambda:", "logs:", "sts:")) for action in actions)
    assert not any("*" in action for action in actions)


def test_policy_scopes_each_capability_to_exact_resources_and_tags() -> None:
    statements = load_policy()["Statement"]
    for statement in statements:
        assert statement["Condition"]["StringEquals"]["aws:RequestedRegion"] == "eu-west-1"
        for key, value in REQUIRED_TAG_CONDITIONS.items():
            assert statement["Condition"]["StringEquals"][key] == value
        resources = statement["Resource"]
        resources = [resources] if isinstance(resources, str) else resources
        assert resources
        assert all(resource.startswith("arn:aws:ec2:") for resource in resources)
        assert all("${account_id}" in resource for resource in resources)


def test_security_group_and_nacl_are_vpc_bound_and_route_scope_is_bilateral() -> None:
    statements = load_policy()["Statement"]
    security_group = next(
        statement
        for statement in statements
        if statement["Sid"] == "RestoreApprovedSecurityGroupIngress"
    )
    network_acl = next(
        statement
        for statement in statements
        if statement["Sid"] == "RestoreApprovedNetworkAclEntry"
    )
    routes = next(
        statement for statement in statements if statement["Sid"] == "RestoreApprovedPeeringRoutes"
    )

    assert security_group["Condition"]["StringEquals"]["ec2:Vpc"] == "${destination_vpc_id}"
    assert network_acl["Condition"]["StringEquals"]["ec2:Vpc"] == "${destination_vpc_id}"
    assert set(routes["Action"]) == {"ec2:CreateRoute", "ec2:ReplaceRoute"}
    assert len(routes["Resource"]) == 2
    assert all("route-table/" in resource for resource in routes["Resource"])


def test_policy_is_unattached_permission_fixture_only() -> None:
    policy = load_policy()
    assert set(policy) == {"Version", "Statement"}
    assert all("Principal" not in statement for statement in policy["Statement"])
