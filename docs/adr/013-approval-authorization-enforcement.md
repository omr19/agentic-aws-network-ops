# ADR 013 — Approval Authorization Enforcement

## Status
Accepted

## Decision
Use AgentCore Gateway with Policy in AgentCore for preferred MCP tool-level
authorization, independently backed by a dedicated remediation identity and IAM. Use
an interceptor only for required validation Policy cannot express cleanly. Use
IAM/SigV4 for inbound Gateway authorization in the native MVP path.

## Consequences
Approval must bind approver, action, resource, session, and expiration. Representation,
replay protection, and role-access mechanics are defined by ADR 021. Policy is tested
in `LOG_ONLY` before promotion to `ENFORCE`.
