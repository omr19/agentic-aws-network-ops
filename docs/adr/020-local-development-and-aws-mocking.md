# ADR 020 — Local Development and AWS Mocking

## Status
Accepted

## Decision
Use one implementation of each tool's business logic for local and deployed execution.
Separate every tool into:

1. Version-controlled input/output schema
2. Framework-independent Python logic with dependency-injected AWS clients
3. Thin diagnostic or remediation Lambda adapter

Use `pytest`, Botocore `Stubber`, JSON Schema validation, local Gateway/Lambda event
fixtures, and a small handler runner for ordinary local tests. Unit tests make no real
AWS calls and require no live AWS credentials. Use `agentcore dev` for local agent
execution, inspection, hot reload, and traces with deterministic stub tool responses.

## Test progression

1. Schema validation and negative inputs
2. Tool logic with stubbed AWS requests/responses
3. Diagnostic/remediation Lambda adapter dispatch and boundary tests
4. Local agent tool-selection and explanation tests
5. Controlled deployed Gateway/Lambda integration only after local checks pass

Required failure tests include authorization denial, throttling, timeout, malformed or
partial evidence, conflicting evidence, unsupported WRITE scope, and attempted WRITE
dispatch through the diagnostic adapter.

## Consequences
Local and Lambda behavior share the same core code while AWS cost and mutation risk are
avoided during routine development. `Stubber` validates expected API operations and
parameters instead of merely returning loose mocks. Saved event fixtures make Gateway
adapter behavior reproducible.

Kiro is used at meaningful independent review gates—schema review, IAM/security review,
coverage review, and final implementation diff—not for repetitive local test execution.

## References

- [AgentCore CLI local development](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-get-started-cli.html)
- [Gateway Lambda target configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-api-target-config.html)
