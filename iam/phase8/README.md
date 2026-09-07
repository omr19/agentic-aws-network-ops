# Phase 8 deployment-readiness IAM boundary

The JSON files in this directory are offline policy fixtures. The Terraform
`phase8_readiness` module defines separate Approval Lambda and remediation Lambda roles
when explicitly enabled. Diagnostic and Runtime roles are not reused.

The remediation role has separate policy fixtures for the four ADR 022 EC2 write actions,
the three EC2 read actions required for preflight/verification, and scoped DynamoDB
consumption/result persistence. `remediation-read-permissions.json` is the unattached
read-policy fixture. Approval has only DynamoDB approval persistence. Lambda logging
permissions, packaging, resource-based invocation policy, AgentCore policy
engine/interceptor permissions, and any live role attachment require a separate AWS/IAM
approval gate. No policy fixture is attached or deployed by local validation.
