# ADR 023 — Kiro Spec and Quality Toolchain

## Status
Accepted

## Kiro Spec structure
Create one Phase 3 spec under `.kiro/specs/agentic-aws-network-ops/`:

- `requirements.md` — traceable functional, security, cost, observability, and teardown requirements derived from approved repository documents
- `design.md` — component responsibilities, interfaces, schemas, IAM boundaries, data/control flows, failure handling, and ADR references
- `tasks.md` — ordered, independently verifiable tasks mapped to project phases and requirement IDs

The Spec derives from `docs/requirements.md`, `docs/architecture/phase-2-design.md`,
ADRs, and the authoritative checklist. It cannot change phase order, silently redesign
accepted architecture, authorize AWS changes, or mark work complete without validation.

Use stable requirement IDs and maintain requirements → design → task → test
traceability. Separate implementation tasks from AWS apply/deployment authorization.

## Python and contract tooling

- Supported Lambda-compatible Python version selected during Phase 3 after checking
  current AgentCore/Lambda compatibility; pin it consistently in project configuration
- `uv` for local environment and dependency locking
- Ruff for formatting and linting
- mypy for static typing
- pytest and pytest-cov for tests and coverage
- Botocore `Stubber` for AWS API unit tests
- JSON Schema validation for MCP contracts and fixtures
- Bandit for Python security linting
- pip-audit for dependency vulnerability review

## Terraform and repository validation

- `terraform fmt -check`, `terraform validate`, and reviewed `terraform plan`
- TFLint for Terraform linting
- Checkov for IaC security/misconfiguration scanning
- pre-commit for fast local formatting, linting, schema, and secret checks
- GitHub Actions for non-destructive checks only; no broad AWS deployment credentials

Pin tool versions or lock dependencies in Phase 3. Prefer one tool per responsibility
and avoid duplicate scanners unless an independent review identifies a material gap.
Warnings are not silently ignored; suppressions require narrow scope and rationale.

## Quality gates

1. Fast local format/lint/schema/unit checks
2. Full local type, coverage, security, and IaC checks
3. Kiro independent review at material schema/IAM/coverage/final-diff gates
4. Terraform plan review and explicit authorization before any later apply
5. Controlled AWS integration and end-to-end tests only in their approved phases

Coverage percentage is evidence, not the goal: security boundaries, denial paths,
idempotency, partial evidence, and remediation verification require explicit tests.
