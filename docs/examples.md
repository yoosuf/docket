# Sample Requests

Ready-to-run mock payloads for all 5 document types shipped with this
POC, so you can generate a real document in one command with nothing to
fill in yourself. The raw JSON files live in
[`docs/examples/`](./examples/) — each verified against the running
service (both the rendered field substitution and the table row loop for
line items).

Field names below match the placeholders in `templates/{type}_v1.docx`
(or `.doc` — see [Memo](#memo-legacy-doc-template)), authored by
`scripts/create_sample_templates.py`. If you add your own template for a
type, its `data` shape is whatever placeholders you put in that file —
these tables just document what the *shipped* samples expect.

## Quick start

```bash
# Start the service (either works)
docker compose up -d --build
# or: uvicorn app.main:app --reload

curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/invoice.json
```

Swap `invoice.json` for `quote.json`, `purchase_order.json`,
`contract.json`, or `memo.json` to try the others. Edit
`"output_format"` from `"docx"` to `"pdf"` in any of them to get a PDF
back instead (requires
LibreOffice — already included if you're using Docker Compose).

### Or use the helper script

`scripts/try_document.sh` wraps the curl call above for any shipped
document type — it reads `docs/examples/<type>.json` and swaps in the
output format you ask for, so you never have to hand-edit JSON just to
try a different combination:

```bash
./scripts/try_document.sh                      # invoice, docx (defaults)
./scripts/try_document.sh quote                # quote, docx
./scripts/try_document.sh purchase_order pdf   # purchase_order, pdf
./scripts/try_document.sh contract pdf
```

Passing a document type with no matching file in `docs/examples/` fails
with a list of what's actually available, instead of a confusing error
from the API:

```
$ ./scripts/try_document.sh nonexistent_type
No sample payload for document type 'nonexistent_type'.
Available: contract invoice memo purchase_order quote
```

`DOCKET_HOST` overrides the target (defaults to `http://localhost:8000`)
if you're running the service somewhere other than locally.

## Invoice

`data` shape (`templates/invoice_v1.docx`):

| Field | Type | Notes |
|---|---|---|
| `invoice_number` | string | |
| `issue_date` | string | Free-text — the template does not parse/validate dates |
| `due_date` | string | |
| `customer_name` | string | |
| `line_items` | array of `{description, quantity, unit_price, total}` | Rendered as a repeating table row |
| `subtotal` | string | Not computed from `line_items` — pass the final value |
| `tax` | string | |
| `total_due` | string | |

<details>
<summary>docs/examples/invoice.json</summary>

```json
{
  "document_type": "invoice",
  "output_format": "docx",
  "data": {
    "invoice_number": "INV-1001",
    "issue_date": "2026-07-04",
    "due_date": "2026-07-18",
    "customer_name": "Acme Corp",
    "line_items": [
      {"description": "Consulting Services", "quantity": 10, "unit_price": "150.00", "total": "1500.00"},
      {"description": "Support Retainer", "quantity": 1, "unit_price": "400.00", "total": "400.00"}
    ],
    "subtotal": "1900.00",
    "tax": "190.00",
    "total_due": "2090.00"
  }
}
```
</details>

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/invoice.json
```

## Quote

`data` shape (`templates/quote_v1.docx`):

| Field | Type | Notes |
|---|---|---|
| `quote_number` | string | |
| `valid_until` | string | |
| `customer_name` | string | |
| `line_items` | array of `{description, quantity, unit_price, total}` | |
| `estimated_total` | string | |

<details>
<summary>docs/examples/quote.json</summary>

```json
{
  "document_type": "quote",
  "output_format": "docx",
  "data": {
    "quote_number": "Q-2024-045",
    "valid_until": "2026-08-01",
    "customer_name": "Beta Industries",
    "line_items": [
      {"description": "Website Redesign", "quantity": 1, "unit_price": "8000.00", "total": "8000.00"},
      {"description": "SEO Audit", "quantity": 1, "unit_price": "1200.00", "total": "1200.00"}
    ],
    "estimated_total": "9200.00"
  }
}
```
</details>

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/quote.json
```

## Purchase Order

`data` shape (`templates/purchase_order_v1.docx`):

| Field | Type | Notes |
|---|---|---|
| `po_number` | string | |
| `order_date` | string | |
| `vendor_name` | string | |
| `ship_to_address` | string | |
| `line_items` | array of `{description, quantity, unit_price, total}` | |
| `order_total` | string | |

<details>
<summary>docs/examples/purchase_order.json</summary>

```json
{
  "document_type": "purchase_order",
  "output_format": "docx",
  "data": {
    "po_number": "PO-58210",
    "order_date": "2026-07-04",
    "vendor_name": "Global Supplies Ltd.",
    "ship_to_address": "123 Warehouse Way, Springfield, IL 62704",
    "line_items": [
      {"description": "Office Chairs", "quantity": 20, "unit_price": "85.00", "total": "1700.00"},
      {"description": "Standing Desks", "quantity": 10, "unit_price": "320.00", "total": "3200.00"}
    ],
    "order_total": "4900.00"
  }
}
```
</details>

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/purchase_order.json
```

## Contract

`data` shape (`templates/contract_v1.docx`) — the only shipped type
without a `line_items` table, just a free-text terms block:

| Field | Type | Notes |
|---|---|---|
| `contract_number` | string | |
| `effective_date` | string | |
| `party_a_name` | string | |
| `party_b_name` | string | |
| `terms_text` | string | Rendered as a single paragraph, no line-loop |
| `contract_value` | string | |

<details>
<summary>docs/examples/contract.json</summary>

```json
{
  "document_type": "contract",
  "output_format": "docx",
  "data": {
    "contract_number": "C-2026-012",
    "effective_date": "2026-07-04",
    "party_a_name": "Acme Corp",
    "party_b_name": "Beta LLC",
    "terms_text": "Beta LLC agrees to provide consulting services to Acme Corp for a period of 12 months, commencing on the effective date above. Either party may terminate this agreement with 30 days written notice.",
    "contract_value": "60000.00"
  }
}
```
</details>

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/contract.json
```

## Memo (legacy `.doc` template)

`data` shape (`templates/memo_v1.doc`) — this template exists specifically
to demonstrate `.doc` support: it's a genuine legacy binary Word document
(not a renamed `.docx`), transparently converted to `.docx` via
LibreOffice before the same Jinja2/docxtpl rendering used for every other
type runs. See ADR-013 in [`design-decisions.md`](./design-decisions.md).

| Field | Type | Notes |
|---|---|---|
| `recipient` | string | |
| `author` | string | |
| `subject` | string | |
| `body` | string | Rendered as a single paragraph |

<details>
<summary>docs/examples/memo.json</summary>

```json
{
  "document_type": "memo",
  "output_format": "docx",
  "data": {
    "recipient": "All Staff",
    "author": "Ada Lovelace",
    "subject": "Legacy .doc template support",
    "body": "This memo was rendered from a genuine legacy .doc template, converted to .docx by LibreOffice before Jinja2 data was applied."
  }
}
```
</details>

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/memo.json
```

## Working with the created document

`POST /documents` returns a full resource representation:

```json
{
  "document_id": "bc966a14b176440390302a36faceea06",
  "document_type": "invoice",
  "version": "v1",
  "output_format": "docx",
  "filename": "invoice_v1_20260705T030041771156Z_bc966a14b176440390302a36faceea06.docx",
  "content_url": "http://localhost:8000/api/v1/documents/bc966a14b176440390302a36faceea06/content",
  "size_bytes": 37010,
  "created_at": "2026-07-05T03:00:41.771156Z"
}
```

`document_id` is the resource's identity — use it for everything else:

```bash
# List everything generated so far
curl http://localhost:8000/api/v1/documents

# Read one document's metadata
curl http://localhost:8000/api/v1/documents/bc966a14b176440390302a36faceea06

# Fetch the actual file bytes (or just curl content_url from the create response)
curl -o invoice.docx http://localhost:8000/api/v1/documents/bc966a14b176440390302a36faceea06/content

# Delete it
curl -X DELETE http://localhost:8000/api/v1/documents/bc966a14b176440390302a36faceea06
```

(An earlier version of this API had a single `POST /documents/generate`
action endpoint and a separate `GET /documents/download/{filename}`, and
returned an absolute server-internal path — e.g. `/app/generated/....docx`,
the container's filesystem path, not anything reachable on your host.
The current shape is REST-resource-oriented: `documents` is a collection
you `POST` to create, `GET`/`DELETE` by id, with `content` as a
sub-resource — see `docs/design-decisions.md` ADR-012.)

If you're running via Docker Compose, the same file is also directly
readable from the host at `./generated/<filename>` thanks to the bind
mount — but `content_url` is the supported way to fetch it
programmatically.

## Error responses

Every error — a bad request body, an unknown document type, a missing
document — returns the same envelope shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "8cf8c4308d89",
    "fields": [
      {"field": "document_type", "message": "Field required"},
      {"field": "data", "message": "Field required"}
    ]
  }
}
```

`fields` only appears for `VALIDATION_ERROR` (a malformed request body —
e.g. posting the invoice fields directly instead of nesting them under
`"data"` — or an invalid `document_id` in the URL, which is validated as
a path parameter). Every response, success or error, also carries an
`X-Request-Id` header — include it when reporting an issue so the
corresponding server log line can be found.

| `code` | HTTP status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body or path parameter doesn't match the schema — see `fields` |
| `TEMPLATE_NOT_FOUND` | 404 | No template on disk for that `document_type` (+ `version` if given) |
| `TEMPLATE_RENDER_ERROR` | 422 | The template's Jinja placeholders don't match the supplied `data` |
| `CONVERSION_UNAVAILABLE` | 503 | `output_format: "pdf"` requested but LibreOffice isn't installed/reachable |
| `DOCUMENT_CONVERSION_FAILED` | 502 | LibreOffice ran but the conversion itself failed |
| `DOCUMENT_NOT_FOUND` | 404 | No document with that id (`GET`/`DELETE /documents/{id}`, `GET /documents/{id}/content`) |
| `DOCUMENT_STORAGE_FAILED` | 500 | Couldn't write the generated file to disk |
| `HTTP_ERROR` | varies | Generic framework-level error (e.g. wrong HTTP method, unknown route) |
