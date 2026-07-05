# Design Decisions

Lightweight ADRs (Architecture Decision Records) for the choices made in
this codebase. Each entry: **Context** (the problem), **Decision**,
**Consequences** (what you get and what you give up). Status is `Accepted`
for all unless noted otherwise — this is a POC, so several of these are
explicitly `Accepted for POC, revisit for production` and are cross-linked
to [`production-readiness.md`](./production-readiness.md).

---

## ADR-001: Modular monolith over layered Clean Architecture

**Context**: The first pass at this service used strict layered Clean
Architecture — `api/`, `domain/` (with Protocol-based ports),
`services/`, `infrastructure/`, `schemas/`, `utils/` — spread across the
top level of `app/`, for a single business capability (document
generation).

**Decision**: Restructure into a modular monolith: one
`app/modules/documents/` package containing everything about that
capability (router, schemas, service, adapters), plus a thin
`app/core/` for genuinely cross-cutting concerns (config, error base
class).

**Consequences**:
- (+) One capability = one folder. To understand or change document
  generation, there is one place to look, not six.
- (+) Removes duplication that the layered version had: a
  `DocumentGenerationRequest` domain dataclass that mirrored
  `DocumentGenerateRequest` (the API DTO) field-for-field; five separate
  `lru_cache` DI factory functions; a `Protocol`-based ports layer with
  exactly one implementation per port.
- (+) Adding a second capability later (e.g. `notifications`) is
  additive: a new `app/modules/notifications/` package, one
  `include_router()` line in `main.py`. Nothing in `documents/` changes.
- (−) If this capability grows multiple genuinely-swappable
  implementations per adapter (e.g. three different storage backends
  selectable at runtime), the lack of a formal `Protocol` layer means
  that flexibility has to be re-introduced deliberately (see ADR-006)
  rather than already being in place.
- (−) A team scaling to many engineers/many capabilities will eventually
  want per-module ownership boundaries enforced by tooling (import-linter,
  separate packages) — this is not set up yet, only the folder convention.

---

## ADR-002: Convention-based template discovery, not a registry

**Context**: Document types (`invoice`, `quote`, `purchase_order`,
`contract`, and any future type) need to map to a specific `.docx` file
and version.

**Decision**: `FilesystemTemplateRepository` scans `templates/` for files
matching `{document_type}_v{N}.docx` and resolves the highest version by
default. No enum, no config file, no database table lists the supported
types.

**Consequences**:
- (+) Adding a document type is a file-drop, zero code change — directly
  satisfies the "new types without touching core logic" requirement.
- (+) `GET /documents/types` is always accurate — it reflects the
  filesystem, so it cannot drift out of sync with a hardcoded list.
- (−) There's no validation step before a template is "live" — a
  malformed `.docx` is discovered only when the first request tries to
  render it (surfaces as a `422 TemplateRenderError`, not caught earlier).
  Production version: see "Template management" in
  `production-readiness.md`.
- (−) No metadata beyond type/version/path — no author, description,
  required-fields schema, or changelog per template. Fine for a POC with
  4 known types; not fine once non-engineers manage templates.

---

## ADR-003: docxtpl (Jinja2-in-DOCX) for rendering

**Context**: Need to inject structured JSON into a `.docx` and get a
`.docx` back, including repeating table rows (line items).

**Decision**: Use `docxtpl`, which lets a `.docx` authored in Word
contain Jinja2 syntax (`{{ field }}`, `{%tr for/endfor %}` for row loops)
and renders it by templating the underlying XML.

**Alternatives considered**:
- Raw `python-docx` manipulation (build the document from scratch in
  code): rejected — moves document layout into Python code, so every
  layout tweak requires a deploy; business users can't touch it.
- MS Word COM automation: rejected — requires a Windows host with Word
  installed, a non-starter for a Linux container deployment.

**Consequences**:
- (+) Templates are authored and maintained in Word by non-engineers.
- (+) Supports the full range of things a real invoice/contract template
  needs: conditionals, loops, rich text.
- (−) The row-loop syntax has a real, non-obvious constraint: `{%tr for %}`
  and `{%tr endfor %}` must each occupy their own dedicated table row
  (not share a row with the data), or docxtpl silently drops the
  `endfor` tag and rendering fails with a confusing `unknown tag 'endfor'`
  error. This is documented inline in
  `scripts/create_sample_templates.py` because it isn't obvious from
  docxtpl's own docs.

---

## ADR-004: Headless LibreOffice (subprocess) for PDF conversion

**Context**: `output_format: "pdf"` needs a DOCX → PDF conversion step.

**Decision**: Shell out to `soffice --headless --convert-to pdf`, with a
fresh `-env:UserInstallation` profile directory per invocation.

**Alternatives considered**:
- Paid conversion APIs (CloudConvert, Aspose Cloud, Adobe API): rejected
  for the POC to avoid an external network dependency and API cost, but
  the strongest production candidate — see `production-readiness.md`.
- `docx2pdf` (wraps MS Word via COM): rejected, same Windows/Word
  dependency problem as ADR-003.

**Consequences**:
- (+) No paid dependency, no additional network hop, works entirely
  offline.
- (+) Faithful rendering (LibreOffice's DOCX support is close to Word's).
- (−) `soffice` startup is slow (~1-2s cold) and each call spawns a new
  process — fine for a POC's request volume, a real bottleneck under
  concurrent load. This is the single biggest reason a queue exists in
  the production plan (see "Async processing" in
  `production-readiness.md`).
- (−) Per-invocation profile directories avoid *lock contention* between
  concurrent conversions, but each `soffice` process still costs real
  CPU/memory — running many in parallel on one host will contend for
  resources regardless.
- (−) If `soffice` isn't installed, PDF requests fail loudly and
  immediately (`503 ConversionUnavailableError`) rather than degrading
  silently to DOCX — a deliberate choice: the caller asked for a PDF and
  got a DOCX instead is a worse failure mode than an explicit error.

---

## ADR-005: No Protocol/ports layer — concrete adapters injected directly

**Context**: The original layered version defined `TemplateRepositoryPort`,
`DocumentRendererPort`, `PdfConverterPort`, `FileStoragePort` as
`typing.Protocol` classes that `DocumentGenerationService` depended on,
with exactly one concrete implementation each.

**Decision**: `DocumentGenerationService.__init__` takes the concrete
classes (`FilesystemTemplateRepository`, `DocxtplRenderer`,
`LibreOfficeConverter`, `LocalFileStorage`) directly. No `Protocol`
declarations.

**Consequences**:
- (+) One less file, one less indirection to trace through when reading
  the code. Python doesn't enforce the constructor's type hints at
  runtime anyway, so tests can (and do) pass in duck-typed fakes
  (`_UnavailablePdfConverter` in `tests/conftest.py`) without needing a
  `Protocol` to formally satisfy.
- (+) Matches the actual current need: exactly one implementation per
  adapter, today.
- (−) This is a real trade-off, not a free simplification: the moment a
  second implementation of any adapter needs to be selected at *runtime*
  (e.g. S3 in production, local disk in dev, chosen via config) rather
  than by editing `get_document_service()`, a `Protocol` earns its keep
  again. Re-introducing it at that point is cheap (add the `Protocol`,
  change the type hints, nothing else moves) — deferring it was a
  deliberate YAGNI call, not an oversight.

---

## ADR-006: One Pydantic schema, reused as service input — no separate domain model

**Context**: The layered version had `DocumentGenerateRequest` (the API
DTO) and `DocumentGenerationRequest` (an internal frozen dataclass) as
two types with identical fields, converted into each other in the router.

**Decision**: `DocumentGenerateRequest` (Pydantic, defined in `schemas.py`)
is passed directly into `DocumentGenerationService.generate()`. No
parallel dataclass.

**Consequences**:
- (+) Removes a mapping step that added no behavior — the two shapes
  never diverged and had no reason to.
- (−) `service.py` now has a (mild) dependency on Pydantic/the wire
  format. Acceptable inside one module owned by one team; would be worth
  splitting again if `documents/` service logic needed to be called from
  a second entry point (e.g. a CLI or a queue consumer) with a
  meaningfully different input shape.

---

## ADR-007: Synchronous, in-request document generation — no queue

**Context**: Document generation (especially with PDF conversion) is not
instantaneous.

**Decision (Accepted for POC, revisit for production)**: `POST
/documents/generate` does the full pipeline inline and returns the
result in the same HTTP response. No job queue, no polling endpoint, no
webhook.

**Consequences**:
- (+) Simplest possible API to integrate against — one request, one
  response, nothing to poll.
- (+) No queue infrastructure (Redis/SQS/RabbitMQ) needed for the POC.
- (−) Request latency is the sum of every step, including LibreOffice
  startup for PDF requests (~1-2s+). Under concurrent load, the API
  process itself becomes the bottleneck (see ADR-004).
- (−) No retry semantics if conversion fails transiently — the caller
  has to retry the whole request.
- This is the single highest-priority item in the production roadmap:
  see "Async processing" in `production-readiness.md`.

---

## ADR-008: Local filesystem for both templates and generated output

**Context**: Hard constraint for this POC: no S3, no external storage.

**Decision**: `templates/` and `generated/` are plain directories on
whatever disk the process runs on, managed by
`FilesystemTemplateRepository` and `LocalFileStorage` respectively.

**Consequences**:
- (+) Zero infrastructure to stand up; `git clone && pip install && run`
  is the entire setup.
- (−) Not viable beyond a single instance: no shared state across
  replicas, nothing survives a container restart/redeploy, no CDN/
  pre-signed-URL story for serving downloads at scale.
- Direct migration path exists and is narrow by design — see ADR-005:
  swapping `LocalFileStorage` for an S3 adapter is a one-file addition
  plus one changed constructor call.

---

## ADR-009: No authentication/authorization

**Context**: Hard constraint for this POC.

**Decision**: Every endpoint is unauthenticated.

**Consequences**:
- (+) Removes an entire dimension of setup (IdP, token issuance, secrets)
  for a proof of concept meant to validate the generation pipeline, not
  access control.
- (−) Not deployable to anything but a fully trusted network as-is. See
  "Auth & authorization" in `production-readiness.md`.

---

## ADR-010: No database — filesystem is the only source of truth

**Context**: Hard constraint for this POC.

**Decision**: No record of a generation request or its result is kept
anywhere except the generated file itself (its filename encodes type,
version, timestamp, and a short id).

**Consequences**:
- (+) One less moving part; nothing to migrate, seed, or back up for the
  POC.
- (−) No way to list "documents generated for customer X," no audit
  trail of who requested what, no way to detect/clean up orphaned files
  by any dimension other than "look at the directory." `GET
  /documents/types` works only because it's derived from the templates
  directory, not from any generation history.
- See "Persistence / metadata" in `production-readiness.md`.

---

## ADR-011: Unified error envelope, no leaked filesystem paths, request-id correlation

**Context**: Real usage surfaced two concrete API-contract problems, not
just documentation gaps:
1. `POST /documents/generate` returned `file_path` — the path *inside
   the running container* (`/app/generated/....docx`). A client cannot
   do anything useful with that path; it repeatedly caused confusion
   about "where did my file go," because the obvious reading (a path on
   the machine making the request) was simply wrong.
2. A malformed request body (missing the `document_type`/`data`
   envelope) returned FastAPI's default `RequestValidationError` shape
   (`{"detail": [...]}`), while a domain failure (e.g. an unknown
   document type) returned this service's own shape
   (`{"error": "TemplateNotFoundError", "detail": "..."}`). Two
   different error shapes from the same API means any client has to
   write two different error-handling branches, and can't rely on a
   single `error.code` field existing on every 4xx/5xx response.

**Decision**:
- Replace `file_path` with `filename` (bare filename — what the download
  endpoint actually takes) and `download_url` (an absolute,
  directly-callable URL built from the *inbound request's* host via
  `request.url_for(...)`, not from any server-internal path). Also added
  `size_bytes`, computed once from the already-in-memory content.
- Every exception (`AppError` and subclasses), every Pydantic
  `RequestValidationError`, and every generic `StarletteHTTPException`
  now renders through the same `ErrorEnvelope`/`ErrorDetail` models in
  `core/errors.py`: `{"error": {"code", "message", "request_id", "fields"?}}`.
  `code` is a stable string set per exception class (e.g.
  `TEMPLATE_NOT_FOUND`), independent of the Python class name.
  `fields` (a list of `{field, message}`) is populated only for
  `VALIDATION_ERROR`, giving a client (or a human pasting a curl
  command) an exact, machine-readable pointer to what's wrong — this is
  the difference between "422, good luck" and "422, you're missing
  `document_type` and `data`."
- Added `RequestIdMiddleware` (`core/middleware.py`): every request gets
  an `X-Request-Id` (reused from the caller if supplied, otherwise
  minted), echoed on every response header and included in every error
  body, so a bug report naming a `request_id` can be matched to a
  specific server log line.
- Added a `json_schema_extra` example to `DocumentGenerateRequest`
  showing the correct envelope shape, so FastAPI's Swagger UI
  ("Try it out") pre-fills a request that actually works, rather than a
  user having to construct the nested `document_type`/`output_format`/`data`
  shape from the field list alone.

**Consequences**:
- (+) A client can write exactly one error-handling code path:
  read `response.json()["error"]["code"]`, always present, same shape.
- (+) `download_url` is correct regardless of deployment topology
  (`localhost`, a Docker Compose service name, or a real domain behind a
  load balancer) because it's derived from the request that hit the
  server, not from configuration.
- (+) `GET /documents/types`'s bare array was also wrapped
  (`{"items": [...], "count": N}`) for the same reason arrays are
  generally avoided as a JSON response root: it leaves room to add
  pagination or metadata later without a breaking shape change.
- (−) This is a breaking change to the response contract for any
  existing client parsing `file_path` or a bare types array — acceptable
  here because there are no external consumers yet (POC), but would
  need an API version bump in a real deployment (see
  `production-readiness.md`).

---

## ADR-012: RESTful resource model — `documents` as a collection, not an action

**Context**: The API was action/RPC-style: `POST /documents/generate`
and `GET /documents/download/{filename}` put verbs in the URL path and
addressed a document by its filename rather than a stable identifier.
This works, but isn't what "RESTful" means: resources should be nouns
addressed by an id, and the action should be expressed by the HTTP
method (`POST` to create, `GET` to read, `DELETE` to remove), not by a
path segment.

**Decision**: Restructure around two resources:
- `documents` — a collection you `POST` to (create/generate),
  `GET` (list) or `GET /{id}` (read one), and `DELETE /{id}` (remove).
  The file's bytes are a sub-resource: `GET /{id}/content`.
- `document-types` — split out to its own top-level resource
  (`GET /document-types`), since a type/template isn't a document, it's
  what a document is generated *from*; nesting it under `documents` (as
  `/documents/types`) conflated two different resources.

No `PUT`/`PATCH` on `documents/{id}`: a generated document is treated as
an immutable artifact. There is no sensible "update a PDF in place"
operation — regenerating is a new `POST`.

Making `documents/{id}` addressable required solving the same problem
ADR-010 already accepted the cost of: no database means no natural place
to store an id → file mapping. The fix is the same shape as ADR-010's
answer for template resolution — encode the identity in the filename
itself. `_build_filename` (`service.py`) now embeds the **full**
`document_id` (previously truncated to 8 hex chars, since it only needed
to be a human-scannable suffix) plus a microsecond-precision timestamp
(previously second-precision — insufficient to order two documents
created in the same second). `storage.find_by_id` reverses this with a
glob (`*_{document_id}.*`); `service._parse_generated_file` reverses the
rest with a regex, reconstructing `document_type`, `version`,
`output_format`, `size_bytes` (via `stat()`), and `created_at` (parsed
from the timestamp segment) with no persistence layer at all.

**Consequences**:
- (+) `document_id` — not a filename — is now the one identifier a
  client needs to hold onto. `content_url` is still returned for
  convenience, but everything (read, delete, content) is reachable from
  `document_id` alone.
- (+) `GET /documents` (list) and `GET /documents/{id}` (read) are new
  capabilities that fell out of solving the addressing problem, not
  extra work: once a document is parseable from its filename, listing
  all of them is just `iterdir()` + parse + filter-out-unparseable.
- (+) `document_id` is validated as a path parameter
  (`pattern=^[0-9a-f]{32}$`), so a malformed or path-traversal-shaped id
  is rejected by FastAPI's routing/validation layer before
  `storage.find_by_id` ever runs — one fewer thing for the storage layer
  to defend against.
- (−) Filenames on disk are longer now (full 32-char id instead of 8)
  and files written by the previous filename scheme are silently
  invisible to `GET /documents`/`GET /documents/{id}` (they simply don't
  match `_FILENAME_PATTERN`, so they're skipped rather than erroring) —
  acceptable for a POC with no persisted history to migrate, would need
  an explicit migration step (rename-in-place, or a backing index) in a
  real deployment.
- (−) Still no true "list documents for customer X" or any query beyond
  "all of them, newest first" — that still needs the database described
  in ADR-010/`production-readiness.md`; this ADR only makes the
  filesystem-as-record trick stretch a little further, not a substitute
  for one.

---

## ADR-013: Legacy `.doc` template support via LibreOffice pre-conversion

**Context**: Templates were `.docx`-only, because docxtpl (ADR-003)
only understands the modern OOXML `.docx` structure — it cannot open
the legacy binary `.doc` format at all. Some organizations still have
templates only in `.doc` (old Word 97-2003 files), and re-authoring
every one in `.docx` isn't always practical before onboarding them.

**Decision**: `FilesystemTemplateRepository` now discovers both `.docx`
and `.doc` (`Settings.template_extensions`, `.docx` first — it wins when
both exist for the same type/version, since it needs no extra step).
When `service.generate()` resolves a `.doc` template, it converts it to
`.docx` first via `LibreOfficeConverter.convert_to_docx` (LibreOffice
has full native `.doc` support — this is an exact conversion, not a
lossy approximation), then feeds the resulting bytes into the same
docxtpl rendering path used for native `.docx` templates. `.doc` support
is therefore additive to the existing pipeline, not a parallel one: the
render step, the error types, and the optional PDF conversion step are
all unchanged and unaware a `.doc` was ever involved.

**A real bug surfaced during implementation, not just extra plumbing**:
verifying this against a genuine legacy `.doc` file (not a renamed
`.docx` — produced via `soffice --convert-to doc` from a python-docx
source, to be sure) found that requesting `output_format: "pdf"` from a
`.doc` template failed with `DOCUMENT_CONVERSION_FAILED: source file
could not be loaded`, while `output_format: "docx"` from the same
template worked fine. Root cause: `python-docx` (which docxtpl saves
through) writes a **duplicate** `docProps/core.xml` zip entry when
re-saving a document that originated from a *LibreOffice-exported*
`.docx`, rather than one authored by Word or python-docx itself — a
genuine interop gap between the two libraries' OPC package handling, not
a mistake in this codebase's own logic. Most zip readers (including
python-docx's own, on the *first* read) silently tolerate a duplicate
name and use the last one. LibreOffice's OOXML import filter does not —
it rejects the file outright. Since a rendered `.docx` from a `.doc`
template may be handed straight back to LibreOffice for PDF conversion,
this was a real, reachable failure, not a theoretical one.

**Fix**: `rendering.py`'s `_dedupe_zip_entries` runs immediately after
`document.save()` inside `DocxtplRenderer.render`, collapsing any
duplicate zip entries (keeping the last occurrence — matching what a
lenient reader would have done anyway) before the bytes leave the
renderer. It opens the zip's central directory once and returns the
input unchanged if there's nothing to dedupe, so it's a no-op for the
common case (a native `.docx` template, which never produces duplicates).

**Consequences**:
- (+) `.doc` and `.docx` templates are interchangeable from the API's
  perspective — same request shape, same `document_type`/`version`
  resolution, same errors, same `output_format` options.
- (+) The zip-dedup fix is defensive at the right layer: it protects
  *any* future path that re-feeds a docxtpl-rendered file back into
  LibreOffice, not just this one, without needing to know in advance
  which templates originated from LibreOffice.
- (−) `.doc` requests cost one extra LibreOffice round-trip
  (`doc → docx`) before rendering even starts, on top of the existing
  `docx → pdf` round-trip when `output_format: "pdf"` — up to two
  LibreOffice subprocess invocations per request instead of one. Same
  scalability caveat as ADR-004/ADR-007: fine for a POC, a stronger
  argument for moving conversion off the request path in production.
- (−) `docProps/core.xml` (document metadata: author, timestamps, etc.)
  reflects whichever occurrence survives dedup, not a merge — acceptable
  since nothing in this system reads or exposes that metadata.
