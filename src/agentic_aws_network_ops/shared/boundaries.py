"""Typed local boundaries for the Phase 5 READ request path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol, TypeGuard

JsonObject = dict[str, Any]
ToolName = Literal[
    "describe_vpcs",
    "describe_subnets",
    "describe_route_tables",
    "describe_security_groups",
    "describe_network_acls",
    "describe_vpc_endpoints",
    "analyze_reachability",
    "query_flow_logs",
    "get_cloudwatch_metrics",
]

READ_TOOL_NAMES: tuple[ToolName, ...] = (
    "describe_vpcs",
    "describe_subnets",
    "describe_route_tables",
    "describe_security_groups",
    "describe_network_acls",
    "describe_vpc_endpoints",
    "analyze_reachability",
    "query_flow_logs",
    "get_cloudwatch_metrics",
)


class BoundaryError(ValueError):
    """Raised when a local boundary message is not a valid READ message."""


def is_read_tool(value: object) -> TypeGuard[ToolName]:
    """Return whether a value is one of the nine approved diagnostic tools."""
    return isinstance(value, str) and value in READ_TOOL_NAMES


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise BoundaryError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class RuntimeRequest:
    """Natural-language request accepted by the local Runtime boundary."""

    prompt: str
    correlation_id: str
    session_id: str
    region: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RuntimeRequest:
        expected = {"prompt", "correlation_id", "session_id", "region"}
        if set(value) != expected:
            raise BoundaryError("Runtime request fields are not exact")
        return cls(
            prompt=_text(value["prompt"], "prompt"),
            correlation_id=_text(value["correlation_id"], "correlation_id"),
            session_id=_text(value["session_id"], "session_id"),
            region=_text(value["region"], "region"),
        )


@dataclass(frozen=True)
class GatewayReadRequest:
    """Typed request from Runtime to the managed or local Gateway boundary."""

    tool: ToolName
    arguments: JsonObject
    correlation_id: str
    session_id: str
    region: str

    def __post_init__(self) -> None:
        if not is_read_tool(self.tool):
            raise BoundaryError("tool is not in the approved diagnostic boundary")
        if self.arguments.get("correlation_id") != self.correlation_id:
            raise BoundaryError("arguments correlation_id must match the Gateway request")
        if self.arguments.get("region") != self.region:
            raise BoundaryError("arguments region must match the Gateway request")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> GatewayReadRequest:
        expected = {"tool", "arguments", "correlation_id", "session_id", "region"}
        if set(value) != expected:
            raise BoundaryError("Gateway request fields are not exact")
        tool = value["tool"]
        arguments = value["arguments"]
        if not is_read_tool(tool):
            raise BoundaryError("tool is not in the approved diagnostic boundary")
        if not isinstance(arguments, dict):
            raise BoundaryError("arguments must be an object")
        correlation_id = _text(value["correlation_id"], "correlation_id")
        session_id = _text(value["session_id"], "session_id")
        region = _text(value["region"], "region")
        if arguments.get("correlation_id") != correlation_id:
            raise BoundaryError("arguments correlation_id must match the Gateway request")
        if arguments.get("region") != region:
            raise BoundaryError("arguments region must match the Gateway request")
        return cls(tool, dict(arguments), correlation_id, session_id, region)

    def to_diagnostic_event(self) -> JsonObject:
        """Convert the outer Gateway message to the existing Lambda event shape."""
        return {"tool": self.tool, "arguments": dict(self.arguments)}


@dataclass(frozen=True)
class GatewayReadResponse:
    """Typed response returned by the Gateway READ boundary."""

    accepted: bool
    tool: str
    correlation_id: str
    session_id: str
    result: JsonObject | None = None
    error: JsonObject | None = None

    @classmethod
    def accepted_result(
        cls, request: GatewayReadRequest, result: JsonObject
    ) -> GatewayReadResponse:
        return cls(True, request.tool, request.correlation_id, request.session_id, result=result)

    @classmethod
    def rejected(
        cls,
        *,
        tool: object,
        correlation_id: object,
        session_id: object,
        code: str,
        message: str,
    ) -> GatewayReadResponse:
        return cls(
            False,
            str(tool),
            str(correlation_id),
            str(session_id),
            error={"code": code, "message": message},
        )

    def to_mapping(self) -> JsonObject:
        output: JsonObject = {
            "accepted": self.accepted,
            "tool": self.tool,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
        }
        if self.accepted and self.result is not None:
            output["result"] = self.result
        if not self.accepted and self.error is not None:
            output["error"] = self.error
        return output


@dataclass(frozen=True)
class RuntimeResponse:
    """Typed response returned from Runtime to the native client."""

    accepted: bool
    tool: str
    correlation_id: str
    session_id: str
    result: JsonObject | None = None
    error: JsonObject | None = None

    @classmethod
    def from_gateway(cls, response: GatewayReadResponse) -> RuntimeResponse:
        return cls(
            response.accepted,
            response.tool,
            response.correlation_id,
            response.session_id,
            response.result,
            response.error,
        )

    @classmethod
    def rejected(cls, request: RuntimeRequest, code: str, message: str) -> RuntimeResponse:
        return cls(
            False,
            "",
            request.correlation_id,
            request.session_id,
            error={"code": code, "message": message},
        )

    def to_mapping(self) -> JsonObject:
        output: JsonObject = {
            "accepted": self.accepted,
            "tool": self.tool,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
        }
        if self.accepted and self.result is not None:
            output["result"] = self.result
        if not self.accepted and self.error is not None:
            output["error"] = self.error
        return output


class GatewayReadInvoker(Protocol):
    """Protocol implemented by managed or local Gateway transports."""

    def invoke(self, request: GatewayReadRequest) -> GatewayReadResponse:
        """Invoke only a typed READ request."""


class SigV4Transport(Protocol):
    """Injected transport seam for a future IAM/SigV4 Gateway client."""

    def send(self, config: SigV4Config, request: RuntimeRequest) -> RuntimeResponse:
        """Send a request using an implementation-provided signer/transport."""


@dataclass(frozen=True)
class SigV4Config:
    """Non-secret IAM/SigV4 metadata; credentials are deliberately not stored here."""

    service: str
    region: str
    endpoint_url: str
    path: str = "/"

    @classmethod
    def placeholder(cls, region: str) -> SigV4Config:
        """Create deployment-agnostic metadata without resolving credentials or network."""
        return cls(
            service="bedrock-agentcore",
            region=region,
            endpoint_url="${agentcore_gateway_endpoint}",
            path="${agentcore_gateway_path}",
        )
