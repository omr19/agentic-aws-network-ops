# Phase 5 Validation Matrix

| Path or control | Validation | Result | Evidence |
|---|---|---|---|
| Local diagnostic contracts | Focused/full offline pytest suite | PASS (local contract; test count varies by checkpoint) | Current test commands and Phase 10 matrix |
| Local Runtime HTTP boundary | `/ping` and `/invocations` contract | PASS (local contract) | `runtime_entrypoint.py` |
| Diagnostic Lambda | Sanitized historical smoke evidence | PASS (historical deployed evidence; not revalidated in this local task) | `phase-5-lambda-smoke.json` |
| Gateway target | Sanitized historical SigV4 smoke evidence | PASS (historical deployed evidence; not revalidated in this local task) | `phase-5-gateway-smoke.json` |
| AgentCore Runtime | Runtime → Gateway → Lambda call | DEFERRED / historical evidence retained separately; current local selector is fixed `describe_vpcs` | `phase-5-runtime-smoke.json`; `phase-10-validation-matrix.md` |
| Runtime IAM | Historical simulation evidence | DEFERRED for current live revalidation | `phase-5-runtime-iam-simulation.json` |
| Artifact integrity | Historical artifact evidence | DEFERRED for current live revalidation | `phase-5-runtime-iam-simulation.json` |
| Gateway schema hardening | Explicit nine-contract input properties | PASS (local contract; historical READY claim retained as dated evidence) | Kiro reconciliation; Phase 10 matrix |

The Runtime, Gateway, and diagnostic Lambda are retained temporarily for portfolio
demonstration. No remediation or write path was exercised.
