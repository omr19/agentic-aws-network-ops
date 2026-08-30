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

## Local production wrapper layer

`agentic_aws_network_ops.adapters.approval_lambda:handler` and
`agentic_aws_network_ops.adapters.remediation_lambda:handler` are the standard local
`handler(event, context)` entrypoints. They are deployment-boundary wrappers only: they
perform no AWS calls and their default `build_service`/`build_executor` factories raise a
configuration error until an approved AWS adapter is injected.

Both wrappers validate the existing closed-world event contracts before constructing an
adapter. They require a Lambda request ID and exactly one authenticated principal supplied
by a trusted invocation-context adapter. They never infer identity from an event field. The
Approval wrapper requires the event approver principal to equal that context identity before
calling the injected service. The Remediation wrapper validates the request hash, UUIDs,
closed fields, and immutable manifest-compatible action boundary before calling the injected
executor. Its executor contract must perform the fail-closed approval lookup, binding checks,
atomic approval consumption, preflight, one allowlisted write, result persistence, and
independent READ verification; an absent or mismatched approval must never reach an AWS
write.

Direct Lambda Invoke does not expose the SigV4 caller ARN in the standard Lambda context.
The approved deployment adapter must therefore authenticate the caller and populate the
wrapper context's `authenticated_principal` (or the explicitly supported trusted identity
field). Missing or ambiguous identity is rejected. Caller-supplied event identity is never
trusted. Logs are JSON and contain only safe status and correlation/approval/execution/action
identifiers; request bodies, resource details, hashes, credentials, exception text, and
hidden reasoning are not logged.

The wrappers use injectable clock and service/executor factories for offline tests. The
repository's `InMemoryApprovalRepository` and fake executor are test doubles only; they are
not production persistence or authorization implementations. The production factories must
provide the separately approved DynamoDB-backed approval service and remediation executor
without broadening the existing IAM boundaries.

## Proposed deployment settings

These are explicit proposed values for later review; none are applied by this local task:

| Setting | Approval | Remediation |
|---|---|---|
| Runtime | `python3.13` | `python3.13` |
| Architecture | `arm64` | `arm64` |
| Memory | `256 MB` | `256 MB` |
| Timeout | `30 seconds` | `30 seconds` |
| CloudWatch log retention | `7 days` | `7 days` |
| Function names | `agentic-aws-network-ops-lab-phase8-approval` | `agentic-aws-network-ops-lab-phase8-remediation` |

Environment variables must contain non-secret, deployment-scoped configuration only. The
proposed allowlist is `PHASE8_AWS_REGION=eu-west-1`,
`PHASE8_APPROVAL_TABLE_NAME=agentic-aws-network-ops-lab-phase8-approvals`, and immutable
manifest/configuration identifiers required by the approved adapter. No AWS credentials,
access keys, tokens, approval payloads, request hashes, resource overrides, or model-provided
parameters may be supplied through environment variables. Secrets must not be added to the
wrapper configuration; the Lambda execution role is the only AWS credential source.

Both functions should carry these tags:

- `Project=agentic-aws-network-ops`
- `Environment=lab`
- `ManagedBy=terraform`
- `Component=phase8-approval` or `phase8-remediation`

The proposed settings require separate approval and remain absent from the current
Terraform resource graph.

## Local AWS-backed adapter layer

`agentic_aws_network_ops.approval.dynamodb_repository.DynamoDBApprovalRepository`
implements the existing `ApprovalRepository` contract using an injected low-level
boto3-style DynamoDB client. It uses strong reads, `attribute_not_exists(approval_id)`
conditional writes, and a conditional `APPROVED` to `EXECUTING` update. A duplicate approval
ID cannot overwrite an existing record. Claim outcomes are `NOT_FOUND`, `NOT_APPROVED`,
`EXPIRED`, `CLAIMED`, `REPLAY_SAME_EXECUTION`, or `REPLAY_DIFFERENT_EXECUTION`. A same-
execution replay returns the stored result and a different execution can never claim or
persist against the record. Execution-result persistence is owner-conditional and
same-result idempotent. TTL is derived from the UTC `expires_at` value into `ttl_epoch`.

`agentic_aws_network_ops.remediation.aws_executor.AwsRemediationExecutor` receives the
DynamoDB approval repository, an injected EC2 client, and a trusted
`TrustedPhase8Resources` configuration containing the destination security-group ID,
destination VPC ID, and source VPC ID. Resource IDs and VPC IDs in that configuration are
deployment inputs only; Lambda events cannot supply or override them. The immutable manifest
assigns each route-table group a VPC role (`source` for the `10.20.0.0/16` route tables and
`destination` for the `10.10.0.0/16` route tables) and assigns the NACL to the destination
role. The executor resolves the action and scenario through the immutable manifest, validates
every approval binding, performs a READ preflight, claims approval atomically, executes only
the manifest operation, performs a separate post-write READ verification, and persists the
execution result. Same-execution retries return the stored result before any EC2 read or
write. Missing, denied, expired, misbound, differently owned, or wrong-VPC resources fail
closed.

Route-table preflight and post-write verification require every returned route table's
`VpcId` to match its immutable manifest VPC role and the trusted source/destination VPC
configuration. NACL preflight and post-write verification require the returned ACL `VpcId`
to match the trusted destination VPC. These checks occur in the shared `_preflight()` path,
which is called both before the write and by independent verification after the write.

The exact adapter write boundaries are:

- `restore_security_group_ingress`: `AuthorizeSecurityGroupIngress` with the manifest TCP/
  443/`10.10.0.0/16` values on the trusted destination security group only.
- `restore_vpc_peering_route`: `CreateRoute` for absent routes or `ReplaceRoute` for wrong
  routes, using only the four route-table/destination-CIDR/peering mappings in the frozen
  manifest. No route deletion is supported.
- `restore_network_acl_entry`: `ReplaceNetworkAclEntry` for the fixed destination NACL,
  ingress rule 100, TCP/443, `10.10.0.0/16`, and `allow`. No NACL deletion or arbitrary rule
  input is supported.

The adapter rejects wrong resource ownership tags/VPC bindings, caller-supplied resource or
write parameters, unsupported actions, deletes, revokes, DNS changes, and arbitrary EC2
operations. AWS errors are converted to safe categorized adapter errors or persisted as
failed execution results after a claim; raw AWS request/error details are not returned in
structured results. Verification failure conservatively sets `status=failed`,
`terraform_drift=true`, and `reconciliation_required=true`.

The composition helpers in `adapters/phase8_aws.py` accept already-created boto3-style
clients, so all adapter behavior remains mockable and the wrappers do not create clients
implicitly. A live deployment factory must inject the approved DynamoDB and EC2 clients,
table name, authorized approval principals, and trusted resource configuration.

### Required runtime permissions

The adapter code requires the following permissions from the separately approved execution
roles; this task does not attach or modify any IAM policy:

- Approval role: `dynamodb:PutItem` and `dynamodb:GetItem` on the Phase 8 approval table.
- Remediation role: `dynamodb:GetItem` and `dynamodb:UpdateItem` on the Phase 8 approval table.
- Remediation READ preflight/verification: `ec2:DescribeSecurityGroups`,
  `ec2:DescribeRouteTables`, and `ec2:DescribeNetworkAcls`, scoped to the approved region
  and resources/conditions supported by AWS.
- Remediation WRITE: only the existing four allowlisted actions:
  `ec2:AuthorizeSecurityGroupIngress`, `ec2:CreateRoute`, `ec2:ReplaceRoute`, and
  `ec2:ReplaceNetworkAclEntry`.
- Both functions additionally require the separately approved CloudWatch Logs permissions.

The currently deployed remediation role contains the DynamoDB permissions and four EC2
writes but does not contain the three EC2 describe permissions required by this adapter.
That is an explicit deployment prerequisite, not an IAM change made here.


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
