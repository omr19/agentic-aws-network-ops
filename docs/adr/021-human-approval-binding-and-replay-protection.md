# ADR 021 — Human Approval Binding and Replay Protection

## Status
Accepted

## Decision
Natural-language confirmation is not an approval control. The agent first creates a
canonical remediation proposal containing correlation/session IDs, tool, region,
resource, operation, exact parameters, evidence, expected result, and a SHA-256 hash of
that request.

An authenticated human explicitly approves the proposal through a dedicated Approval
Lambda that is invoked directly with IAM/SigV4. The Approval Lambda is not a Gateway
target or MCP tool, and Agent Runtime, diagnostic, and remediation identities cannot
invoke it.

Store the approval in a dedicated DynamoDB on-demand table with:

- UUID approval, correlation, and policy-session identifiers
- exact canonical request hash and approved operation fields
- authenticated approver principal
- `APPROVED` status, creation time, five-minute expiry, and TTL
- execution/consumption fields used for idempotency and audit

## Enforcement chain

1. AgentCore Policy runs default-deny and forbid-wins.
2. A temporal Dogwood policy requires a matching proposal earlier in the same policy
   session and within the permitted window.
3. A Gateway request interceptor validates approval existence, hash, approver, status,
   expiry, session, correlation, tool, resource, operation, and parameters.
4. The remediation Lambda conditionally and atomically changes `APPROVED` to
   `EXECUTING` before calling AWS.
5. The dedicated remediation IAM role independently limits the AWS API and resources.
6. The result becomes `COMPLETED` or `FAILED`; READ diagnostics verify the outcome.

The interceptor validates but does not consume the record because Gateway may retry it.
The remediation Lambda uses an execution ID so an identical retry returns the recorded
result instead of repeating the write. Expired, changed, failed, or reused requests
require a new approval.

## Policy session and rollout

Use a UUIDv4 in `x-amzn-bedrock-agentcore-policy-session-id` for every related Gateway
request. Validate policies in `LOG_ONLY`, including positive and negative cases, before
promoting them to `ENFORCE`. Scope the Gateway role permissions required for policy and
temporal identity propagation to the specific project resources.

## Required security tests

- conversational “Yes” without the explicit approval operation is denied
- expired, reused, changed-resource, changed-parameter, and wrong-session approvals are denied
- Agent Runtime and tool identities cannot invoke the Approval Lambda
- policy permit plus IAM deny produces no change
- IAM capability plus absent approval produces no change
- interceptor/Gateway retries cannot produce duplicate writes
- verification failure is reported and Terraform drift is surfaced

## Consequences
The Approval Lambda and DynamoDB table add small, justified components and cost. They
must use least privilege, project tags, TTL, logging without sensitive values, and
teardown verification. Approval expresses intent, AgentCore Policy authorizes the tool,
the interceptor validates binding, and IAM authorizes the AWS operation.

## References

- [AgentCore temporal policies](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-temporal.html)
- [Policy sessions and identity propagation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-session-based-temporal.html)
- [Gateway interceptors](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-interceptors.html)
- [Policy enforcement modes](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_GatewayPolicyEngineConfiguration.html)
