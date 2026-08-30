from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).parents[2]
POLICY_PATH = ROOT / "iam/phase8/remediation-read-permissions.json"
APPROVED_ACTIONS = {
    "ec2:DescribeSecurityGroups",
    "ec2:DescribeRouteTables",
    "ec2:DescribeNetworkAcls",
}


def load_policy() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(POLICY_PATH.read_text(encoding="utf-8")))


def test_policy_allows_only_the_remediation_read_actions() -> None:
    policy = load_policy()
    assert set(policy) == {"Version", "Statement"}
    assert policy["Version"] == "2012-10-17"
    assert len(policy["Statement"]) == 1

    statement = policy["Statement"][0]
    assert set(statement) == {"Sid", "Effect", "Action", "Resource", "Condition"}
    assert statement["Sid"] == "RemediationReadPreflightAndVerification"
    assert statement["Effect"] == "Allow"
    assert len(statement["Action"]) == len(APPROVED_ACTIONS)
    assert set(statement["Action"]) == APPROVED_ACTIONS
    assert statement["Resource"] == "*"
    assert statement["Condition"] == {
        "StringEquals": {"aws:RequestedRegion": "eu-west-1"}
    }


def test_policy_has_no_write_or_unrelated_capabilities() -> None:
    statement = load_policy()["Statement"][0]
    actions = statement["Action"]
    assert all(action in APPROVED_ACTIONS for action in actions)
    assert not any("*" in action for action in actions)
    assert not any(
        action.startswith(("iam:", "lambda:", "logs:", "sts:")) for action in actions
    )
    assert "Principal" not in statement
