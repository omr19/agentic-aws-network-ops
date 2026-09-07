"""Schema validation for the fixed diagnostic READ boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError  # type: ignore[import-untyped]
from referencing import Registry, Resource

LOCAL_SCHEMA_ROOT = Path(__file__).parents[3] / "schemas"


def _default_schema_root() -> Path:
    """Resolve schemas in local development or at the Lambda deployment root."""
    configured = os.environ.get("DIAGNOSTIC_SCHEMA_ROOT")
    if configured:
        return Path(configured)
    lambda_root = os.environ.get("LAMBDA_TASK_ROOT")
    if lambda_root:
        return Path(lambda_root) / "schemas"
    return LOCAL_SCHEMA_ROOT


class ContractError(ValueError):
    """Raised when a request or result violates a diagnostic contract."""


class ContractValidator:
    """Validate diagnostic payloads against the version-controlled schemas."""

    def __init__(self, schema_root: Path | None = None) -> None:
        schema_root = schema_root or _default_schema_root()
        common = self._load(schema_root / "common/result-envelope.schema.json")
        tools = self._load(schema_root / "diagnostic/read-tools.schema.json")
        self._tools_id = str(tools["$id"])
        self._registry = Registry().with_resources(
            (str(schema["$id"]), Resource.from_contents(schema)) for schema in (common, tools)
        )

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def _validate(self, definition: str, payload: dict[str, Any]) -> None:
        validator = Draft202012Validator(
            {"$ref": f"{self._tools_id}#/$defs/{definition}"},
            registry=self._registry,
            format_checker=FormatChecker(),
        )
        try:
            validator.validate(payload)
        except ValidationError as error:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            raise ContractError(f"contract validation failed at {path}: {error.message}") from None

    def validate_input(self, tool: str, payload: dict[str, Any]) -> None:
        self._validate(f"{tool}_input", payload)

    def validate_output(self, tool: str, payload: dict[str, Any]) -> None:
        self._validate(f"{tool}_output", payload)
