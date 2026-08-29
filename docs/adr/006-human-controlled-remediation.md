# ADR 006 — Human-Controlled Remediation

## Status
Accepted

## Decision
Separate READ diagnosis from WRITE remediation. The agent proposes a structured change;
an authorized human approves or denies it; a separately authorized narrow WRITE tool
executes it; READ diagnostics verify the result.

## Consequences
A natural-language “Yes” grants no AWS permission. Denial produces zero writes, and no
generic arbitrary AWS change tool is permitted. ADR 021 defines the explicit human
approval, request binding, expiration, consumption, and replay controls.
