# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/) — this project
hasn't cut versioned releases yet (POC stage, no git history), so
everything to date is grouped under **Unreleased**.

## [Unreleased]

### Added
- Document generation service (FastAPI): renders DOCX/PDF from
  versioned templates and dynamic JSON data, for 5 sample document
  types (`invoice`, `quote`, `purchase_order`, `contract`, `memo`).
- Convention-based template discovery — drop a `{type}_v{N}.docx` (or
  `.doc`) file into `templates/` and it's live, no code changes.
- Legacy `.doc` template support: transparently converted to `.docx`
  via LibreOffice before the same Jinja2/docxtpl rendering path used
  for native `.docx` templates.
- RESTful API: `POST/GET /documents`, `GET/DELETE /documents/{id}`,
  `GET /documents/{id}/content`, `GET /document-types` — documents are
  addressable by id with no database, via metadata encoded in the
  generated filename.
- Unified error envelope (`{"error": {"code", "message", "request_id", "fields"?}}`)
  across domain errors, request validation failures, and generic HTTP
  errors, plus `X-Request-Id` correlation on every response.
- Docker + Docker Compose support, with LibreOffice baked into the
  image so PDF conversion works with a single `docker compose up`.
- Full documentation set under `docs/`: architecture, ADR-style design
  decisions, a production-readiness migration guide (local disk → S3,
  no DB → Postgres, sync → job queue, etc.), and ready-to-run sample
  requests (`docs/examples/`).
- `scripts/try_document.sh` — one-command smoke test for any shipped
  document type/format.
- Test suite (36 tests) covering template resolution, service
  orchestration, REST endpoints, and the docx zip-dedup fix (below).

### Changed
- Refactored from a layered Clean Architecture (`api/`, `domain/`,
  `services/`, `infrastructure/` at the top level) to a modular
  monolith (`app/modules/documents/`) — one capability, one folder.
- Redesigned the API from RPC-style actions (`POST /documents/generate`,
  `GET /documents/download/{filename}`) to a REST resource model.
- Redesigned the response contract: dropped a leaked server-internal
  `file_path` in favor of `filename` + an absolute, directly-callable
  `content_url`; wrapped list endpoints in `{items, count}`.
- Renamed the project from **DocFlow** to **Docket** — env var prefix
  (`DOCFLOW_` → `DOCKET_`), logger name, internal identifiers, and all
  documentation.

### Fixed
- A duplicate `docProps/core.xml` zip entry — written by `python-docx`
  when re-saving a document that originated from a LibreOffice-exported
  `.docx` — that broke PDF conversion for `.doc`-sourced documents with
  `"source file could not be loaded"`. Fixed by de-duplicating zip
  entries immediately after rendering (no-op for native `.docx`
  templates, which never trigger it).
- A stray corrupted character in `invoice_v1.docx`, introduced by an
  earlier template regeneration, caught and fixed by regenerating from
  the canonical script.
- Removed dead code left over from initial scaffolding (an empty,
  unreferenced `tests/fixtures/` directory).
