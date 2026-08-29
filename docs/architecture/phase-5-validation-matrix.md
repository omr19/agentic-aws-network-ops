# Phase 5 Validation Matrix

| Path or control | Validation | Result | Evidence |
|---|---|---|---|
| Local diagnostic contracts | Full pytest suite | PASS (86 tests) | CI/local test output |
| Local Runtime HTTP boundary | `/ping` and `/invocations` contract | PASS | `runtime_entrypoint.py` |
| Diagnostic Lambda | Tagged read-only `describe_vpcs` invocation | PASS | `phase-5-lambda-smoke.json` |
| Gateway target | SigV4 MCP `describe_vpcs` call | PASS | `phase-5-gateway-smoke.json` |
| AgentCore Runtime | Runtime → Gateway → Lambda call | PASS | `phase-5-runtime-smoke.json` |
| Runtime IAM | Gateway/S3 allowed; direct EC2, Lambda, IAM denied | PASS | `phase-5-runtime-iam-simulation.json` |
| Artifact integrity | S3 object size, AES-256, SHA-256 recorded | PASS | `phase-5-runtime-iam-simulation.json` |
| Gateway schema hardening | Explicit nine-contract input properties | PASS (9 tools, READY) | Kiro live update reconciliation |

The Runtime, Gateway, and diagnostic Lambda are retained temporarily for portfolio
demonstration. No remediation or write path was exercised.
