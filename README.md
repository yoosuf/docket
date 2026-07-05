# Docket — Document Generation Service

Generates DOCX/PDF documents from versioned templates and dynamic JSON
data. POC-scoped (no DB, no S3, no auth, no queues — everything lives on
local disk), built as a modular monolith.

**Full documentation lives in [`/docs`](./docs/README.md):**
- [`docs/architecture.md`](./docs/architecture.md) — module layout, component & sequence diagrams, extension points
- [`docs/design-decisions.md`](./docs/design-decisions.md) — why the codebase looks the way it does, ADR-style
- [`docs/production-readiness.md`](./docs/production-readiness.md) — how to turn this into a real deployed system (S3, Postgres, queues, auth, observability)

## Adding a new document type

No code changes required. Drop a template file into `templates/` named
`{document_type}_v{version}.docx` (e.g. `credit_note_v1.docx`) —
`FilesystemTemplateRepository` discovers it by convention. Multiple
versions can coexist; the latest is used unless a specific `version` is
requested. See [`docs/architecture.md`](./docs/architecture.md#extension-points-already-supported-zero-code-change)
for details and `scripts/create_sample_templates.py` for a working
docxtpl (Jinja2-in-DOCX) example, including the table row-loop syntax.

Legacy **`.doc`** templates work too — drop in `{type}_v{version}.doc`
and it's converted to `.docx` via LibreOffice automatically before
rendering (`templates/memo_v1.doc` is a working example; see
[`docs/examples.md`](./docs/examples.md#memo-legacy-doc-template)).

## Running

### Option A: Docker Compose (includes LibreOffice — PDF conversion works out of the box)

```bash
docker compose up --build
```

`templates/` and `generated/` are bind-mounted into the container, so
dropping a new `{type}_v{N}.docx` into `templates/` on the host is picked
up immediately, no rebuild needed. The image bakes in LibreOffice, so
`"output_format": "pdf"` works without any host setup.

### Option B: Local Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# (Re)generate the sample templates shipped with this POC
python scripts/create_sample_templates.py

uvicorn app.main:app --reload
```

Either way, interactive docs are at `http://127.0.0.1:8000/docs`.

### PDF conversion

PDF output requires LibreOffice on PATH (`soffice`) — already included in
the Docker image. For local (non-Docker) runs, install it separately;
without it, requests with `"output_format": "pdf"` return `503
ConversionUnavailableError` while DOCX generation is unaffected.

```bash
# macOS
brew install --cask libreoffice
# Debian/Ubuntu
apt-get install libreoffice
```

## API

RESTful resource model — `documents` is a collection you create into,
read from, and delete by id; `document-types` is a separate, read-only
resource. See [`docs/architecture.md`](./docs/architecture.md#api-surface-rest-resource-model)
for the full design rationale.

- `GET /health` — liveness check
- `GET /api/v1/document-types` — supported document types + versions (derived from `templates/`)
- `POST /api/v1/documents` — create (generate) a document
- `GET /api/v1/documents` — list previously generated documents
- `GET /api/v1/documents/{document_id}` — read one document's metadata
- `GET /api/v1/documents/{document_id}/content` — fetch the actual file bytes
- `DELETE /api/v1/documents/{document_id}` — delete a generated document

### Try it immediately with mock data

Ready-to-run sample payloads for all 5 shipped document types
(`invoice`, `quote`, `purchase_order`, `contract`, `memo` — the last one
sourced from a legacy `.doc` template) are in
[`docs/examples/`](./docs/examples/) — no need to construct a request
yourself:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/invoice.json
```

Or use the helper script, which works for any of the shipped types:

```bash
./scripts/try_document.sh                      # invoice, docx (defaults)
./scripts/try_document.sh quote                # quote, docx
./scripts/try_document.sh purchase_order pdf   # purchase_order, pdf
```

See [`docs/examples.md`](./docs/examples.md) for all 5 samples, a
field-reference table per document type, the full read/list/delete flow,
and how to switch to `"output_format": "pdf"`.

## Testing

```bash
pytest
```

Tests exercise the service against real (temp-dir) template/storage
instances and the API via `TestClient` with a single dependency override
(`get_document_service`) — no mocking of the DOCX rendering itself, so a
broken template or a broken `docxtpl` integration would actually fail a
test.

## License & changelog

[MIT](./LICENSE). See [`CHANGELOG.md`](./CHANGELOG.md) for what's changed.
