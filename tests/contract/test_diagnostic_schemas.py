"""Contract tests for the nine approved read-only diagnostic tools."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from jsonschema import (  # type: ignore[import-untyped]
    Draft202012Validator,
    FormatChecker,
    ValidationError,
)
from referencing import Registry, Resource

from agentic_aws_network_ops.diagnostics.contracts import ContractValidator

ROOT = Path(__file__).parents[2]
COMMON_PATH = ROOT / "schemas/common/result-envelope.schema.json"
TOOLS_PATH = ROOT / "schemas/diagnostic/read-tools.schema.json"

COMMON = json.loads(COMMON_PATH.read_text())
TOOLS = json.loads(TOOLS_PATH.read_text())
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in (COMMON, TOOLS)
)

BASE = {"schema_version": "1.0.0", "correlation_id": "corr-test-0001", "region": "eu-west-1"}
VALID_INPUTS: dict[str, dict[str, Any]] = {
    "describe_vpcs": {**BASE, "project_tag": "agentic-aws-network-ops"},
    "describe_subnets": {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
    "describe_route_tables": {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
    "describe_security_groups": {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
    "describe_network_acls": {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
    "describe_vpc_endpoints": {**BASE, "vpc_id": "vpc-0123456789abcdef0"},
    "analyze_reachability": {**BASE, "network_insights_path_id": "nip-0123456789abcdef0"},
    "query_flow_logs": {
        **BASE,
        "log_group_name": "/aws/vpc/flowlogs/agentic-aws-network-ops/lab",
        "start_time": "2026-08-28T18:00:00Z",
        "end_time": "2026-08-28T18:05:00Z",
    },
    "get_cloudwatch_metrics": {
        **BASE,
        "namespace": "AWS/EC2",
        "metric_name": "NetworkPacketsIn",
        "start_time": "2026-08-28T18:00:00Z",
        "end_time": "2026-08-28T18:05:00Z",
        "period": 60,
        "statistic": "Sum",
    },
}
VALID_OUTPUT_DATA: dict[str, dict[str, Any]] = {
    **{tool: {"resources": []} for tool in tuple(VALID_INPUTS)[:6]},
    "analyze_reachability": {
        "analysis_status": "succeeded",
        "path_found": True,
        "explanations": [],
    },
    "query_flow_logs": {"query_status": "complete", "records": []},
    "get_cloudwatch_metrics": {"datapoints": []},
}


def validator(definition: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"{TOOLS['$id']}#/$defs/{definition}"},
        registry=REGISTRY,
        format_checker=FormatChecker(),
    )


def test_schemas_are_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(COMMON)
    Draft202012Validator.check_schema(TOOLS)


def test_runtime_schema_root_is_independent_of_repository_layout(
    monkeypatch: Any, tmp_path: Path
) -> None:
    deployed_schemas = tmp_path / "deployment/schemas"
    shutil.copytree(ROOT / "schemas", deployed_schemas)
    monkeypatch.setenv("DIAGNOSTIC_SCHEMA_ROOT", str(deployed_schemas))
    monkeypatch.chdir(tmp_path)
    ContractValidator().validate_input("describe_vpcs", VALID_INPUTS["describe_vpcs"])


@pytest.mark.parametrize(("tool", "payload"), VALID_INPUTS.items())
def test_valid_tool_input(tool: str, payload: dict[str, Any]) -> None:
    validator(f"{tool}_input").validate(payload)


@pytest.mark.parametrize(("tool", "payload"), VALID_INPUTS.items())
def test_inputs_reject_unknown_fields(tool: str, payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        validator(f"{tool}_input").validate({**payload, "aws_api": "execute-anything"})


@pytest.mark.parametrize("tool", VALID_INPUTS)
def test_inputs_reject_invalid_region(tool: str) -> None:
    with pytest.raises(ValidationError):
        validator(f"{tool}_input").validate({**VALID_INPUTS[tool], "region": "not-a-region"})


@pytest.mark.parametrize("status", COMMON["properties"]["status"]["enum"])
def test_result_envelope_supports_each_required_status(status: str) -> None:
    payload = {
        "schema_version": "1.0.0",
        "tool": "describe_vpcs",
        "status": status,
        "correlation_id": "corr-test-0001",
        "observed_at": "2026-08-28T18:00:00Z",
        "region": "eu-west-1",
        "authorization": {"decision": "allowed", "missing_actions": []},
        "evidence_completeness": "complete",
        "evidence": [],
        "limitations": [],
        "errors": [],
        "data": {},
    }
    Draft202012Validator(COMMON, format_checker=FormatChecker()).validate(payload)


@pytest.mark.parametrize("tool", VALID_INPUTS)
def test_tool_output_is_bound_to_its_contract_name(tool: str) -> None:
    payload = {
        "schema_version": "1.0.0",
        "tool": tool,
        "status": "success",
        "correlation_id": "corr-test-0001",
        "observed_at": "2026-08-28T18:00:00Z",
        "region": "eu-west-1",
        "authorization": {"decision": "allowed", "missing_actions": []},
        "evidence_completeness": "complete",
        "evidence": [],
        "limitations": [],
        "errors": [],
        "data": VALID_OUTPUT_DATA[tool],
    }
    validator(f"{tool}_output").validate(payload)
    with pytest.raises(ValidationError):
        validator(f"{tool}_output").validate({**payload, "tool": "execute_boto3"})


def test_result_envelope_rejects_raw_stack_trace_field() -> None:
    payload = {
        "schema_version": "1.0.0",
        "tool": "describe_vpcs",
        "status": "api_error",
        "correlation_id": "corr-test-0001",
        "observed_at": "2026-08-28T18:00:00Z",
        "region": "eu-west-1",
        "authorization": {"decision": "unknown", "missing_actions": []},
        "evidence_completeness": "none",
        "evidence": [],
        "limitations": [],
        "errors": [{"code": "API_ERROR", "message": "AWS request failed", "retryable": False}],
        "data": {},
        "stack_trace": "sensitive implementation detail",
    }
    with pytest.raises(ValidationError):
        Draft202012Validator(COMMON).validate(payload)
