# ADR 014 — AgentCore Memory

## Status
Accepted

## Decision
Use session-scoped operational context for the MVP. Persistent AgentCore Memory is an
optional advanced capability for incident history or recurring-pattern context.

## Consequences
Memory stores neither credentials nor reusable approval. Memory may inform reasoning;
it never grants authority.
