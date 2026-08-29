# Phase 5 Diagnostic Lambda Packaging

The local packaging command creates an ignored artifact under `.artifacts/` and does not
contact AWS, upload code, invoke Lambda, change IAM, or deploy AgentCore:

```text
uv run python scripts/package_diagnostic_lambda.py
```

The script:

1. Exports only runtime dependencies from the frozen `uv.lock` (`--no-dev`).
2. Installs Python 3.13 `x86_64-manylinux2014` binary wheels into temporary staging.
3. Copies the complete `src/agentic_aws_network_ops/` package.
4. Copies the complete `schemas/` tree to the ZIP package root.
5. Excludes virtual environments, Terraform directories/state, caches, bytecode, coverage,
   and unrelated repository files.
6. Creates deterministic `diagnostic-lambda.zip` contents with normalized timestamps.
7. Writes a SHA-256 checksum and per-member SHA-256 manifest.
8. Extracts the artifact in a temporary directory and smoke-tests
   `agentic_aws_network_ops.adapters.diagnostic_lambda.handler` with an injected fake
   service. No Boto3 client is constructed by the smoke test. On a macOS development host,
   the package and schemas are imported from the artifact while the host's compatible
   development dependencies are used; the artifact still contains Linux-targeted wheels.
   On a compatible Linux x86_64 host, the smoke test imports the complete extracted tree.

Expected local outputs:

```text
.artifacts/diagnostic-lambda/diagnostic-lambda.zip
.artifacts/diagnostic-lambda/diagnostic-lambda.zip.sha256
.artifacts/diagnostic-lambda/diagnostic-lambda.zip.manifest.txt
```

Verify required package members locally:

```text
unzip -l .artifacts/diagnostic-lambda/diagnostic-lambda.zip
sha256sum .artifacts/diagnostic-lambda/diagnostic-lambda.zip
```

The manifest must include at least:

```text
agentic_aws_network_ops/adapters/diagnostic_lambda.py
schemas/common/result-envelope.schema.json
schemas/diagnostic/read-tools.schema.json
```

The artifact targets Python 3.13 on Linux x86_64, matching the planned Lambda runtime
architecture. A Lambda ARM64 deployment requires a separately built ARM64 artifact. The
artifact is deployment-ready only after the separate IAM simulation, role attachment,
Lambda configuration, Gateway target mapping, and AWS approval gates in
`phase-5-deployment-readiness.md` are completed.
