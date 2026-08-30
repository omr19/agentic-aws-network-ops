"""Minimal AgentCore Runtime HTTP entry point for the read-only project path."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from uuid import uuid4

import boto3  # type: ignore[import-untyped]
from botocore.auth import SigV4Auth  # type: ignore[import-untyped]
from botocore.awsrequest import AWSRequest  # type: ignore[import-untyped]

from agentic_aws_network_ops.shared.boundaries import RuntimeRequest
from agentic_aws_network_ops.shared.observability import emit_event, emit_exception

LOGGER = logging.getLogger(__name__)


class RuntimeHandler(BaseHTTPRequestHandler):
    """Implement the AgentCore /ping and /invocations HTTP contract."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/ping":
            self.send_error(404)
            return
        self._respond(200, {"status": "healthy"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invocations":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            request = RuntimeRequest.from_mapping(payload)
            self._respond(200, invoke_gateway(request))
        except (ValueError, json.JSONDecodeError, TypeError) as error:
            self._respond(400, {"error": {"code": "INVALID_REQUEST", "message": str(error)}})

    def _respond(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    """Start the local/AgentCore HTTP server."""
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), RuntimeHandler).serve_forever()  # noqa: S104


def invoke_gateway(request: RuntimeRequest) -> dict[str, Any]:
    """Invoke only the fixed read-only Gateway tool through IAM/SigV4."""
    started = time.perf_counter()
    tool_call_id = str(uuid4())
    emit_event(
        LOGGER,
        "mcp_tool_call",
        status="started",
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        tool_call_id=tool_call_id,
        region=request.region,
        tool_name="describe_vpcs",
    )
    endpoint = os.environ.get("AGENTCORE_GATEWAY_ENDPOINT", "")
    if not endpoint:
        response = {
            "accepted": False,
            "correlation_id": request.correlation_id,
            "session_id": request.session_id,
            "error": {
                "code": "GATEWAY_ENDPOINT_NOT_CONFIGURED",
                "message": "AGENTCORE_GATEWAY_ENDPOINT is required",
            },
        }
        emit_event(
            LOGGER,
            "mcp_tool_call",
            status="failure",
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            tool_call_id=tool_call_id,
            duration_ms=(time.perf_counter() - started) * 1000,
            region=request.region,
            tool_name="describe_vpcs",
        )
        return response
    args = {
        "schema_version": "1.0.0",
        "correlation_id": request.correlation_id,
        "region": request.region,
        "project_tag": "agentic-aws-network-ops",
    }
    body = {
        "jsonrpc": "2.0",
        "id": request.correlation_id,
        "method": "tools/call",
        "params": {"name": "phase5-diagnostic-lambda___describe_vpcs", "arguments": args},
    }
    data = json.dumps(body).encode()
    url = endpoint.rstrip("/") + "/mcp"
    signed = AWSRequest(
        method="POST",
        url=url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-03-26",
        },
    )
    credentials = (
        boto3.Session(region_name=request.region).get_credentials().get_frozen_credentials()
    )
    SigV4Auth(credentials, "bedrock-agentcore", request.region).add_auth(signed)
    try:
        with urllib.request.urlopen(  # noqa: S310 - endpoint is operator-configured HTTPS URL
            urllib.request.Request(url, data=data, headers=dict(signed.headers), method="POST"),  # noqa: S310
            timeout=60,
        ) as response:  # noqa: S310 - endpoint is operator-configured HTTPS Gateway URL
            result = {
                "accepted": True,
                "correlation_id": request.correlation_id,
                "session_id": request.session_id,
                "result": json.loads(response.read().decode()),
            }
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        emit_exception(
            LOGGER,
            "mcp_tool_call",
            error,
            status="failure",
            correlation_id=request.correlation_id,
            session_id=request.session_id,
            tool_call_id=tool_call_id,
            duration_ms=(time.perf_counter() - started) * 1000,
            region=request.region,
            tool_name="describe_vpcs",
        )
        return {
            "accepted": False,
            "correlation_id": request.correlation_id,
            "session_id": request.session_id,
            "error": {"code": "GATEWAY_INVOCATION_FAILED", "message": str(error)},
        }
    emit_event(
        LOGGER,
        "mcp_tool_call",
        status="success",
        correlation_id=request.correlation_id,
        session_id=request.session_id,
        tool_call_id=tool_call_id,
        duration_ms=(time.perf_counter() - started) * 1000,
        region=request.region,
        tool_name="describe_vpcs",
    )
    return result


if __name__ == "__main__":
    main()
