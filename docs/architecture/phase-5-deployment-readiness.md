# Phase 5 Deployment Readiness Plan

## Purpose and authority

This document is a **local deployment-readiness plan**, not deployment authorization. It
translates the approved Phase 5 READ implementation into a gated sequence for a future,
separately authorized AWS deployment. It does not authorize AWS API calls, IAM changes,
AgentCore deployment, Lambda deployment, Terraform apply/destroy, or destructive cleanup.

The approved architecture remains authoritative:

- One AgentCore Runtime hosts the operational agent outside the workload VPCs.
- AgentCore Gateway is the managed MCP and policy boundary.
- One non-VPC diagnostic Lambda exposes exactly the nine READ contracts.
- Diagnostic READ and future remediation WRITE identities and targets remain separate.
- Deterministic AWS evidence establishes facts; the agent does not invent reachability.
- IAM/SigV4, Gateway authorization, and tool execution remain independent controls.
- No approval, remediation, WRITE tool, generic AWS execution tool, or `StartNetworkInsightsAnalysis`
  path is introduced by Phase 5 deployment.

## Current local readiness

The following work is complete locally and does not contact AWS:

- Typed Runtime-to-Gateway and Gateway-to-diagnostic boundaries.
- Deterministic local nine-tool READ allowlist.
- Injected non-secret IAM/SigV4 configuration and transport seam.
- Diagnostic Lambda dispatch seam with Boto3 construction retained at the deployment handler.
- Versioned schemas and the required schema package-root convention.
- Four sanitized event fixtures covering Runtime request, valid Gateway forwarding, invalid
  Gateway rejection, and diagnostic result return.
- Offline fake/Stubber tests for the composed Runtime → Gateway → diagnostic path.
- Separate local IAM contracts under `iam/phase5/`.

The local tests prove composition and contract behavior only. They do **not** prove that
an AWS role is attached correctly, that AgentCore accepts the rendered policies, that a
Gateway target has the expected event mapping, or that deployed SigV4 authorization works.
Those are future gates below.

## Required inputs and invariant controls

Before any AWS gate is requested, prepare these inputs locally and keep them free of
secrets, credentials, Terraform state, raw account identifiers, and hidden model reasoning:

- Approved source revision and package/artifact hash.
- Target Region, expected AWS account, project/environment tags, and resource naming plan.
- Rendered values for `${region}`, `${account_id}`, `${gateway_id}`,
  `${diagnostic_function_name}`, and `${diagnostic_log_group_name}`. Rendered values must
  be reviewed before use and must not be committed to public artifacts.
- Diagnostic Lambda handler:
  `agentic_aws_network_ops.adapters.diagnostic_lambda.handler`.
- Python runtime/dependency lock, package manifest, and the complete `schemas/` tree at the
  Lambda package root. The validator may use `DIAGNOSTIC_SCHEMA_ROOT` only for a reviewed
  non-default packaging layout.
- A named diagnostic log group and retention policy for controlled Flow Logs queries.
- Sanitized request fixtures and a correlation/session-ID convention.
- A deployment operator identity with narrowly reviewed provisioning permissions. This is
  distinct from the Runtime, Gateway, and diagnostic execution identities.

The existing Phase 5 policies are contracts, not rendered or attached AWS policies. Do not
replace their placeholders with `*` or account-wide resource patterns.

## Gated deployment sequence

Each step has an explicit gate. A gate marked **AWS approval required** must not be crossed
by completing a prerequisite or by natural-language confirmation from the agent.

### 0. Confirm local readiness and deployment freeze

**Purpose:** Establish that only the approved local READ implementation is being promoted.

- **Required inputs:** Clean reviewable source scope, local test results, package manifest,
  schema manifest, IAM contract files, and the approved target Region/account context.
- **Expected AWS resources:** None.
- **IAM permissions:** None. Local checks use fakes and Stubber only.
- **Validation evidence:** Full local test result; Ruff/mypy/security results; schema and
  fixture manifest; source-to-handler mapping; confirmation that no remediation package,
  WRITE policy, approval path, or generic AWS tool is included.
- **Rollback/cleanup:** Discard the local artifact or return to the prior local revision.
  No AWS rollback is possible or needed.
- **Approval gate:** **No AWS approval required** for local preparation. A separate review
  must approve progression to Step 1 and identify the deployment operator.

### 1. Build the diagnostic Lambda package

**Purpose:** Produce a reproducible, dependency-complete artifact for the diagnostic READ
Lambda without deploying it.

- **Required inputs:** Approved source revision, Python runtime version, locked dependencies,
  handler path, schemas, package layout, target architecture, and artifact destination.
- **Expected AWS resources:** None during packaging. The local artifact and its checksum are
  the only outputs.
- **IAM permissions:** None for local packaging. The eventual deployment operator may need
  narrowly scoped Lambda package-upload permissions depending on the selected packaging
  mechanism; these are not diagnostic execution permissions.
- **Validation evidence:** Artifact checksum; file manifest; import/handler smoke test;
  proof that `schemas/common/result-envelope.schema.json` and
  `schemas/diagnostic/read-tools.schema.json` plus referenced files are at the package
  root; dependency/license/security scan; proof that no credentials, account IDs, state,
  or hidden reasoning are packaged.
- **Rollback/cleanup:** Delete the local artifact and any temporary build directory. Do not
  upload an artifact until the next approval gate is granted.
- **Approval gate:** **AWS approval required before any upload or Lambda API call.** Local
  packaging itself does not authorize deployment.

### 2. Create or select the diagnostic IAM execution role

**Purpose:** Establish the separate, least-privileged identity used only by the diagnostic
Lambda.

- **Required inputs:** Rendered account/Region/log-group/function values, role name, the
  diagnostic trust policy, the diagnostic READ policy, and a separately reviewed Lambda
  basic-execution logging policy if required by the runtime.
- **Expected AWS resources:** One diagnostic Lambda execution role and its policy attachment
  or inline policy. No Runtime, Gateway, remediation, approval, or deployment permissions
  belong on this role.
- **IAM permissions:**
  - The diagnostic policy allows exactly the ten evidence actions required by the nine
    READ tools: the seven EC2 describe/analysis actions, `logs:StartQuery`,
    `logs:GetQueryResults`, and `cloudwatch:GetMetricStatistics`.
  - EC2 and result/metric statements are Region-conditioned. `logs:StartQuery` is scoped
    to the named project log group. `logs:StartQuery` remains a read query operation;
    `ec2:StartNetworkInsightsAnalysis` remains prohibited.
  - The Lambda service trust is separate from Runtime and Gateway trust. The role must not
    contain `iam:PassRole`, `sts:AssumeRole`, Lambda invocation, remediation, or generic
    wildcard authority.
  - Lambda basic execution log writes, if needed, must be a separately reviewed policy
    limited to the function's log group. They are not part of the diagnostic evidence
    policy and must not be silently added to it.
  - The provisioning operator requires separately approved IAM role/policy management
    permissions. Those permissions must never be attached to the diagnostic role.
- **Validation evidence:** Rendered policy diff; trust-principal review; IAM Access Analyzer
  or equivalent policy validation; IAM simulation for every required allow and representative
  forbidden actions; confirmation that the role has no unreviewed attached, inline, or
  permissions-boundary policy; exact role ARN recorded in protected deployment evidence.
- **Rollback/cleanup:** Before any role deletion, detach the function and policies and
  confirm no other resource uses the role. Detach/delete operations are destructive IAM
  changes and require a separate approval. If a pre-existing role is selected, do not
  remove unrelated policies during rollback.
- **Approval gate:** **AWS/IAM approval required.** IAM simulation is a mandatory gate before
  Lambda deployment; static JSON tests alone are insufficient.

### 3. Deploy the diagnostic Lambda

**Purpose:** Publish only the diagnostic READ adapter and connect it to the approved
execution role.

- **Required inputs:** Artifact checksum, handler path, runtime/architecture, diagnostic
  role ARN, timeout/memory/concurrency settings, Region, environment configuration, log
  group name, and package-root schema verification.
- **Expected AWS resources:** One non-VPC diagnostic Lambda function, optionally a reviewed
  version/alias, and its CloudWatch log group. No VPC attachment, NAT, endpoint, approval
  Lambda, remediation Lambda, or Gateway is created by this step.
- **IAM permissions:**
  - The deployment operator needs separately approved Lambda create/update/read and
    narrowly scoped `iam:PassRole` for the diagnostic role. Package storage permissions
    depend on the chosen artifact path.
  - The function execution role uses only the reviewed diagnostic READ policy plus the
    separately reviewed logging policy. It cannot invoke Gateway, Approval, or
    Remediation functions and cannot change IAM or infrastructure.
- **Validation evidence:** Function configuration and code checksum; handler invocation
  configuration; role ARN; schema-root inspection; log-group name/retention; tags; no-VPC
  configuration; sanitized startup/log evidence; an approved read-only smoke invocation
  using a known project tag or fixture-compatible input.
- **Rollback/cleanup:** Prefer reverting an alias/version or restoring the prior function
  code/configuration. Deleting the function, versions, or log group is destructive and
  cost/lifecycle-sensitive; require explicit cleanup approval and preserve evidence first.
- **Approval gate:** **AWS deployment approval required.** A Lambda invocation is an AWS
  action and may create log/cost records; it is not covered by local tests.

### 4. Create AgentCore Gateway and register only the diagnostic target

**Purpose:** Establish the managed MCP and policy boundary for the READ target.

- **Required inputs:** Gateway name/ID, Region/account, diagnostic Lambda ARN (and version
  or alias choice), target protocol/event mapping, Gateway execution role, authentication
  mode, policy/interceptor configuration, and the approved target timeout behavior.
- **Expected AWS resources:** One AgentCore Gateway, one diagnostic Lambda target, and any
  required Gateway execution-role or policy configuration. No remediation target or generic
  AWS/Boto3/shell target is registered.
- **IAM permissions:**
  - The Gateway execution role trusts `bedrock-agentcore.amazonaws.com` with the reviewed
    source-account and regional source-ARN conditions.
  - Its target permission is exactly `lambda:InvokeFunction` on the rendered diagnostic
    function ARN from `gateway-permissions.json`.
  - Any additional AgentCore policy/interceptor permissions required by the deployed
    Gateway must be separately reviewed and scoped; the local contract does not authorize
    broad Gateway management or policy permissions.
  - The deployment operator needs separately approved AgentCore Gateway/target management
    and `iam:PassRole` permissions. These are provisioning permissions, not Gateway runtime
    authority.
- **Validation evidence:** Gateway ARN/ID; target inventory; target Lambda ARN and
  qualifier; execution-role trust/policy; configured inbound authorization; valid READ
  request mapping; invalid/generic request rejection; no remediation target; sanitized
  Gateway logs/traces; correlation/session propagation.
- **Rollback/cleanup:** Remove the target before deleting the Gateway. Preserve policy and
  invocation evidence. Gateway/target deletion can affect access and incur operational
  impact; it requires explicit approval and must not be performed as an automatic test
  failure response.
- **Approval gate:** **AWS AgentCore deployment approval required.** Gateway creation and
  target registration are external side effects.

### 5. Create/configure the single AgentCore Runtime

**Purpose:** Host the one operational agent outside the workload VPCs and connect it to the
Gateway without adding authority to the model.

- **Required inputs:** Runtime artifact/configuration, Runtime name/Region, Gateway endpoint
  or ARN, session/correlation configuration, model/runtime settings, execution role,
  logging/observability settings, and no-VPC placement confirmation.
- **Expected AWS resources:** One AgentCore Runtime and its required execution/configuration
  resources. No VPC attachment, workload-network route, remediation capability, or
  persistent Memory authority is introduced.
- **IAM permissions:**
  - The Runtime execution role trusts `bedrock-agentcore.amazonaws.com` with the reviewed
    source-account and regional source-ARN conditions.
  - Its Phase 5 permission is exactly `bedrock-agentcore:InvokeGateway` on the rendered
    Gateway ARN from `runtime-permissions.json`.
  - Any baseline Runtime logging/model permissions and the separate human/operator
    caller permission must be designed and reviewed for the selected Runtime deployment;
    they are not implied by the local P5-04 seam or by the Runtime-to-Gateway policy.
  - The Runtime role must not invoke Approval or Remediation and must not receive
    diagnostic AWS evidence permissions.
- **Validation evidence:** Runtime ARN/configuration; no-VPC placement; execution-role
  trust/policy; Gateway reference; sanitized local/deployed configuration; correlation and
  session behavior; confirmation that Runtime cannot directly call diagnostic AWS APIs or
  future WRITE targets.
- **Rollback/cleanup:** Disable or revert the Runtime revision first. Runtime deletion and
  associated log/observability cleanup are cost-sensitive and require explicit approval.
- **Approval gate:** **AWS AgentCore Runtime deployment approval required.**

### 6. Configure IAM/SigV4 inbound authorization and run mandatory simulation

**Purpose:** Bind the native client, Runtime, Gateway, and Lambda roles without placing
credentials in code, fixtures, logs, or Git.

- **Required inputs:** Rendered Runtime/Gateway/function ARNs, account/Region, SigV4
  service/endpoint/path, inbound authorization mode, caller principal, trust policies,
  resource policies if used, and an allow/deny test matrix.
- **Expected AWS resources:** IAM policy/trust updates and AgentCore authorization settings
  only. No network or remediation resources.
- **IAM permissions:**
  - Human/native caller: the separately reviewed permission needed to invoke the Runtime
    and/or Gateway through IAM/SigV4. The exact deployed API action/resource must be
    verified against the selected AgentCore invocation path; it is not represented by the
    local placeholder transport.
  - Runtime: scoped `bedrock-agentcore:InvokeGateway` only.
  - Gateway: scoped `lambda:InvokeFunction` only for the diagnostic Lambda target, plus
    separately approved AgentCore policy permissions if required.
  - Diagnostic Lambda: exact read-only evidence actions and separately reviewed logging.
  - Deployment operator: separate, time-bounded management permissions; never reuse the
    runtime or diagnostic execution role for provisioning.
- **Validation evidence:** IAM simulation or equivalent for positive and negative cases:
  Runtime can invoke only the intended Gateway; Gateway can invoke only the diagnostic
  target; diagnostic role can perform required reads; diagnostic role is denied write,
  IAM, STS, Lambda invocation, role assumption, and remediation actions; cross-Region and
  wrong-resource attempts are denied; trust-source conditions evaluate as intended.
- **Rollback/cleanup:** Remove temporary simulation-only policies and restore the prior
  policy version. IAM policy deletion, detachment, or trust changes require explicit
  approval and a documented dependency check.
- **Approval gate:** **Mandatory IAM simulation gate plus explicit IAM/SigV4 approval.** Do
  not proceed on static-policy evidence alone, and do not put access keys or session tokens
  into the client configuration.

### 7. Run deployed read-only validation

**Purpose:** Prove the deployed Runtime → Gateway → diagnostic Lambda path while preserving
zero-write and deterministic-evidence boundaries.

- **Required inputs:** Approved validation matrix, sanitized fixtures, valid/invalid request
  cases, project tag, approved Region, correlation/session IDs, existing Network Insights
  path/analysis identifiers, named diagnostic log group, and a bounded validation window.
- **Expected AWS resources:** Existing Runtime, Gateway, Lambda, IAM, and log resources only;
  read-only validation must not create a Network Insights analysis, modify routes/SGs/NACLs,
  invoke remediation, or alter Terraform-managed resources.
- **IAM permissions:** Use only the deployed Runtime/Gateway/diagnostic chain. No validation
  role may add permissions to make a test pass. The diagnostic role must use
  `DescribeNetworkInsightsAnalyses`; `ec2:StartNetworkInsightsAnalysis` remains denied.
- **Validation evidence:**
  - Healthy READ calls for all nine tool contracts and valid result envelopes.
  - Invalid schema, unknown-tool, wrong-region, wrong-resource, and malformed Gateway
    requests rejected before AWS access where applicable.
  - Authorization denial represented as a limitation, never a root cause.
  - Existing Reachability Analyzer analysis described without starting a new analysis.
  - Flow Logs query restricted to the named log group and controlled time window.
  - Correlation/session IDs visible across observable Runtime, Gateway, Lambda, and evidence
    events without prompts, credentials, account IDs, or hidden reasoning.
  - CloudTrail/IAM evidence showing no prohibited write, IAM, STS, role-assumption,
    remediation, or Lambda-configuration action by the diagnostic identity.
- **Rollback/cleanup:** Stop validation immediately on unexpected write capability,
  cross-target invocation, schema bypass, credential/log leakage, or unbounded query. Disable
  the test alias/endpoint if needed; do not automatically delete shared resources. Preserve
  failure evidence for review.
- **Approval gate:** **Explicit read-only validation approval required.** This step still
  invokes AWS services and may incur Lambda, Logs Insights, CloudWatch, or AgentCore usage.

### 8. Capture sanitized evidence and close or retain the deployment

**Purpose:** Make the deployment reproducible and auditable before any cleanup decision.

- **Required inputs:** Artifact and policy hashes, rendered resource ARNs stored in a
  protected location, correlation/session IDs, validation results, IAM simulation output,
  CloudTrail references, logs/metrics, cost tags, and cleanup decision.
- **Expected AWS resources:** No new resources. Evidence should reference existing resources
  without publishing secrets, credentials, raw account IDs, Terraform state, or hidden
  reasoning.
- **IAM permissions:** Read-only evidence access as separately approved; no policy changes
  are needed to capture local/deployment evidence. Avoid broadening permissions to fill
  inventory gaps.
- **Validation evidence:** Sanitized deployment report containing package checksum, handler,
  schema inclusion, function/Gateway/Runtime identifiers redacted or placeholderized for
  public artifacts, rendered policy review, simulation matrix, nine-tool results, denial
  results, logs/traces, and known limitations.
- **Rollback/cleanup:** Decide explicitly whether to retain the short-lived diagnostic
  deployment for a bounded demonstration window or clean it up. Retention requires owner,
  tags, budget/cost monitoring, and expiry date. Cleanup proceeds only through the approved
  destructive sequence below.
- **Approval gate:** **Evidence acceptance and separate retain/cleanup approval required.**

## Destructive and cost-sensitive cleanup sequence

Cleanup is not automatic and is not part of local readiness. If authorized, use a dependency-
aware sequence and capture evidence before each deletion:

1. Stop validation traffic and disable the client/Runtime invocation path.
2. Remove or disable the Gateway diagnostic target.
3. Disable or delete the AgentCore Runtime according to the approved retention decision.
4. Delete the Gateway only after target and policy dependencies are removed.
5. Delete or disable the Lambda version/function only after Gateway references are absent.
6. Preserve or delete the diagnostic CloudWatch log group according to the approved
   retention policy; check retention/cost implications first.
7. Detach and delete temporary IAM policies/roles only after proving no remaining consumer.
8. Do not run Terraform destroy or modify the Phase 4 network lab as part of P5 cleanup.
   The stopped Phase 4 instances and network resources remain governed by their separate
   lifecycle and authorization decisions.
9. Independently verify no unintended AgentCore, Lambda, IAM, log, or other billable
   project resource remains, and record the result.

Every deletion, IAM detachment, log deletion, or resource stop is a **destructive or
cost-sensitive action requiring explicit approval**. Preserve CloudTrail, validation,
policy, package, and cost evidence before cleanup.

## Go/no-go checklist

Deployment may be proposed only when all applicable answers are yes:

- [ ] Local tests, schema checks, lint, typing, and security checks pass.
- [ ] Artifact checksum and complete schema/package manifest are recorded.
- [ ] No secrets, credentials, state, raw account IDs, or hidden reasoning are in the
      artifact, fixtures, logs, or evidence.
- [ ] Diagnostic IAM is rendered without broad wildcards and has no WRITE/IAM/STS/Lambda-
      invocation/remediation authority.
- [ ] Runtime, Gateway, diagnostic, and future remediation identities remain separate.
- [ ] Mandatory IAM simulation covers positive, negative, wrong-resource, and wrong-Region
      cases before role attachment/deployment.
- [ ] Lambda handler, schema root, role, Region, log group, and target mapping are reviewed.
- [ ] Gateway has only the diagnostic target; no remediation or generic execution target.
- [ ] Runtime has only the approved Gateway path and no direct diagnostic AWS authority.
- [ ] Native caller SigV4 configuration contains no long-lived credentials.
- [ ] Read-only validation matrix and evidence-retention plan are approved.
- [ ] Cost window, tags, teardown owner, and cleanup approval path are recorded.
- [ ] Explicit AWS/IAM/deployment approval has been granted for the exact next step.

Until every required gate is satisfied, the correct action is to remain local-only.
