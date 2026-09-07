# Phase 5 Local READ Flow

This document describes the deployment-agnostic P5-04 foundation. It exercises the
approved READ path without contacting AWS:

`RuntimeRequest → Runtime selector → GatewayReadRequest → local Gateway adapter → diagnostic Lambda adapter → DiagnosticService → GatewayReadResponse → RuntimeResponse`

- `Runtime` carries the prompt, correlation ID, session ID, and Region and accepts an
  injected selector. The local selector is deterministic; no model, approval, or WRITE
  path is implemented here.
- `LocalGatewayAdapter` accepts only the nine approved diagnostic tool names and invokes
  an injected diagnostic target with the existing Lambda event shape. Unknown or
  malformed requests are rejected before the target is called.
- `LocalDiagnosticLambdaTarget` reuses the framework-independent diagnostic service
  through an injected dispatch seam. It does not construct Boto3 clients.
- `NativeAgentClient` accepts non-secret `SigV4Config` metadata and an injected transport.
  The placeholder endpoint/path and transport make the IAM/SigV4 boundary explicit while
  keeping signing, credential resolution, sockets, and AgentCore deployment out of this
  task.
- Diagnostic result envelopes are carried back unchanged. Observed evidence remains
  separate from interpretation, and no approval or remediation boundary is reachable.

The future deployment boundary replaces the injected selector/transport and local
Gateway target with AgentCore Runtime, AgentCore Gateway, IAM/SigV4 authorization, and
the separately deployed diagnostic Lambda. The Phase 5 IAM contracts remain independent
of this local composition and are not modified or attached by these tests. Authorized
integration testing is required before claiming deployed AgentCore/Gateway readiness.
