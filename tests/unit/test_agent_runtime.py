"""Offline tests for the typed Runtime and native-client boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_aws_network_ops.agent.client import NativeAgentClient
from agentic_aws_network_ops.agent.runtime import FixedToolSelector, Runtime
from agentic_aws_network_ops.shared.boundaries import (
    BoundaryError,
    GatewayReadRequest,
    GatewayReadResponse,
    RuntimeRequest,
    RuntimeResponse,
    SigV4Config,
)

FIXTURES = Path(__file__).parents[1] / "fixtures/events"


class FakeGateway:
    def __init__(self, response: GatewayReadResponse) -> None:
        self.response = response
        self.requests: list[GatewayReadRequest] = []

    def invoke(self, request: GatewayReadRequest) -> GatewayReadResponse:
        self.requests.append(request)
        return self.response


class FakeTransport:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.configs: list[SigV4Config] = []

    def send(self, config: SigV4Config, request: RuntimeRequest) -> RuntimeResponse:
        self.configs.append(config)
        return self.runtime.handle(request)


def load(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def test_runtime_selects_read_tool_and_preserves_correlation_and_session() -> None:
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))
    result = load("diagnostic-result-describe-vpcs.json")
    gateway = FakeGateway(
        GatewayReadResponse.accepted_result(
            GatewayReadRequest(
                "describe_vpcs",
                {
                    "schema_version": "1.0.0",
                    "correlation_id": request.correlation_id,
                    "region": request.region,
                    "project_tag": "agentic-aws-network-ops",
                },
                request.correlation_id,
                request.session_id,
                request.region,
            ),
            result,
        )
    )
    runtime = Runtime(
        FixedToolSelector(
            "describe_vpcs", {"schema_version": "1.0.0", "project_tag": "agentic-aws-network-ops"}
        ),
        gateway,
    )

    response = runtime.handle(request)

    assert response.accepted is True
    assert response.result == result
    assert response.correlation_id == request.correlation_id
    assert response.session_id == request.session_id
    assert gateway.requests[0].tool == "describe_vpcs"
    assert "approval" not in response.to_mapping()


def test_native_client_uses_injected_sigv4_metadata_and_transport() -> None:
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))
    gateway = FakeGateway(
        GatewayReadResponse.rejected(
            tool="describe_vpcs",
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            code="TEST_ONLY",
            message="injected response",
        )
    )
    runtime = Runtime(
        FixedToolSelector("describe_vpcs", {"schema_version": "1.0.0"}),
        gateway,
    )
    config = SigV4Config.placeholder(request.region)
    transport = FakeTransport(runtime)

    response = NativeAgentClient(config, transport).submit(request)

    assert response.accepted is False
    assert transport.configs == [config]
    assert config.endpoint_url == "${agentcore_gateway_endpoint}"


def test_runtime_surfaces_selector_failure_without_gateway_call() -> None:
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))

    class FailingSelector:
        def select(self, value: RuntimeRequest) -> GatewayReadRequest:
            del value
            raise RuntimeError("injected selector failure")

    gateway = FakeGateway(
        GatewayReadResponse.rejected(
            tool="describe_vpcs",
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            code="NOT_REACHED",
            message="not reached",
        )
    )

    with pytest.raises(RuntimeError, match="injected selector failure"):
        Runtime(FailingSelector(), gateway).handle(request)
    assert gateway.requests == []


def test_runtime_surfaces_gateway_failure_after_one_call() -> None:
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))

    class FailingGateway:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, value: GatewayReadRequest) -> GatewayReadResponse:
            del value
            self.calls += 1
            raise TimeoutError("injected Gateway timeout")

    gateway = FailingGateway()
    runtime = Runtime(
        FixedToolSelector("describe_vpcs", {"schema_version": "1.0.0"}),
        gateway,
    )

    with pytest.raises(TimeoutError, match="injected Gateway timeout"):
        runtime.handle(request)
    assert gateway.calls == 1


def test_runtime_rejects_selector_binding_mismatch_without_gateway_call() -> None:
    request = RuntimeRequest.from_mapping(load("runtime-describe-vpcs.json"))
    gateway = FakeGateway(
        GatewayReadResponse.rejected(
            tool="describe_vpcs",
            correlation_id="other-correlation",
            session_id=request.session_id,
            code="TEST_ONLY",
            message="not reached",
        )
    )

    class MismatchedSelector:
        def select(self, value: RuntimeRequest) -> GatewayReadRequest:
            return GatewayReadRequest(
                "describe_vpcs",
                {
                    "schema_version": "1.0.0",
                    "correlation_id": "other-correlation",
                    "region": value.region,
                    "project_tag": "agentic-aws-network-ops",
                },
                "other-correlation",
                value.session_id,
                value.region,
            )

    response = Runtime(MismatchedSelector(), gateway).handle(request)

    assert response.accepted is False
    assert response.error == {
        "code": "INVALID_REQUEST",
        "message": "Gateway request correlation_id does not match Runtime request",
    }
    assert gateway.requests == []


def test_boundary_rejects_unknown_runtime_fields() -> None:
    payload = load("runtime-describe-vpcs.json")
    payload["credentials"] = "must-not-cross-boundary"
    with pytest.raises(BoundaryError):
        RuntimeRequest.from_mapping(payload)
