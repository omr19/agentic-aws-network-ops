# Phase 7 Deterministic Diagnosis Foundation

This local-only foundation correlates normalized READ evidence; it does not call AWS, Terraform, IAM, deployment, or remediation/write tooling. The workflow is implemented in `src/agentic_aws_network_ops/diagnostics/deterministic.py` and deliberately does not duplicate the Phase 6 scenario model.

## Workflow

1. Accept a normalized evidence object using `schemas/diagnostic/normalized-evidence.schema.json`.
2. Validate the common correlation, region, timestamp, completeness, Reachability Analyzer, and optional observability fields.
3. Preserve Reachability Analyzer, configuration/API, Flow Logs, and CloudWatch observations as facts.
4. Correlate a completed reachability result with configuration and optional observability facts using a closed set of deterministic signatures.
5. Reject unsupported observability shapes, evidence older than 15 minutes, and explicit signal conflicts.
6. Return a diagnosis result using the existing result-envelope shape, with diagnosis data separated into `observed_facts`, stable machine-readable `root_cause`, and advisory `recommendations`.
7. Return no-finding/healthy when a completed Reachability Analyzer result finds a path and no blocker is observed.

The result contract is defined in `schemas/diagnostic/diagnosis-result.schema.json`. Recommendations are descriptive only; this module has no AWS client, Terraform, IAM, or write-tool dependency.

## Live observability validation limitation

A temporary validation run was authorized locally and in AWS operational scope to start both tagged Phase 4 EC2 instances, but both were restored to `stopped` before the validation ended. No Flow Logs were created. No test traffic was generated. The current least-privilege role denied `ssm:DescribeInstanceInformation`, `cloudwatch:GetMetricData`, and `logs:DescribeLogGroups`; consequently, no live Flow Logs or CloudWatch evidence was collected. The existing diagnostic and Runtime IAM roles must not be broadened for this optional validation. A separate temporary read-only observability role is a future enhancement. Sanitized evidence is recorded in `docs/evidence/phase-7/observability-validation-limitation.json`.


## Temporary Flow Logs validation attempt

A bounded live-delivery attempt created one tagged one-day log group, one temporary provisioning role, one temporary Flow Logs delivery role, and two tagged VPC Flow Logs for the source and destination project VPCs. The two tagged EC2 instances were started and restored to `stopped`. `ssm:SendCommand` was denied, so no TCP/443 probe ran and no live Flow Log record was delivered or queried. Cleanup succeeded: both Flow Logs, the log group, and both temporary IAM roles were deleted; no unrelated resources were created or changed. Sanitized evidence is recorded in `docs/evidence/phase-7/flowlogs-validation.json`. CloudWatch EC2 metrics are complete. Live Flow Logs/CloudWatch Logs traffic evidence remains a documented limitation; no live Flow Log record or Logs Insights query was obtained.


The confirmed SSM-readiness check found that both tagged project EC2 instances have no IAM instance profile. They are therefore not SSM-managed or ready for `ssm:SendCommand`. The earlier Flow Logs attempt could not generate traffic because `ssm:SendCommand` was denied and the instances lacked instance-side SSM authorization. No instance profile, SSM endpoint, or additional IAM permission was added. Both instances remain stopped; the temporary Flow Logs, log group, and IAM roles were cleaned up. CloudWatch metrics remain complete. Live Flow Logs/CloudWatch Logs traffic evidence remains a documented limitation; no live Flow Log record or Logs Insights query was obtained.

## Future observability-role foundation

`iam/phase7/observability-read-permissions.json` is a local, unattached policy fixture for a future demo role. It is intentionally separate from the Runtime and diagnostic identities and allows only project-instance observation (`ec2:DescribeInstances`, `ec2:DescribeTags`), Flow Logs discovery, CloudWatch Logs discovery/query/results, and CloudWatch metric reads. Logs-group discovery uses `Resource: "*"` with only the approved region condition because `logs:DescribeLogGroups` does not support the log-group condition in this API call; `logs:StartQuery` remains scoped to the project log-group ARN and `logs:GetQueryResults` remains read-only. The policy contains no route, security-group, NACL, peering, IAM, Lambda invocation, PassRole, lifecycle, or remediation authority. Actual role creation, attachment, policy simulation, and use require a separate IAM approval gate; this foundation does not broaden existing roles.


`flow_logs` and `cloudwatch` are optional top-level normalized inputs. Their absence adds a limitation and does not change a healthy or supported diagnosis into a failure. A supplied source must use the closed schema, carry an observation timestamp no more than 15 minutes older than the diagnosis, and use a supported signal. Flow Logs use `path_outcome` (`accepted`, `rejected`, or `unknown`); CloudWatch uses `network_error` (`true` or `false`). Signals that contradict Reachability Analyzer are rejected as `CONFLICTING_EVIDENCE`; stale signals are rejected as `STALE_OBSERVABILITY_EVIDENCE`. No AWS query or log/metric retrieval occurs in this module.


| Classification | Required deterministic evidence | Stable root-cause identifier | Human-readable explanation |
|---|---|---|---|
| `security_group_mismatch` | Unreachable result plus observed SG source CIDR differs from the approved expected CIDR | `destination_security_group_ingress_does_not_match_source` | Destination SG ingress does not match the approved source |
| `missing_route` | Unreachable result plus source-to-destination route absent and return route present | `missing_source_to_destination_peering_route` | A required peering route is missing |
| `nacl_restriction` | Unreachable result plus observed destination TCP/443 deny rule | `destination_nacl_denies_tcp_443_ingress` | Destination NACL denies the tested traffic |
| `peering_path_dns_failure` | Unreachable result plus both peering route directions absent and both DNS options false | `peering_path_disabled_both_route_directions_and_dns` | The peering path is disabled by routes and DNS options |

The local DNS fixture remains a Phase 6 concern and is not silently inferred as an AWS DNS failure by this workflow. It can be represented as a future normalized evidence extension only when its local-only provenance is explicit.

## Healthy, incomplete, and conflicting evidence

Healthy evidence is `status=succeeded`, `path_found=true`, and no contradictory blocker. It returns `status=no_finding`, classification `healthy`, a null root cause, observed facts, and no recommendation.

Pending, failed, partial, or missing configuration evidence returns `status=no_finding` with classification `indeterminate`, an `INCOMPLETE_EVIDENCE` error, and no root-cause claim. A completed healthy reachability result combined with a blocking configuration fact returns `invalid_request` with `CONFLICTING_EVIDENCE`. Multiple independent blockers also return `invalid_request`; the workflow never silently chooses one.

## Evidence and recommendation boundary

`observed_facts` are direct normalized observations, such as `path_found=false`, a route absence, an NACL rule number, or DNS options. `recommendations` are bounded advisory text, such as restoring the approved route or SG CIDR. Recommendations are not evidence and are never executable actions.

## Tests and limitations

`tests/unit/test_deterministic_diagnosis.py` covers healthy no-finding, all four implemented AWS failure classes, tracked Phase 6 SG/route/NACL/peering fixtures, optional Flow Logs and CloudWatch correlation, missing observability limitations, stale/conflicting/unsupported observability evidence, incomplete evidence, conflicting evidence, unsupported claims, and repeatability. Schema tests cover closed-world normalized input.

Limitations:

- The workflow diagnoses only the four implemented AWS failure classes; it does not query AWS or infer facts absent from normalized input.
- Reachability Analyzer is correlated but not treated as sufficient by itself for a root-cause claim when configuration evidence is incomplete.
- Multiple blockers are reported as conflicting rather than ranked.
- Flow Logs are currently disabled and CloudWatch metrics/log evidence is not yet used in diagnosis; both remain optional integrations, with live delivery explicitly limited by the documented instance SSM-readiness boundary rather than treated as N/A.
- Optional observability evidence is local normalized input only; this foundation does not enable Flow Logs or query CloudWatch.
- A future adapter may expose this as a read-only contract, but adding it to the MCP/Gateway allowlist is outside this local foundation task.
