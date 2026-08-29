# ADR 011 — MCP Tool Architecture

## Status
Accepted

## Decision
Use strict, local-testable MCP contracts, consistent result/error envelopes, separate
READ/WRITE domains, controlled inputs, no generic AWS execution tool, and permission-
awareness diagnostics. Package the READ contracts in one diagnostic Lambda target and
approved WRITE contracts in a separate remediation Lambda target.

## Consequences
Tool availability is not AWS authority. Gateway controls, approval context, schemas,
execution identities, and IAM remain independent layers. Shared framework-independent
tool logic and thin Lambda adapters keep local and deployed behavior aligned; ADR 020
defines the testing path.
