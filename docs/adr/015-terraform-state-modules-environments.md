# ADR 015 — Terraform State, Modules, and Environments

## Status
Accepted

## Decision
Use local state for the single-engineer MVP, one `lab` environment, safe example
variables, consistent tags, and responsibility-based modules. Keep state and real
configuration out of Git. Document remote state as a team evolution.

## Consequences
Later apply requires format, validation, plan, explicit plan review, and authorization.
Exact module files are finalized in Phase 3 without artificial boundaries.
