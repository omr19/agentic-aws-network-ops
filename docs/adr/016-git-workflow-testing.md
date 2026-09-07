# ADR 016 — Git Workflow and Testing

## Status
Accepted; quality tool selection locked by ADR 023

## Decision
Use `develop` for integration and `main` for stable state, with optional feature
branches for substantial/risky work. Test static validity, unit contracts, AWS
integration, scenarios, authorization failures, AI failures, and end-to-end behavior.

## Consequences
CI may run non-destructive checks but gets no broad AWS credentials. The exact Python
quality toolchain remains open.
