# Phase 8 deployment-readiness package

This document defines the local package boundary for a future live remediation deployment. It is not deployment evidence and does not mark Phase 8 complete.

## Packaging readiness

`scripts/package_phase8_lambdas.py` creates reproducible, ignored local artifacts for the
Approval and Remediation Lambda boundaries. It packages only the existing interfaces,
manifest/workflow modules, and remediation schemas; it does not change behavior, add AWS
clients, or broaden IAM permissions. Fixed ZIP timestamps and sorted members make repeated
builds byte-identical. Each component writes:

- `<component>.zip`
- `<component>.zip.sha256`
- `<component>.zip.manifest.txt` with per-member SHA-256 values
- `package-manifest.json` with entrypoint contract, role boundary, runtime, members, and artifact digest

`scripts/verify_phase8_lambda_packages.py` validates those files without AWS access.
Artifacts live below `.artifacts/`, which is already ignored by `.gitignore`.

The packages are not deployment authorization. Before deployment, the production wrapper
must require authenticated IAM/SigV4 invocation, preserve the closed-world schemas, emit
structured logs with correlation/request/approval/execution identifiers and no secrets or
hidden reasoning, and use only the separate Phase 8 IAM roles. Lambda logging permissions,
resource policies, and AgentCore policy/interceptor configuration remain separate approval
gates and are not included in these packages.

The Approval Lambda accepts only the closed-world `approval-lambda-event.schema.json` event and delegates to the structured `ApprovalService`. The authenticated principal must come from the production IAM/SigV4 invocation identity; conversational text is never an approval. It records the proposal/request bindings, action, exact operation/resource, principal, decision, creation/expiry timestamps, `ttl_epoch`, consumed state, execution ID/status, and execution-result audit fields.

The opt-in Terraform module creates an on-demand, server-side-encrypted DynamoDB table keyed by `approval_id` with TTL on `ttl_epoch`. A production adapter must use conditional writes/updates: reject duplicate approval IDs, atomically transition `APPROVED` to `EXECUTING`, bind the claiming execution ID, and permit same-execution idempotent replay while rejecting a different execution. The interceptor validates but does not consume because Gateway retries are possible.

## Remediation Lambda

The remediation Lambda accepts only `{action, request, execution_id}`. It resolves the action/scenario exclusively through the frozen manifest, then delegates to a thin executor that must perform preflight, approval consumption, one allowlisted EC2 write, result persistence, and independent READ verification. The exact tools are `restore_security_group_ingress`, `restore_vpc_peering_route`, and `restore_network_acl_entry`; there is no DNS, delete/revoke, generic AWS, or caller-supplied resource/parameter path.

The local interfaces contain no boto3/AWS calls. AWS adapters are a later implementation seam and are tested with mocks only in this package.

## IAM and Terraform boundary

`terraform/modules/phase8_readiness` is opt-in and reproducible. It defines the tagged approval table and separate Approval Lambda/remediation Lambda roles. The remediation policy contains only the four ADR 022 EC2 writes and DynamoDB consumption/result persistence. The module is disabled by default, supports teardown by normal Terraform destruction, and uses PAY_PER_REQUEST/TTL to avoid persistent baseline cost.

Lambda packaging, CloudWatch logging permissions, resource-based invocation policies, AgentCore policy/interceptor resources, and live manifest injection are intentionally not invented in Terraform. The current AWS provider/resource graph does not establish those AgentCore deployment contracts; their exact later boundary is: approved Lambda artifact/package and role wiring, direct IAM/SigV4 Approval Lambda invocation, Gateway interceptor/policy configuration through the supported AgentCore control-plane/API path, then policy LOG_ONLY validation before ENFORCE.

## Later AWS approval gates

1. Approve enabling the opt-in module and its cost/retention plan.
2. Approve account/resource placeholder substitution from trusted Terraform outputs.
3. Review IAM action/resource/condition-key support and attach separate roles; never reuse diagnostic/Runtime roles.
4. Approve Lambda packaging, logging, invocation authentication, and deployment.
5. Approve AgentCore policy/interceptor configuration and LOG_ONLY test matrix before ENFORCE.
6. Approve controlled failure injection, one remediation execution per scenario, Reachability Analyzer verification, Terraform drift/source reconciliation, and cleanup.
