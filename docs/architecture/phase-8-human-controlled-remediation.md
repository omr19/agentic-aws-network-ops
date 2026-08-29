# Phase 8 Human-Controlled Remediation Foundation

Phase 8 begins with a local-only contract and state-machine foundation. It does not call AWS, Terraform, IAM, AgentCore, or deployment tooling, and it does not mark the phase complete.

## Separation of responsibilities

- Diagnostic READ contracts remain under `schemas/diagnostic/` and the diagnostic service allowlist is unchanged.
- Remediation WRITE contracts are separate under `schemas/remediation/`.
- A proposal describes one allowlisted corrective action and its deterministic evidence; proposal creation never executes a write.
- A human records an explicit `APPROVED` or `DENIED` decision bound to the approval ID, correlation ID, policy session ID, request hash, resource, and operation.
- Execution requires a matching, unexpired, unconsumed approval and uses an injected adapter only in this local foundation.
- Verification is a separate READ adapter/result and cannot be represented as execution evidence.

## Supported corrective actions

The local scenario contract covers the approved Phase 6 corrections: `security_group_rule`, `route_table_entry`, `nacl_rule`, and `peering_routes_dns`. They map only to the three ADR-approved narrow tools: `restore_security_group_ingress`, `restore_vpc_peering_route`, and `restore_network_acl_entry`. No generic AWS command, arbitrary resource selection, delete operation, or diagnostic READ tool can enter this workflow.

The future manifest must resolve exact Terraform-managed resources and fixed parameters before a human approves the complete proposal. Runtime IAM, Approval Lambda, DynamoDB, AgentCore Policy, Gateway interceptors, and AWS execution adapters are intentionally outside this local task.

## Approval and result lifecycle

```text
normalized READ facts
        -> proposal (no write)
        -> explicit human APPROVED / DENIED decision
        -> validate binding + consume once
        -> injected execution result
        -> separate READ verification result
        -> Terraform drift / source reconciliation warning
```

Denial, absent approval, expiration, changed hash, wrong correlation/session, and replay all stop before the execution adapter. A successful local execution result explicitly reports Terraform drift and required source reconciliation because a future runtime correction would change Terraform-managed state.

## Contracts and evidence

- `schemas/remediation/request.schema.json` — model-controlled request with no AWS parameters.
- `schemas/remediation/proposal.schema.json` — complete human-reviewable change proposal.
- `schemas/remediation/approval.schema.json` — explicit decision and binding fields.
- `schemas/remediation/execution-result.schema.json` — write result and drift boundary.
- `schemas/remediation/verification-result.schema.json` — separate deterministic READ verification.
- `docs/evidence/phase-8/remediation-validation-template.json` — sanitized evidence structure for future local validation.
- `tests/unit/test_phase8_remediation_workflow.py`, `tests/contract/test_phase8_remediation_schemas.py`, and `tests/security/test_phase8_remediation_security.py` — offline enforcement tests.

This foundation is not a production persistence or AWS authorization implementation. Any future deployment requires separate architecture, IAM, resource, and approval gates.
