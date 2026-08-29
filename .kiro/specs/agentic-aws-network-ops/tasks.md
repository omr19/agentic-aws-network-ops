# Kiro Spec Tasks — Agentic AWS Network Operations

## Rules

Execute only in `PROJECT_CHECKLIST.md` phase order. Checked means implemented and
validated. Apply/deploy, IAM changes, destructive actions, commit, and push require
applicable explicit authorization; prerequisites do not authorize them.

## Phase 3 — Spec and foundation

- [x] **P3-01** Validate requirement → design → task/test traceability. **Req:** all.
  **Verify:** automated ID/reference check and independent Kiro review.
- [x] **P3-02** Establish approved Terraform, Python, contract, fixture, test, script,
  and docs directories. **Req:** TST-001–002, ENG-001–002. **Verify:** tree and smoke checks.
- [x] **P3-03** Pin compatible Python and configure ADR 023's Python, schema, security,
  and pre-commit tools. **Req:** TST-001–002, ENG-001–002. **Verify:** local checks run.
- [x] **P3-04** Create Terraform root, local backend convention, module interfaces,
  lab environment, tags, and placeholder-only tfvars example. **Req:** NET-001–005,
  ENG-001, CST-001–002. **Verify:** fmt and static review.
- [x] **P3-05** Initialize/validate Terraform, track its lock file, and exclude state.
  **Req:** ENG-001, SEC-007. **Verify:** init/validate and Git ignore review.
- [x] **P3-06** Configure TFLint, Checkov, and non-destructive CI without broad AWS
  credentials. **Req:** ENG-001–002, SEC-007. **Verify:** local equivalents and review.
- [x] **P3-07** Review foundation diff and commit only after authorization. **Req:**
  ENG-001–002, SEC-007. **Verify:** diff, secret scan, and checklist evidence.

## Phase 4 — Healthy network lab

- [ ] **P4-01** Implement Source/Destination VPC modules and approved private layout.
  **Req:** NET-001, NET-003, CST-001. **Verify:** static tests and reviewed plan.
- [ ] **P4-02** Implement peering, routes, SGs, NACLs, and TCP/443 workloads. **Req:**
  NET-002–005. **Verify:** plan has no public/NAT/endpoint resources.
- [ ] **P4-03** After apply authorization, deploy and validate healthy connectivity and
  Reachability Analyzer. **Req:** NET-002, DIA-001. **Verify:** evidence and inventory.

## Phase 5 — AgentCore and READ diagnostics

- [ ] **P5-01** Define/test the common envelope and nine diagnostic schemas. **Req:**
  DIA-002–004, TST-002. **Verify:** positive/negative schema tests.
- [ ] **P5-02** Implement shared READ logic and thin Lambda adapter. **Req:** DIA-001–004,
  AGT-002, TST-001–002. **Verify:** Stubber tests without live calls.
- [ ] **P5-03** Implement separated Runtime/Gateway/diagnostic IAM and prove diagnostic
  zero-write capability. **Req:** SEC-001, SEC-007. **Verify:** policy/denial tests.
- [ ] **P5-04** Implement single Runtime, Gateway READ integration, IAM/SigV4 client, and
  local agent path. **Req:** SYS-001–002, AGT-001–003. **Verify:** local then authorized integration tests.

## Phase 6 — Controlled failures

- [ ] **P6-01** Implement repeatable SG, route, and NACL failure/reset fixtures. **Req:**
  NET-004, REM-001–003. **Verify:** reviewed plans/state transitions.
- [ ] **P6-02** Validate healthy and three-failure diagnosis with deterministic evidence.
  **Req:** SYS-002, DIA-001–005, TST-002. **Verify:** scenario/root-cause evidence.

## Phase 7 — Intelligent Deterministic Diagnosis

- [ ] **P7-01** Define and document the diagnostic workflow for the healthy baseline and
  each failure class, including applicable AWS configuration APIs, Reachability
  Analyzer, Flow Logs, CloudWatch evidence, evidence correlation, limitations, and
  ambiguous cases. **Req:** SYS-002, DIA-001, DIA-003, DIA-004, DIA-005.
  **Verify:** workflow-to-scenario and evidence-source review.
- [ ] **P7-02** Test healthy infrastructure for false positives and repeat every
  representative failure scenario to assess root-cause accuracy and consistency.
  Require outputs to separate observed evidence from recommendation and reject
  unsupported claims. **Req:** SYS-002, DIA-001, DIA-003, DIA-004, TST-002.
  **Verify:** repeated-run matrix with expected roots, limitations, and consistency results.

## Phase 8 — Approval and remediation

- [ ] **P8-01** Define/test canonical hash encoding and golden vectors. **Req:** SEC-003,
  TST-002. **Verify:** cross-component tamper tests.
- [ ] **P8-02** Implement approval/table, policy, interceptor, atomic consumption,
  expiry, replay protection, and idempotency. **Req:** SEC-002–006. **Verify:** adversarial tests.
- [ ] **P8-03** Implement immutable manifest and exactly three WRITE tools; verify EC2
  condition-key support. **Req:** REM-001–003, SEC-001. **Verify:** IAM/schema/code tests.
- [ ] **P8-04** Implement preflight, restoration, verification, audit, and drift warning.
  **Req:** REM-004–005, SYS-003. **Verify:** success/partial/idempotency/failure tests.
- [ ] **P8-05** Promote policy to `ENFORCE` only after test review. **Req:** SEC-004–006.
  **Verify:** recorded gate evidence.

## Phase 9 — Observability and cost

- [ ] **P9-01** Implement sanitized end-to-end correlated telemetry. **Req:** SYS-003,
  OBS-001–002, SEC-007. **Verify:** trace a representative session.
- [ ] **P9-02** Configure controlled Flow Logs, retention, dashboard, alarms, SNS, and
  budget alert. **Req:** DIA-005, OBS-002, CST-002. **Verify:** safe alert test.

## Phase 10 — Full validation and reviews

- [ ] **P10-01** Run healthy/failure/diagnosis/approval/denial/remediation/verification
  matrix. **Req:** SYS-001–003, NET-004, DIA-001–005, SEC-001–007, REM-001–005, TST-002.
  **Verify:** published evidence matrix.
- [ ] **P10-02** Review architecture, IAM, Checkov, cost, resilience, and deviations.
  **Req:** ENG-001–002, CST-001–002. **Verify:** documented senior review.

## Phase 11 — Destroy and verify cost

- [ ] **P11-01** After authorization, destroy and independently verify resources,
  approval table, logs, and billable services are removed or documented. **Req:**
  CST-002, LIF-001. **Verify:** post-destroy inventory/cost record.

## Phase 12 — Documentation and diagrams

- [ ] **P12-01** Finalize reproducible runbooks and five diagrams against reality.
  **Req:** LIF-001, SYS-003, SEC-001–007. **Verify:** link/render/content review.
- [ ] **P12-02** Document portfolio evidence, security, cost, limitations, TGW evolution,
  and sanitized screenshots. **Req:** NET-005, CST-001–002, LIF-001. **Verify:** privacy review.

## Phase 13 — Portfolio readiness

- [ ] **P13-01** Perform final code/test/security/cost/docs/Git/Kiro review and verify
  authoritative gates plus GitHub portfolio audit, resume bullets, and LinkedIn project
  summary before publication. **Req:** all. **Verify:** reproducible report, sanitized
  portfolio artifacts, and explicit user approval.

## Requirement coverage index

This explicit index makes compact task ranges mechanically traceable:

| Requirement IDs | Verification tasks |
|---|---|
| SYS-001, SYS-002, SYS-003 | P5-04, P7-01, P7-02, P8-04, P9-01, P10-01 |
| NET-001, NET-002, NET-003, NET-004, NET-005 | P4-01, P4-02, P4-03, P6-01, P6-02, P11-01 |
| DIA-001, DIA-002, DIA-003, DIA-004, DIA-005 | P5-01, P5-02, P6-02, P7-01, P7-02, P9-02, P10-01 |
| AGT-001, AGT-002, AGT-003 | P5-02, P5-04, P10-02 |
| SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007 | P5-03, P8-01, P8-02, P8-03, P8-05, P10-02 |
| REM-001, REM-002, REM-003, REM-004, REM-005 | P6-01, P8-03, P8-04, P10-01 |
| OBS-001, OBS-002 | P9-01, P9-02, P10-01 |
| TST-001, TST-002 | P3-02, P3-03, P5-01, P5-02, P7-01, P7-02, P10-01 |
| ENG-001, ENG-002 | P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P10-02 |
| CST-001, CST-002 | P3-04, P4-01, P4-03, P9-02, P11-01 |
| LIF-001 | P11-01, P12-01, P12-02, P13-01 |
