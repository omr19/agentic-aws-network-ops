"""Deployment-facing Approval Lambda contract without an AWS runtime dependency."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol

from .service import ApprovalService


class ApprovalLambdaError(ValueError):
    """Raised when an Approval Lambda event is outside the closed contract."""


class ApprovalClock(Protocol):
    def now(self) -> datetime: ...


def handle_approval_event(
    event: Mapping[str, Any],
    *,
    service: ApprovalService,
    now: datetime,
) -> dict[str, Any]:
    """Persist one explicit decision; this boundary never executes remediation.

    The production adapter should obtain the authenticated principal from the
    Lambda authorizer/SigV4 identity and construct ``approver_principal`` before
    calling this function. The local contract remains closed-world and AWS-free.
    """

    if not isinstance(event, Mapping):
        raise ApprovalLambdaError("event must be a structured mapping")
    try:
        return service.submit(event, now=now)
    except ValueError as error:
        raise ApprovalLambdaError(str(error)) from error
