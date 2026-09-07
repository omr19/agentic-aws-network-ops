# ADR 012 — Identity and IAM Architecture

## Status
Accepted

## Decision
Use separate least-privilege identities for Agent Runtime, diagnostic READ execution,
and remediation WRITE execution. Do not grant broad administrator or `ec2:*` access.

## Consequences
Approval never changes IAM authority. Authorization failures identify the relevant
identity/action where evidence permits and feed security observability.
