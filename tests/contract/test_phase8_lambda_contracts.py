"""Contract coverage for the new Lambda event schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

ROOT = Path(__file__).parents[2]


def schema(name: str) -> dict[str, object]:
    return cast(dict[str, object], json.loads((ROOT / "schemas/remediation" / name).read_text()))


def test_lambda_event_schemas_are_valid() -> None:
    for name in ("approval-lambda-event.schema.json", "remediation-lambda-event.schema.json"):
        Draft202012Validator.check_schema(schema(name))


def test_remediation_event_is_closed_world() -> None:
    validator = Draft202012Validator(
        schema("remediation-lambda-event.schema.json"), format_checker=FormatChecker()
    )
    payload = {
        "action": "restore_security_group_ingress",
        "request": {
            "schema_version": "1.0.0",
            "scenario_id": "security_group_rule",
            "approval_id": "00000000-0000-4000-8000-000000000001",
            "request_hash": "0" * 64,
            "correlation_id": "00000000-0000-4000-8000-000000000002",
            "policy_session_id": "00000000-0000-4000-8000-000000000003",
        },
        "execution_id": "00000000-0000-4000-8000-000000000004",
    }
    validator.validate(payload)
    payload["resource"] = "attacker"
    assert list(validator.iter_errors(payload))


def test_approval_lambda_event_excludes_caller_identity() -> None:
    validator = Draft202012Validator(
        schema("approval-lambda-event.schema.json"), format_checker=FormatChecker()
    )
    payload = {
        "operation": "approve",
        "proposal_id": "00000000-0000-4000-8000-000000000001",
        "approval_id": "00000000-0000-4000-8000-000000000002",
        "correlation_id": "00000000-0000-4000-8000-000000000003",
        "policy_session_id": "00000000-0000-4000-8000-000000000004",
        "request_hash": "0" * 64,
        "action": "restore_security_group_ingress",
        "resource": "${destination_security_group_id}",
        "remediation_operation": "AuthorizeSecurityGroupIngress",
    }
    validator.validate(payload)
    payload["approver_principal"] = "arn:aws:iam::000000000000:user/operator"
    assert list(validator.iter_errors(payload))
