# ADR 010 — Agent Invocation Path

## Status
Accepted

## Decision
Use native AgentCore invocation for the MVP. Treat API Gateway and an adapter Lambda
as an extension for external REST consumers, webhooks, authentication, validation, or
rate limiting. The native MVP client authenticates with IAM/SigV4.

## Consequences
The MVP demonstrates AgentCore directly while preserving a defensible external-API
evolution path.
