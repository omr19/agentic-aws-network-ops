"""Deployment-agnostic native-client seam for future IAM/SigV4 transport."""

from __future__ import annotations

from agentic_aws_network_ops.shared.boundaries import (
    BoundaryError,
    RuntimeRequest,
    RuntimeResponse,
    SigV4Config,
    SigV4Transport,
)


class NativeAgentClient:
    """Submit Runtime requests through an injected, future SigV4 transport."""

    def __init__(self, config: SigV4Config, transport: SigV4Transport) -> None:
        self._config = config
        self._transport = transport

    def submit(self, request: RuntimeRequest) -> RuntimeResponse:
        if request.region != self._config.region:
            raise BoundaryError("Runtime request region does not match SigV4 configuration")
        return self._transport.send(self._config, request)
