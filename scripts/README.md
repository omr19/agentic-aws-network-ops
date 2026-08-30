# Local packaging scripts

`package_diagnostic_lambda.py` prepares the ignored local Phase 5 diagnostic Lambda ZIP.
It uses the frozen runtime dependency graph, includes the source package and complete
schema tree, writes checksum/manifest files, and runs an offline fake-service handler
smoke test. It does not contact AWS or perform deployment.

`package_phase8_lambdas.py` builds deterministic, source-only ZIPs for the Phase 8
Approval and Remediation Lambda boundaries under `.artifacts/phase8-approval-lambda/`
and `.artifacts/phase8-remediation-lambda/`. ZIP timestamps and member ordering are
fixed; each output includes a ZIP SHA-256 checksum, per-member manifest, and JSON package
manifest. The script runs offline import/smoke tests and never invokes AWS. Run
`verify_phase8_lambda_packages.py` to recheck checksums and members without rebuilding.

The packages contain interfaces and contracts only. They do not include AWS adapters,
DynamoDB clients, Lambda deployment configuration, logging permissions, or AgentCore
configuration. The production Lambda wrapper must obtain authenticated identity from
IAM/SigV4, emit structured logs containing correlation/request/approval/execution IDs
without secrets or hidden reasoning, and use the separately approved roles.

`phase6_scenario_harness.py` models the Phase 6 `scenario -> diagnose -> restore ->
verify` lifecycle offline. It mirrors the Terraform `scenario_effects` contract, prints or
emits JSON evidence, and runs no Terraform, AWS, or IAM operations.
