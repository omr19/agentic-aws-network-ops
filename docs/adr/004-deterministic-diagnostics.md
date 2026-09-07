# ADR 004 — Deterministic Diagnostics

## Status
Accepted

## Decision
Use AWS configuration APIs for configuration facts, Reachability Analyzer for primary
configured-path analysis, and Flow Logs for complementary observed-traffic evidence
where justified. The LLM correlates and explains the evidence.

## Consequences
The agent cannot assert an unsupported root cause. Missing permissions or incomplete
evidence are reported as limitations rather than network failures.
