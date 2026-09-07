"""Closed-world contract tests for the local Phase 8 remediation foundation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]

ROOT = Path(__file__).parents[2]
SCHEMA_DIR = ROOT / "schemas/remediation"
SCHEMAS = {
    path.name.removesuffix(".schema.json"): json.loads(path.read_text())
    for path in SCHEMA_DIR.glob("*.json")
}


def validate(name: str, payload: dict[str, Any]) -> None:
    Draft202012Validator(SCHEMAS[name], format_checker=FormatChecker()).validate(payload)


def test_phase8_schemas_are_valid() -> None:
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)


def test_request_rejects_arbitrary_aws_parameters() -> None:
    payload = {
        "schema_version": "1.0.0",
        "scenario_id": "security_group_rule",
        "approval_id": "00000000-0000-4000-8000-000000000001",
        "request_hash": "0" * 64,
        "correlation_id": "00000000-0000-4000-8000-000000000002",
        "policy_session_id": "00000000-0000-4000-8000-000000000003",
        "execute": True,
    }
    with pytest.raises(ValidationError):
        validate("request", payload)


def test_execution_and_verification_results_are_separate_contracts() -> None:
    validate(
        "execution-result",
        {
            "schema_version": "1.0.0",
            "execution_id": "00000000-0000-4000-8000-000000000004",
            "correlation_id": "00000000-0000-4000-8000-000000000002",
            "approval_id": "00000000-0000-4000-8000-000000000001",
            "status": "completed",
            "write_performed": True,
            "terraform_drift": True,
            "reconciliation_required": True,
        },
    )
    validate(
        "verification-result",
        {
            "schema_version": "1.0.0",
            "correlation_id": "00000000-0000-4000-8000-000000000002",
            "execution_id": "00000000-0000-4000-8000-000000000004",
            "status": "verified",
            "remediation_fact": "Approved rule is present.",
        },
    )
