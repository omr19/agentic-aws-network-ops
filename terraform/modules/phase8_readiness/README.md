# Phase 8 deployment-readiness module

This opt-in module defines the supported persistent approval boundary: one tagged,
on-demand DynamoDB table with TTL and separate Approval Lambda/remediation Lambda
execution roles. The remediation role uses separate inline policies for the four ADR 022 EC2 write
capabilities, the three EC2 read actions required for preflight/verification, and
approval-table consumption/result persistence.

The module is disabled by default from the lab root, so normal Terraform validation/plan work
creates no Phase 8 resources. When explicitly enabled, it also creates the two local
ZIP-backed Lambda functions and their explicitly retained seven-day CloudWatch log groups.
The runtime packages now include strict, role-backed deployment factories. Approval requires a
non-empty deployment-managed IAM principal allowlist and a trusted authenticated principal
from the eventual Gateway/authorized invocation adapter; remediation requires Terraform-managed
trusted resource IDs. Missing or malformed configuration fails closed. The module does not
create AgentCore resources, Lambda resource-based invocation policies, or authenticated
Gateway configuration. Destroying the opt-in module removes the table, roles, functions, and
log groups; production retention/export policy must be approved before teardown.
