"""Local contract for handing a verified IAM principal to Phase 8 wrappers.

A real IAM/SigV4 ingress adapter must authenticate the caller before calling
``handoff_verified_iam_principal``. The approval event is never an identity
source, and ordinary Lambda context or ClientContext values are not trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

IAM_PRINCIPAL_PATTERN: Final = re.compile(
    r"arn:aws:iam::[0-9]{12}:(?:user|role)/[A-Za-z0-9+=,.@_/-]+"
)
AUTHENTICATION_SOURCE: Final = "aws-iam-sigv4"


class TrustedIdentityError(ValueError):
    """Raised when a verified-principal handoff is malformed."""


@dataclass(frozen=True)
class TrustedApprovalInvocationContext:
    """Typed context produced after an IAM/SigV4 ingress adapter authenticates."""

    aws_request_id: str
    principal: str
    authentication_source: str = AUTHENTICATION_SOURCE

    def __post_init__(self) -> None:
        if not isinstance(self.aws_request_id, str) or not self.aws_request_id.strip():
            raise TrustedIdentityError("aws_request_id is required")
        if self.authentication_source != AUTHENTICATION_SOURCE:
            raise TrustedIdentityError("unsupported authentication source")
        if IAM_PRINCIPAL_PATTERN.fullmatch(self.principal) is None:
            raise TrustedIdentityError("principal must be an IAM user or role ARN")


def handoff_verified_iam_principal(
    *, aws_request_id: str, principal: str
) -> TrustedApprovalInvocationContext:
    """Create trusted wrapper context from an already verified IAM/SigV4 caller.

    This function performs shape validation only. The caller is responsible for
    authenticating the IAM/SigV4 request; event fields and ClientContext values
    must never be passed here as a substitute for that authentication.
    """

    return TrustedApprovalInvocationContext(
        aws_request_id=aws_request_id,
        principal=principal,
    )
