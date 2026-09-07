# ADR 009 — Terraform Ownership and Runtime Drift

## Status
Accepted

## Decision
Terraform remains the authoritative definition. Approved runtime remediation may
correct AWS but must identify resulting drift and require explicit IaC reconciliation.

## Consequences
Do not conceal drift with broad `ignore_changes`, and do not let the agent silently
rewrite Terraform. After changing a Terraform-managed resource, remediation must
return an explicit drift warning identifying the affected resource and require source
reconciliation before a later apply. Automated PR reconciliation is an advanced option.
