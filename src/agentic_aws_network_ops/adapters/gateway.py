"""Local emulation of the Gateway READ target boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from agentic_aws_network_ops.adapters import diagnostic_lambda
from agentic_aws_network_ops.shared.boundaries import (
    BoundaryError,
    GatewayReadRequest,
    GatewayReadResponse,
    JsonObject,
)


class DiagnosticTarget(Protocol):
    """Injected diagnostic Lambda target; no AWS client construction is allowed here."""

    def invoke(self, event: JsonObject) -> JsonObject:
        """Invoke the diagnostic READ adapter with a Lambda-shaped event."""


class LocalDiagnosticLambdaTarget:
    """Adapt the existing framework-independent service to the Lambda target seam."""

    def __init__(self, service: diagnostic_lambda.DiagnosticExecutor) -> None:
        self._service = service

    def invoke(self, event: JsonObject) -> JsonObject:
        return diagnostic_lambda.dispatch(event, self._service)


class LocalGatewayAdapter:
    """Validate Gateway messages and forward only approved READ requests."""

    def __init__(self, diagnostic_target: DiagnosticTarget) -> None:
        self._diagnostic_target = diagnostic_target

    def invoke(self, request: GatewayReadRequest) -> GatewayReadResponse:
        result = self._diagnostic_target.invoke(request.to_diagnostic_event())
        return GatewayReadResponse.accepted_result(request, result)

    def handle_event(self, event: Mapping[str, Any]) -> GatewayReadResponse:
        try:
            request = GatewayReadRequest.from_mapping(event)
        except BoundaryError as error:
            return GatewayReadResponse.rejected(
                tool=event.get("tool", ""),
                correlation_id=event.get("correlation_id", "invalid-request"),
                session_id=event.get("session_id", "invalid-session"),
                code="INVALID_REQUEST",
                message=str(error),
            )
        return self.invoke(request)
