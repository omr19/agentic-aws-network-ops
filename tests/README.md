# Tests

Unit and contract tests run without live AWS credentials or calls. Saved event fixtures
support repeatable adapter tests. Integration tests may contact deployed services only
during an explicitly authorized phase and controlled test session.

Phase 5 contract tests cover strict inputs, outputs, result statuses, rejected fields,
and sanitized errors. Unit tests validate all nine diagnostic tools against Botocore
Stubber and verify the thin adapter's structured log event.

Security tests parse the local Phase 5 IAM contracts and prove separation among Runtime,
Gateway, and diagnostic identities. They also verify the diagnostic identity has exactly
the required evidence actions and no IAM, STS, Lambda invocation, remediation, wildcard
action, or infrastructure-mutation permission. These are offline contract tests, not a
substitute for an explicitly authorized AWS IAM simulation before deployment.

The P5-04 local-flow tests compose Runtime, Gateway, the diagnostic Lambda adapter, and
the existing diagnostic service using injected fakes and Botocore Stubber responses. They
prove correlation/session binding, rejection before target invocation, and evidence
round-tripping without model calls, credentials, sockets, or AWS resources.

## Current local test scope

Phase 10 adds focused offline coverage for selector/Gateway/diagnostic failures, repeated
Runtime → Gateway → diagnostic runs, local verification failure, and bounded no-automatic-
retry behavior. The local selector remains intentionally fixed to the Phase 5 demonstration
tool; semantic irrelevant-tool selection is therefore an unresolved capability rather than a
passing test claim. Diagnostic errors expose retryable classification, but no retry loop is
implemented; remediation writes are not automatically retried after approval consumption.

These tests use fakes, Botocore Stubber, and sanitized fixtures. They do not validate live
AWS state, deployed AgentCore observability, current billing, production readiness, or live
post-remediation behavior.
