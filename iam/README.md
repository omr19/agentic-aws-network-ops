# IAM Policy Contracts

`phase5/` contains local, deployment-agnostic IAM contracts for the three separate
Phase 5 execution identities. They are not attached to AWS roles by this task.

- Runtime may invoke only the approved AgentCore Gateway.
- Gateway may invoke only the diagnostic Lambda target.
- Diagnostic execution may call only the AWS evidence APIs used by the nine READ tools.
- Runtime and Gateway trust policies require the AgentCore source account and regional
  source ARN pattern to reduce confused-deputy risk.

`${region}`, `${account_id}`, `${gateway_id}`, `${diagnostic_function_name}`, and
`${diagnostic_log_group_name}` are explicit deployment placeholders. P5-04 must render
them to exact resource ARNs and add any separately reviewed AgentCore Policy permissions
needed by the deployed Gateway. It must not replace them with account-wide wildcards.

The diagnostic contract deliberately includes `logs:StartQuery`. AWS names this action
with `Start`, but it starts a Logs Insights read query and does not modify network
infrastructure. `ec2:StartNetworkInsightsAnalysis` is deliberately excluded because AWS
classifies it as Write; the Phase 5 tool describes existing analyses only.

The future-demo `phase7/observability-read-permissions.json` fixture is separate from
Runtime and diagnostic policies. It permits only project-instance observation, Flow Logs
discovery, Logs Insights discovery/query/results, and CloudWatch metric reads. Actual role
creation or attachment requires a separate IAM approval gate; this local task does not
broaden or modify any existing role.

Local tests prove identity separation, exact allowed actions, resource scoping where AWS
supports it, and absence of IAM, STS, remediation, Lambda invocation, and infrastructure
mutation authority from the diagnostic identity. Live role creation, attachment, IAM
simulation, and AWS deployment require separate approval.
