# Docket Documentation

| Doc | What it covers |
|---|---|
| [`examples.md`](./examples.md) | Ready-to-run mock JSON payloads for all 5 shipped document types — copy, curl, get a document back. Start here if you just want to try the API. |
| [`architecture.md`](./architecture.md) | The system as it exists today: module layout, component diagram, request-flow sequence diagrams, extension points, and an explicit list of what this POC deliberately does not do. |
| [`design-decisions.md`](./design-decisions.md) | Why the codebase looks the way it does — ADR-style entries for every non-obvious choice (modular monolith over layered Clean Architecture, docxtpl, headless LibreOffice, no ports/Protocol layer, no DB, no auth, etc.), including the trade-offs accepted and when to revisit them. |
| [`production-readiness.md`](./production-readiness.md) | How to turn this into a real, deployable system: local disk → S3, no DB → PostgreSQL, synchronous generation → job queue + workers, no auth → API keys/OAuth2, plus observability, security hardening, and a suggested migration order. |

Start with `examples.md` to generate your first document,
`architecture.md` for how it works, `design-decisions.md` for why it
works that way, and `production-readiness.md` for what changes before
this runs anywhere beyond a laptop.

See also the root [`README.md`](../README.md) for setup/run/test
instructions.
