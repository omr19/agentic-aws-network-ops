"""Offline composition test for Runtime -> Gateway -> diagnostic READ."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import boto3  # type: ignore[import-untyped]
from botocore.stub import Stubber  # type: ignore[import-untyped]

from agentic_aws_network_ops.adapters.gateway import (
    LocalDiagnosticLambdaTarget,
    LocalGatewayAdapter,
)
from agentic_aws_network_ops.agent.runtime import FixedToolSelector, Runtime
from agentic_aws_network_ops.diagnostics.service import DiagnosticClients, DiagnosticService
from agentic_aws_network_ops.shared.boundaries import RuntimeRequest

FIXTURES = Path(__file__).parents[1] / "fixtures/events"
REGION = "eu-west-1"


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def client(service: str) -> Any:
    return boto3.client(
        service,
        region_name=REGION,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",  # noqa: S106 - inert Stubber credential
        aws_session_token="testing",  # noqa: S106 - inert Stubber credential
    )


def test_local_runtime_gateway_diagnostic_path_uses_only_stubbed_read_api() -> None:
    ec2 = client("ec2")
    diagnostic = DiagnosticService(
        DiagnosticClients(ec2=ec2, logs=client("logs"), cloudwatch=client("cloudwatch"))
    )
    gateway = LocalGatewayAdapter(LocalDiagnosticLambdaTarget(diagnostic))
    runtime = Runtime(
        FixedToolSelector(
            "describe_vpcs",
            {"schema_version": "1.0.0", "project_tag": "agentic-aws-network-ops"},
        ),
        gateway,
    )
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))

    with Stubber(ec2) as stubber:
        stubber.add_response(
            "describe_vpcs",
            {"Vpcs": [{"VpcId": "vpc-0123456789abcdef0"}]},
            {"Filters": [{"Name": "tag:Project", "Values": ["agentic-aws-network-ops"]}]},
        )
        response = runtime.handle(request)

    assert response.accepted is True
    assert response.result is not None
    assert response.result["tool"] == "describe_vpcs"
    assert response.result["status"] == "success"
    assert response.result["correlation_id"] == request.correlation_id
    assert response.result["data"]["resources"][0]["VpcId"] == "vpc-0123456789abcdef0"
