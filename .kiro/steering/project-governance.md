# Project Governance — Agentic AWS Network Operations

This repository uses explicit governance files as the authoritative source of truth.

## Authoritative Files

Before performing any project work, read these files from disk:

1. `PROJECT_CHECKLIST.md`
2. `PROJECT_STATUS.md`

These files override conversational memory, prior chat context, inferred scope, or reconstructed plans.

## Phase Control

- Do not merge, split, rename, renumber, reorder, add, or remove project phases without explicit user authorization.
- Do not infer that a task or phase is complete.
- Only mark completion after the task has been implemented and validated.
- Work only on the currently authorized phase/task.
- Do not begin future-phase implementation because it appears technically convenient.

## Change Discipline

- Prefer minimal diffs.
- Do not rewrite an entire governance document to make a small change.
- Do not reconstruct `PROJECT_CHECKLIST.md` or `PROJECT_STATUS.md` from chat history.
- If a governance file appears inconsistent, stop and report the inconsistency instead of silently correcting it.
- If you disagree with an architectural decision, flag the concern with rationale; do not silently redesign the project.

## AWS Change Control

Do not perform AWS-changing actions unless explicitly authorized for the current task.

This includes:

- AWS CLI commands that create, update, or delete resources
- Terraform apply/destroy
- AgentCore deployment
- Lambda deployment
- API Gateway deployment
- IAM changes
- Network changes
- Resource provisioning or deletion

Read-only inspection commands may be proposed when appropriate, but explain their purpose first.

## Architecture Principles

Preserve these baseline principles unless explicitly changed through architecture review:

- Amazon Bedrock AgentCore is the primary agent runtime/platform direction.
- MCP is a first-class tool integration layer.
- AgentCore Gateway is the preferred managed gateway path where appropriate.
- Diagnostic READ tools and remediation WRITE tools remain separated.
- AI reasoning does not equal authorization.
- Human approval is required before remediation.
- Deterministic AWS evidence establishes network facts.
- The LLM correlates, explains, and recommends based on evidence rather than guessing reachability.
- VPC Reachability Analyzer is a key deterministic diagnostic capability.
- Costly persistent AWS services are not defaults and must be justified.
- Observability must trace observable execution data without claiming access to hidden chain-of-thought.

## Review Role

Kiro is encouraged to act as an independent technical reviewer.

When reviewing architecture or implementation:

- Identify concrete risks, missing dependencies, AWS limitations, security issues, IAM concerns, cost concerns, test gaps, or implementation conflicts.
- Reference the relevant repository requirement or file section when possible.
- Challenge assumptions when technically justified.
- Do not change approved architecture automatically.
- Present proposed corrections for user/architect review first.

## Session Start

At the beginning of a project task:

1. Read `PROJECT_CHECKLIST.md`.
2. Read `PROJECT_STATUS.md`.
3. Identify the current phase.
4. Identify the exact authorized task.
5. State any prerequisite or blocker before implementation.

## Session End

Before concluding meaningful project work, report:

- What was completed
- What was validated/tested
- AWS resources created/changed/still active
- Cost/usage implications
- Cleanup status
- Decisions made
- Blockers
- Exact next step

Do not update governance status beyond what was actually completed and validated.