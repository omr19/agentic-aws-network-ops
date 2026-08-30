# Phase 10 Requirements-to-Evidence Matrix

**Scope:** bounded local closure preparation on `develop`. This matrix records repository evidence, the final read-only senior architecture/security review, and explicit gaps; it does not mark Phase 10 complete. No AWS state, current billing, deployed observability, production readiness, Terraform execution, IAM deployment, Lambda invocation, or resource lifecycle is validated by this artifact.

**Status meanings:** `PASS` means the bounded local behavior or documentation is covered and validated by an offline test or reviewed contract. `PARTIAL` means some local evidence exists but the checklist requirement is broader. `DEFERRED` means the approved bounded scope excludes live or operational validation. `OPEN` means a required review, correction, or local behavior remains unresolved.

## Senior review outcome

The final read-only senior architecture and security review was completed against the authoritative checklist and status, the approved ADR set, IAM fixtures/tests, remediation workflow, packaging, and current diff. The MVP direction remains coherent: one AgentCore operational agent, Gateway/MCP as the READ boundary, separate READ and WRITE identities, deterministic evidence, explicit human approval, and a bounded remediation manifest.

The review found that the production-shaped approval path is materially fail-closed, but the low-level `record_approval()` helper is a local/test helper rather than a complete production authorization boundary. The Terraform readiness policy has an account-scope wildcard, the current deployment environment injects only some trusted remediation resource IDs, and the route executor can issue up to four bounded route writes for one approved route-remediation operation. Packaging and resilience evidence remain local limitations. These findings are recorded below with owners and dispositions. The authoritative Phase 10 checklist remains unchanged and unchecked.

## 10.1 Functional and end-to-end testing

| Checklist item | Local evidence / contract | Scope and result | Status |
|---|---|---|---|
| Test healthy baseline | `tests/integration/test_phase6_scenarios.py`; `tests/unit/test_deterministic_diagnosis.py`; `tests/integration/test_local_agent_path.py` | Offline fixtures and Stubber cover healthy/no-finding behavior; no current live rerun. | PARTIAL |
| Test each implemented failure scenario | `tests/integration/test_phase6_scenarios.py` | SG, route, NACL, DNS fixture, and peering scenarios are locally represented with diagnosis/restore/verification assertions. | PASS (local) |
| Test deterministic diagnosis | `tests/unit/test_deterministic_diagnosis.py` | Healthy, four failure classes, incomplete/conflicting/stale/unsupported evidence, and repeatability are covered offline. | PASS (local) |
| Test incorrect/irrelevant tool-selection handling | `tests/unit/test_gateway.py::test_gateway_rejects_invalid_generic_execution_request_without_target_call`; `src/.../runtime.py::FixedToolSelector` | Unknown tools are rejected before target invocation. Semantic irrelevant selection is unresolved because the local selector is fixed and does not inspect prompts. | OPEN |
| Test agent/tool failure handling | `tests/unit/test_agent_runtime.py` and `tests/unit/test_gateway.py` | Selector, Gateway, and diagnostic exceptions deliberately propagate fail-fast; there is no structured normalization or automatic retry. Live failure behavior is not validated. | PARTIAL |
| Test remediation approval | `tests/unit/test_phase8_remediation_workflow.py`; `tests/security/test_phase8_remediation_security.py`; `tests/unit/test_phase8_aws_adapters.py` | Production-shaped local service/wrapper controls are strong, but the low-level helper is local/test-only and authenticated live ingress remains deferred. | PARTIAL |
| Test remediation denial | `tests/unit/test_phase8_remediation_workflow.py`; `tests/security/test_phase8_remediation_security.py` | Denied, absent, expired, and misbound approval paths produce no adapter/write call. | PASS (local) |
| Test post-remediation verification | `tests/unit/test_phase8_remediation_workflow.py`; `tests/unit/test_phase8_aws_adapters.py` | Separate verifier success, local verifier failure result/exception, and AWS-backed false verification are covered offline. Live verification remains deferred. | PARTIAL |
| Test representative repeated runs for consistency | `tests/integration/test_local_agent_path.py` | Repeated Runtime → Gateway → diagnostic runs assert equivalent results, stable bindings, and no accumulated Stubber state. | PASS (local) |
| Document test matrix and results | This document; `docs/evidence/phase-8/local-remediation-validation.json`; validation results below | Checklist rows, exact local results, senior findings, owners, and deferred/open items are recorded here. | PASS (bounded documentation) |

## 10.2 Architecture review

| Checklist item | Local evidence / contract | Scope and result | Status |
|---|---|---|---|
| Review implementation against approved Phase 2 architecture | `docs/architecture/phase-2-design.md`; ADRs 005, 006, 009, 012, 013, 015, 019, 021, 022, 023 | Review completed. The overall direction is coherent, but the account wildcard, incomplete environment bindings, and route-write cardinality require explicit disposition. | PARTIAL |
| Document intentional deviations | This matrix; Phase 5/8/9 bounded-scope documents | Fixed selector, local adapters, fail-fast policy, package limitations, incomplete live bindings, and deferred live controls are recorded with owners below. | PASS (bounded documentation) |
| Reassess single-agent vs. multi-agent decision | ADR 005; `docs/requirements.md` | Single-agent remains appropriate for the narrow MVP; added agent separation would not justify its complexity. | PASS (bounded decision) |
| Reassess API Gateway/Lambda entry-path decision | ADR 005; ADR 019; Phase 8 deployment-readiness document | Separate Lambda boundaries and managed Gateway remain defensible locally; live invocation controls remain deferred. | PASS (bounded decision) |
| Reassess MCP hosting/integration decision | ADR 005; ADR 019; Phase 5 validation matrix | Gateway/MCP remains the correct direction, but deployed policy/interceptor behavior is not locally validated. | PARTIAL |
| Reassess network topology choices | `docs/architecture/phase-2-design.md`; ADR 018; Phase 6 scenarios | Two-VPC peering remains the lowest-cost appropriate MVP; TGW remains a separately authorized later variant. | PASS (bounded decision) |
| Review scalability, resilience, and operational limitations | Phase 7/8/9 architecture documents; `docs/development.md`; findings below | Fail-fast propagation, lack of retry/normalization, approval recovery uncertainty, partial route writes, and live operational gaps require continued ownership. | OPEN |
| Perform senior-architect-style design review | This recorded review and finding register below | Independent review completed and recorded; this does not close live or production gates. | PASS (review recorded) |

## 10.3 IAM and security review

| Checklist item | Local evidence / contract | Scope and result | Status |
|---|---|---|---|
| Verify least-privilege IAM | `tests/security/test_phase5_iam.py`; `tests/security/test_phase8_remediation_iam.py`; `iam/phase8/*` | Offline fixtures are narrow, but the Terraform readiness policy renders account `*` resource ARNs while the approved fixture requires `${account_id}`. | PARTIAL |
| Verify read and write roles remain separated | `tests/security/test_phase5_iam.py`; `tests/security/test_phase8_remediation_security.py` | Diagnostic READ cannot enter the WRITE workflow; separate role contracts are tested offline. | PASS (local contract) |
| Verify no unintended sensitive-action wildcards | IAM fixtures and `terraform/modules/phase8_readiness/main.tf` | No action wildcard is present, but the Terraform account wildcard broadens resource scope beyond the approved fixture. | PARTIAL |
| Verify human approval cannot be bypassed | Phase 8 workflow/trusted-identity/security tests; ADR 021 | Local binding, trusted identity, expiry, replay, and denial controls pass; live AgentCore Policy/interceptor and IAM/SigV4 ingress remain deferred. | PARTIAL |
| Verify no raw credentials/secrets are committed or logged | `.gitignore`; observability/security tests; sanitized evidence | Redaction and repository contracts were reviewed; a full current history/secret scan was not run in this bounded task. | PARTIAL |
| Verify managed secret/config references are used appropriately | Phase 8 deployment-readiness; Terraform variable guidance | Non-secret configuration is documented and caller-controlled AWS fields are rejected; live configuration remains deferred. | PARTIAL |
| Review project resources for unintended public/cross-account exposure | Architecture/IAM documentation and sanitized evidence | Requires authorized current AWS inspection. | DEFERRED |
| Run agreed IaC/security scanning | `.github/workflows/ci.yml`; `docs/development.md` | Toolchain is documented/configured, but the scans were not run in this correction pass. | OPEN |
| Document accepted findings with rationale | This matrix's senior-review finding register | Findings, dispositions, risk owners, and remaining blockers are recorded below; implementation of the open IAM correction remains outstanding. | PASS (bounded documentation) |

## 10.4 Cost review

| Checklist item | Local evidence / contract | Scope and result | Status |
|---|---|---|---|
| Review actual project-created resource usage | `PROJECT_STATUS.md`; sanitized evidence | Historical inventory/evidence exists, but current AWS state is not inspected. | DEFERRED |
| Estimate representative lab cost | ADR 015/018; README; Terraform tags/retention guidance | Cost drivers and controls are documented; no current billing or account estimate is validated. | PARTIAL |
| Identify primary cost drivers | README; ADR 018; Terraform/teardown guidance | EC2/EBS, Flow Logs, AgentCore, logs, and future TGW/VPN costs are identified qualitatively. | PARTIAL |
| Verify unnecessary persistent resources were avoided | Terraform defaults; README; Phase 8 opt-in module | Defaults avoid NAT/TGW/Flow Logs/readiness resources, but current account state is not verified. | PARTIAL |
| Verify Budget/cost alert configuration | Phase 9 checklist/status | Budget and alert configuration remain explicitly deferred. | DEFERRED |
| Document cost controls and expected operating model | README; `terraform/README.md`; ADRs 015 and 018 | Tags, stopped-compute guidance, retention, opt-in modules, teardown, and separate TGW state/window are documented. | PASS (documentation) |

## Deferred live boundary

The following remain intentionally outside this local closure-preparation scope: current AWS state and exposure, current billing/Cost Explorer data, deployed AgentCore Observability and OpenTelemetry, CloudWatch dashboards/alarms/budgets, Flow Logs delivery, live end-to-end correlation, live approved remediation, live post-remediation verification, production authenticated approval ingress, Lambda resource-policy enforcement, AgentCore Policy/interceptor enforcement, and independent teardown verification. No AWS or Terraform operation is implied by this matrix.

## Offline validation record

The bounded local checks produced these results:

| Check | Result |
|---|---|
| Full pytest suite before approval hardening (`uv run pytest`) | **260 passed** |
| Full pytest suite after approval hardening (`uv run pytest`) | **261 passed** |
| Focused Phase 10 tests | **71 passed** |
| Approval/security regression set | **40 passed** |
| Ruff lint (`uv run ruff check .`) | **Passed** |
| mypy (`uv run mypy`) | **Passed** |
| Repository documentation JSON validation | **25 files parsed successfully** |
| Changed-file Ruff formatting | **Passed** |
| Phase 8 package smoke/rebuild test | **Passed** |
| Git diff check (`git diff --check`) | **Passed** |

The full repository Ruff format check still reports six unrelated pre-existing files; those files are not part of this bounded correction. Terraform, AWS CLI, deployment, Lambda invocation, IAM mutation, EC2 lifecycle, and resource create/delete commands are excluded.

## Senior-review finding register

Every finding has a disposition and risk owner. `Corrected` means the local documentation or contract statement was reconciled in this correction pass; it does not imply live validation. `Accepted bounded deviation` means the limitation is intentionally retained for local scope. `Deferred` requires a separately authorized live or implementation task. `Open` requires a future correction or architecture decision before production-readiness claims.

| Finding | Disposition | Risk owner | Required follow-up |
|---|---|---|---|
| Terraform Phase 8 readiness IAM policy uses account `*` in EC2 resource ARNs, while `iam/phase8/remediation-write-permissions.json` and ADR 022 require exact account scope. | **CORRECTED** | IAM/security owner | All three EC2 write-resource ARN families now use validated `var.account_id`; no account-wildcard write ARN remains. Focused IAM/Terraform tests: **17 passed**; full pytest: **262 passed**; `terraform fmt -check -recursive terraform`: **passed**; local `terraform validate -no-color`: **passed**. This exact-account correction is included in the current checkpoint commit. |
| Terraform environment injects destination SG/VPC IDs, but route-table IDs and the destination NACL ID used by the immutable local manifest are not all injected into the remediation Lambda environment. | **Deferred** | Remediation/platform owner | Add or approve complete trusted binding injection, or explicitly retain source-frozen bindings with deployment evidence. Current documentation now states the gap. |
| ADR 022 described Terraform as injecting a complete immutable manifest, although the package contains the static `manifest.py` values and Terraform currently injects only a subset of trusted resource IDs. | **Corrected** | Remediation/platform owner | Documentation now distinguishes the local static manifest from the partial deployment environment bindings. |
| ADR 022 said each tool executes at most one correction, while `AwsRemediationExecutor._write()` can issue up to four route writes for one approved route-remediation operation. | **Corrected** | Architecture/remediation owner | ADR 022 now defines one approved operation with up to four bounded route writes; no generic or unbounded write is permitted. |
| `record_approval()` accepts a caller-supplied principal and remains weaker than the trusted wrapper, `ApprovalService`, and DynamoDB repository. Its boolean check is not strict, its collection type is not runtime-restricted, proposal validation is incomplete, and the local store overwrites duplicate IDs. | **Accepted bounded deviation** | IAM/security owner | Treat `record_approval()` as local/test-only. Harden or retire it before treating it as a production authorization API. |
| Package smoke tests invoke lower-level handlers rather than exported Lambda handlers; package verification does not validate every member hash, handler import, or architecture metadata. | **Accepted bounded deviation** | Build/release owner | Strengthen release verification before deployment-readiness claims; current package evidence remains local reproducibility only. |
| Runtime/Gateway/diagnostic/verifier failures propagate fail-fast without structured normalization or automatic retries. | **Accepted bounded deviation** | Runtime/resilience owner | Preserve no-retry behavior locally; design caller-facing failure and retry/recovery policy before production use. |
| Approval consumption precedes AWS writes; result persistence failure or partial route success can leave an executing approval requiring reconciliation. | **Open** | Runtime/resilience and remediation owners | Define timeout, recovery, partial-write, reconciliation, and operator-runbook behavior. |
| Semantic irrelevant-tool selection is not implemented; `FixedToolSelector` does not inspect intent or prompts. | **Open** | Agent/runtime architecture owner | Approve a selector contract and add semantic relevance/model-backed selection tests. |
| Live IAM/SigV4 approval ingress, Lambda resource policies, AgentCore Policy/interceptor enforcement, public/cross-account exposure, current inventory, billing, budgets, observability, remediation, and teardown are not locally established. | **Deferred** | IAM/platform, operations, and FinOps owners | Perform only under separately authorized live Phase 10/11 gates. |
| Final senior architecture/security review and bounded deviation record. | **Corrected** | Senior architecture reviewer | This matrix now records the independent review, dispositions, owners, and remaining blockers; it does not mark Phase 10 complete. |

## Local implementation boundary

The following implementation facts are intentionally preserved and documented rather than silently changed in this correction pass:

- `record_approval()` is a local/test helper and is not the production authorization boundary.
- `ApprovalService`, the trusted identity wrapper, and the DynamoDB repository remain the stronger production-shaped local contract.
- The static local manifest contains route-table and NACL identifiers from sanitized evidence; Terraform readiness currently injects only the configured subset of resource/VPC IDs into the Lambda environment.
- One approved route-remediation operation may perform up to four manifest-bounded route writes, followed by verification and drift reporting.
- No automatic retry or caller-facing normalization is added around writes because approval consumption and side-effect uncertainty could create duplicate or ambiguous remediation outcomes.

The matrix and finding register do not mark Phase 10 complete. The authoritative checklist remains unchanged and all Phase 10 completion items remain unchecked.
