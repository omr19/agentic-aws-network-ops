"""Offline tests for the local Gateway-to-diagnostic target adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_aws_network_ops.adapters.gateway import (
    LocalDiagnosticLambdaTarget,
    LocalGatewayAdapter,
)

FIXTURES = Path(__file__).parents[1] / "fixtures/events"


class FakeDiagnosticService:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.events: list[dict[str, Any]] = []

    def execute(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.events.append({"tool": tool, "payload": payload})
        return self.result


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def test_gateway_forwards_valid_request_to_diagnostic_lambda_shape() -> None:
    result = load("diagnostic-result-describe-vpcs.json")
    service = FakeDiagnosticService(result)
    adapter = LocalGatewayAdapter(LocalDiagnosticLambdaTarget(service))

    response = adapter.handle_event(load("gateway-forward-describe-vpcs.json"))

    assert response.accepted is True
    assert response.result == result
    assert service.events == [
        {
            "tool": "describe_vpcs",
            "payload": {
                "schema_version": "1.0.0",
                "correlation_id": "corr-p5-04-0001",
                "region": "eu-west-1",
                "project_tag": "agentic-aws-network-ops",
            },
        }
    ]


def test_gateway_surfaces_diagnostic_target_failure_without_retry() -> None:
    class FailingTarget:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, event: dict[str, Any]) -> dict[str, Any]:
            del event
            self.calls += 1
            raise TimeoutError("injected diagnostic timeout")

    target = FailingTarget()
    adapter = LocalGatewayAdapter(target)

    with pytest.raises(TimeoutError, match="injected diagnostic timeout"):
        adapter.handle_event(load("gateway-forward-describe-vpcs.json"))
    assert target.calls == 1


def test_gateway_rejects_invalid_generic_execution_request_without_target_call() -> None:
    service = FakeDiagnosticService(load("diagnostic-result-describe-vpcs.json"))
    adapter = LocalGatewayAdapter(LocalDiagnosticLambdaTarget(service))

    response = adapter.handle_event(load("gateway-reject-invalid.json"))

    assert response.accepted is False
    assert response.error == {
        "code": "INVALID_REQUEST",
        "message": "tool is not in the approved diagnostic boundary",
    }
    assert service.events == []
