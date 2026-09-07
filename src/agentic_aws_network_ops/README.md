# Python Package Boundaries

The package separates agent orchestration, approval, diagnostic READ logic, remediation
WRITE logic, shared types, and thin deployment adapters.

Phase 5 implements the fixed nine-tool diagnostic boundary under `diagnostics/` with
dependency-injected Boto3 clients and version-controlled JSON Schema validation. The
thin adapter under `adapters/diagnostic_lambda.py` constructs AWS clients only at the
deployment boundary and emits sanitized structured tool-call metadata. The local
P5-04 path adds typed Runtime/Gateway boundaries, an injected IAM/SigV4 transport seam,
and an offline Gateway-to-diagnostic target adapter. Routine tests use Botocore Stubber,
fakes, and saved events without live credentials or AWS calls.

Lambda deployment packages must include the repository `schemas/` directory at the
package root. The validator resolves it through `LAMBDA_TASK_ROOT`; local or custom
packaging workflows may set `DIAGNOSTIC_SCHEMA_ROOT` explicitly.

Phase 8 contains an approval-gated remediation workflow under `remediation/workflow.py`. It models separate proposal, explicit approval/denial, single-use execution, and READ verification contracts. The local workflow and deployment-boundary adapters are validated; trusted authenticated approval and live production remediation remain deferred under the bounded-validation scope.
