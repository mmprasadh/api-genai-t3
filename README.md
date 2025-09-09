# GenAI API Lifecycle — v5.4.3 (Full‑fat, org‑tuned, hardened)

This package implements two use cases via **MCP (required)**:
1) **Generate OpenAPI** spec from prompt/context
2) **Generate user‑friendly docs** from that spec (Markdown + HTML)

What’s included
- Azure Functions: `GenerateOpenApi`, `GenerateDocsFromOpenApi`
- Robust provisioning & deployment scripts (RBAC‑aware Key Vault, Run‑From‑Package fallback)
- MCP orchestrator server (mandatory) with tools (generate/import/docs/mocks)
- Azure DevOps pipeline: Spectral → **42Crunch** → **Auto‑Fix** → Re‑check → Import → API Center → Docs (Blob + SAS)
- **Org rules**: Spectral rules (`.spectral.yaml` + `spectral-rules/index.js`) & stricter 42Crunch CI gate (`security/42c-conf.yaml`)
- Utilities: env persistence, health checks, AOAI deployment helper

See **RUNBOOK.md** for step‑by‑step execution.
