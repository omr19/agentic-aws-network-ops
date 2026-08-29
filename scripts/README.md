# Local packaging scripts

`package_diagnostic_lambda.py` prepares the ignored local Phase 5 diagnostic Lambda ZIP.
It uses the frozen runtime dependency graph, includes the source package and complete
schema tree, writes checksum/manifest files, and runs an offline fake-service handler
smoke test. It does not contact AWS or perform deployment.

`phase6_scenario_harness.py` models the Phase 6 `scenario -> diagnose -> restore ->
verify` lifecycle offline. It mirrors the Terraform `scenario_effects` contract, prints or
emits JSON evidence, and runs no Terraform, AWS, or IAM operations.
