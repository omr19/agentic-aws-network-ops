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

## Local approval-service foundation

The separate `src/agentic_aws_network_ops/approval/` package now provides a local-only `ApprovalService` and `ApprovalRepository` protocol. The service accepts only closed-world structured `approve` or `deny` operations, validates all ADR 021 binding fields and an authorized approver principal, records five-minute expiry and execution fields, and never invokes remediation execution. `InMemoryApprovalRepository` is a thread-safe test fake that models atomic `APPROVED` consumption, same-execution idempotent replay, different-execution rejection, and execution-result persistence. A future DynamoDB adapter must preserve these repository semantics; no AWS persistence or Approval Lambda exists in this foundation.

Focused tests are in `tests/unit/test_phase8_approval_service.py` and `tests/security/test_phase8_approval_security.py`. They reject natural-language input, unauthorized identities, changed bindings, expiry, duplicate approvals, and replay while verifying explicit approval/denial persistence and atomic consumption.

## Immutable remediation manifest

`src/agentic_aws_network_ops/remediation/manifest.py` is the local typed manifest boundary. Frozen dataclasses and immutable tuples/maps define the three supported action/scenario pairs, `eu-west-1`, required ownership tags, fixed TCP/443 values, approved CIDRs, verified route-table/peering/NACL identifiers, deployment placeholders for sanitized identifiers, and expected post-remediation states. `create_proposal()` accepts only the scenario/action plus approval-bound request identifiers and evidence; it resolves resource, operation, parameters, tags, and expected state from the manifest. Caller-supplied resource IDs, AWS operations, parameters, foreign manifests, peering DNS changes, and delete/revoke operations are rejected.

The concrete identifiers are sourced only from sanitized Phase 6 evidence; account, VPC, and parent security-group identifiers remain immutable deployment placeholders where the evidence redacts them. The manifest is local-only and does not load Terraform state or call AWS. Future deployment must inject an equivalent trusted immutable manifest rather than accepting model-controlled resource facts.
