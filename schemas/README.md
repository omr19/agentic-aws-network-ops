# MCP Schemas

Version-controlled JSON Schemas define the shared diagnostic result envelope and the
nine approved diagnostic READ contracts. Inputs are closed to unknown properties and
constrain regions, identifiers, time windows, metrics, and query sizes. The envelope
distinguishes success, no finding, unreachable, authorization denial, API error,
timeout, and invalid request while recording evidence completeness and limitations.

Remediation WRITE contracts are intentionally deferred to Phase 8. No generic AWS or
shell execution contract belongs here.
