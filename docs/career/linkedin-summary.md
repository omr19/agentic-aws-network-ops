# LinkedIn Project Summary

## Short version

Built a governed agentic AWS network-operations platform that helps an operator observe
private VPC connectivity, diagnose failures with deterministic AWS evidence, propose a
bounded remediation, require human approval, and verify the result. The project combines
Terraform, Amazon Bedrock AgentCore, MCP contracts, least-privilege IAM, Reachability
Analyzer, CloudWatch evidence, security testing, and reproducible teardown controls.

This is a private portfolio project with bounded validation. It demonstrates explainable,
human-controlled operations—not unrestricted autonomous production access.

## Suggested post

Network incidents rarely have one source of truth. Routes, security groups, NACLs,
Reachability Analyzer, and telemetry must be correlated before anyone changes production.

I built a governed agentic AWS network-operations lab to demonstrate that workflow:

**Observe → Diagnose → Propose → Human approve/reject → Enforce policy/IAM → Remediate → Verify**

The implementation uses Terraform, strict MCP READ contracts, deterministic evidence,
separate WRITE boundaries, approval binding/replay protection, reversible failure scenarios,
and sanitized evidence. The repository remains private and the documented scope distinguishes
validated local/historical behavior from deferred production capabilities.
