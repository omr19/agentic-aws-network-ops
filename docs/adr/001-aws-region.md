# ADR 001 — AWS Region

## Status
Accepted

## Decision
Use `eu-west-1` (Europe/Ireland). AgentCore Runtime, Gateway, Identity, and
Observability were confirmed available through AWS documentation review during Phase 2
on 2026-08-28. Existing default resources remain untouched.

## Rationale and consequences
The region supports the managed AgentCore direction and appeared relatively clean in
limited read-only reconnaissance. RDS and CloudFormation inventory gaps do not block
the choice because neither service is required by the approved design.
