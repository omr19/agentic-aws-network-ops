"""Single-agent local orchestration for the fixed diagnostic READ boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agentic_aws_network_ops.shared.boundaries import (
    BoundaryError,
    GatewayReadInvoker,
    GatewayReadRequest,
    JsonObject,
    RuntimeRequest,
    RuntimeResponse,
    ToolName,
)


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
        try:
            selected = self._selector.select(request)
            self._validate_binding(request, selected)
            return RuntimeResponse.from_gateway(self._gateway.invoke(selected))
        except BoundaryError as error:
            return RuntimeResponse.rejected(request, "INVALID_REQUEST", str(error))

    @staticmethod
    def _validate_binding(request: RuntimeRequest, selected: GatewayReadRequest) -> None:
        if selected.correlation_id != request.correlation_id:
            raise BoundaryError("Gateway request correlation_id does not match Runtime request")
        if selected.session_id != request.session_id:
            raise BoundaryError("Gateway request session_id does not match Runtime request")
        if selected.region != request.region:
            raise BoundaryError("Gateway request region does not match Runtime request")
