"""Thin AWS Lambda adapter for the diagnostic service."""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

import boto3  # type: ignore[import-untyped]

from agentic_aws_network_ops.diagnostics.service import DiagnosticClients, DiagnosticService
from agentic_aws_network_ops.shared.observability import emit_event, emit_exception

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


class DiagnosticExecutor(Protocol):
    """Minimal injected service interface used by local and deployed adapters."""

    def execute(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute one approved diagnostic tool."""


def build_service(region: str) -> DiagnosticService:
    """Construct the service at the deployment boundary."""
    session = boto3.session.Session(region_name=region)
    return DiagnosticService(
        DiagnosticClients(
            ec2=session.client("ec2"),
            logs=session.client("logs"),
            cloudwatch=session.client("cloudwatch"),
        )
    )


def dispatch(event: dict[str, Any], service: DiagnosticExecutor) -> dict[str, Any]:
    """Dispatch a Lambda-shaped event through an injected diagnostic service."""
    tool = str(event.get("tool", ""))
    arguments = event.get("arguments")
    payload = (
        arguments
        if isinstance(arguments, dict)
        else {key: value for key, value in event.items() if key != "tool"}
    )
    return service.execute(tool, payload)


def _context_tool_name(context: Any) -> str:
    """Read and normalize the tool name supplied by an AgentCore Lambda target."""
    client_context = getattr(context, "client_context", None)
    custom = getattr(client_context, "custom", None)
    if not isinstance(custom, dict):
        return ""
    qualified_name = custom.get("bedrockAgentCoreToolName", "")
    if not isinstance(qualified_name, str):
        return ""
    return qualified_name.partition("___")[2] or qualified_name


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Adapt a strict tool event to the framework-independent service."""
    started = time.perf_counter()
    arguments = event.get("arguments")
    payload = arguments if isinstance(arguments, dict) else {}
    region = str(payload.get("region", "eu-west-1"))
    correlation_id = payload.get("correlation_id")
    event_with_tool = dict(event)
    tool_name = _context_tool_name(context) or str(event.get("tool", ""))
    event_with_tool["tool"] = tool_name
    request_id = getattr(context, "aws_request_id", None)
    try:
        result = dispatch(event_with_tool, build_service(region))
    except Exception as error:
        emit_exception(
            LOGGER,
            "diagnostic_tool_call",
            error,
            status="failure",
            correlation_id=correlation_id if isinstance(correlation_id, str) else None,
            request_id=request_id if isinstance(request_id, str) else None,
            duration_ms=(time.perf_counter() - started) * 1000,
            region=region,
            tool_name=tool_name,
        )
        raise
    emit_event(
        LOGGER,
        "diagnostic_tool_call",
        status=str(result["status"]),
        correlation_id=result.get("correlation_id"),
        request_id=request_id if isinstance(request_id, str) else None,
        duration_ms=(time.perf_counter() - started) * 1000,
        region=region,
        tool_name=str(result.get("tool", tool_name)),
        evidence_completeness=result.get("evidence_completeness"),
    )
    return result
