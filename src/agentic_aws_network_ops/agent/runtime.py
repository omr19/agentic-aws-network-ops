"""Single-agent local orchestration for the fixed diagnostic READ boundary."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from agentic_aws_network_ops.shared.boundaries import (
    BoundaryError,
    GatewayReadInvoker,
    GatewayReadRequest,
    JsonObject,
    RuntimeRequest,
    RuntimeResponse,
    ToolName,
)
from agentic_aws_network_ops.shared.observability import emit_event, emit_exception

LOGGER = logging.getLogger(__name__)


class ToolSelector(Protocol):
    """Injected selector; production model/tool selection is outside this foundation."""

    def select(self, request: RuntimeRequest) -> GatewayReadRequest:
        """Select one approved diagnostic READ request."""


@dataclass(frozen=True)
class FixedToolSelector:
    """Deterministic local selector used by tests and local development."""

    tool: ToolName
    arguments: JsonObject

    def select(self, request: RuntimeRequest) -> GatewayReadRequest:
        arguments = dict(self.arguments)
        arguments["correlation_id"] = request.correlation_id
        arguments["region"] = request.region
        return GatewayReadRequest(
            tool=self.tool,
            arguments=arguments,
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            region=request.region,
        )


class Runtime:
    """Correlate a request, invoke only the Gateway READ boundary, and carry evidence back."""

    def __init__(self, selector: ToolSelector, gateway: GatewayReadInvoker) -> None:
        self._selector = selector
        self._gateway = gateway

    def handle(self, request: RuntimeRequest) -> RuntimeResponse:
        started = time.perf_counter()
        tool_call_id = str(uuid4())
        emit_event(
            LOGGER,
            "runtime_request",
            status="started",
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            region=request.region,
        )
        try:
            selected = self._selector.select(request)
            self._validate_binding(request, selected)
            emit_event(
                LOGGER,
                "mcp_tool_call",
                status="selected",
                correlation_id=request.correlation_id,
                session_id=request.session_id,
                tool_call_id=tool_call_id,
                region=request.region,
                tool_name=selected.tool,
            )
            gateway_response = self._gateway.invoke(selected)
            emit_event(
                LOGGER,
                "mcp_tool_call",
                status="success" if gateway_response.accepted else "failure",
                correlation_id=request.correlation_id,
                session_id=request.session_id,
                tool_call_id=tool_call_id,
                duration_ms=(time.perf_counter() - started) * 1000,
                region=request.region,
                tool_name=selected.tool,
            )
            response = RuntimeResponse.from_gateway(gateway_response)
            emit_event(
                LOGGER,
                "runtime_request",
                status="success" if response.accepted else "failure",
                correlation_id=request.correlation_id,
                session_id=request.session_id,
                tool_call_id=tool_call_id,
                duration_ms=(time.perf_counter() - started) * 1000,
                region=request.region,
            )
            return response
        except BoundaryError as error:
            emit_exception(
                LOGGER,
                "runtime_request",
                error,
                status="rejected",
                correlation_id=request.correlation_id,
                session_id=request.session_id,
                tool_call_id=tool_call_id,
                duration_ms=(time.perf_counter() - started) * 1000,
                region=request.region,
            )
            return RuntimeResponse.rejected(request, "INVALID_REQUEST", str(error))

    @staticmethod
    def _validate_binding(request: RuntimeRequest, selected: GatewayReadRequest) -> None:
        if selected.correlation_id != request.correlation_id:
            raise BoundaryError("Gateway request correlation_id does not match Runtime request")
        if selected.session_id != request.session_id:
            raise BoundaryError("Gateway request session_id does not match Runtime request")
        if selected.region != request.region:
            raise BoundaryError("Gateway request region does not match Runtime request")
