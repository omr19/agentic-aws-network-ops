"""Contract tests for the normalized evidence and diagnosis result schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

ROOT = Path(__file__).parents[2]
COMMON = json.loads((ROOT / "schemas/common/result-envelope.schema.json").read_text())
EVIDENCE = json.loads((ROOT / "schemas/diagnostic/normalized-evidence.schema.json").read_text())
RESULT = json.loads((ROOT / "schemas/diagnostic/diagnosis-result.schema.json").read_text())


def validate(schema: dict[str, Any], payload: dict[str, Any]) -> None:
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)


def test_phase7_schemas_are_valid() -> None:
    Draft202012Validator.check_schema(EVIDENCE)
    Draft202012Validator.check_schema(RESULT)


def test_normalized_evidence_rejects_unknown_fields() -> None:
    payload = {
        "schema_version": "1.0.0",
        "correlation_id": "corr-test-0001",
        "observed_at": "2026-08-29T01:00:00Z",
        "region": "eu-west-1",
        "evidence_completeness": "complete",
        "reachability": {"status": "succeeded", "path_found": True, "explanation_codes": []},
        "execute_write": True,
    }
    try:
        validate(EVIDENCE, payload)
    except Exception as error:
        assert "execute_write" in str(error)
    else:
        raise AssertionError("unknown evidence fields must be rejected")
