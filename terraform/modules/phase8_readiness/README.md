# Phase 8 deployment-readiness module

This opt-in module defines the supported persistent approval boundary: one tagged,
on-demand DynamoDB table with TTL and separate Approval Lambda/remediation Lambda
execution roles. The remediation role uses separate inline policies for the four ADR 022 EC2 write
capabilities, the three EC2 read actions required for preflight/verification, and
approval-table consumption/result persistence.

Lambda functions, packages, AgentCore policy resources, and Gateway interceptors are
not created here. Lambda code uses the local interfaces under `src/`; packaging and
AgentCore policy/interceptor deployment require a later approved AWS gate. The module
is disabled by default from the lab root, so normal Terraform validation/plan work
creates no Phase 8 resources. Destroying the opt-in module removes the table and roles;
production retention/export policy must be approved before teardown.
