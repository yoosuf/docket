<p align="center">
  <h1 align="center">Docket</h1>
  <p align="center"><strong>Document Generation Service</strong></p>
  <p align="center">
    Generate DOCX/PDF from versioned templates and dynamic JSON data.<br>
    Convention-based template discovery — drop a file, it's live. No code changes.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT">
  <img src="https://img.shields.io/badge/tests-36%20passing-brightgreen" alt="36 tests">
</p>

---

## ✨ Features

- **Zero-code document types** — Drop `{type}_v{version}.docx` into `templates/` and it's immediately available via the API
- **Legacy `.doc` support** — Old Word templates auto-convert to `.docx` via LibreOffice
- **PDF output** — Seamless DOCX→PDF via LibreOffice (baked into the Docker image)
- **Versioned templates** — Multiple versions coexist; latest is used unless a specific version is requested
- **RESTful API** — Clean resource model (`documents`, `document-types`) with OpenAPI docs
- **No database** — Metadata is encoded in filenames; everything lives on disk (swap out for S3/Postgres when you're ready)
- **Docker-native** — Single `docker compose up` with LibreOffice included

## 🚀 Quick start

```bash
git clone https://github.com/yoosuf/docket.git
cd docket
docker compose up --build
```

Open **http://127.0.0.1:8000/docs** — interactive API docs are ready.

## 📄 Usage

### Try it in one command:

```bash
./scripts/try_document.sh                     # invoice, docx
./scripts/try_document.sh quote pdf           # quote, pdf
./scripts/try_document.sh purchase_order pdf  # purchase_order, pdf
```

### Or via curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -H "Content-Type: application/json" \
  -d @docs/examples/invoice.json
```

### Adding a new document type:

1. Create a template (`docxtpl`-compatible `.docx` with Jinja2 placeholders)
2. Name it `{type}_v{version}.docx` and drop it into `templates/`
3. That's it — no code, no config, no restart

## 📚 Documentation

| Document | What's inside |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Module layout, component & sequence diagrams, extension points |
| [`docs/design-decisions.md`](docs/design-decisions.md) | ADR-style rationale for key architectural choices |
| [`docs/production-readiness.md`](docs/production-readiness.md) | Migration guide: local disk → S3, no DB → Postgres, sync → job queues |
| [`docs/examples.md`](docs/examples.md) | Ready-to-run samples for all 5 shipped document types |

## 🧪 Tests

```bash
pytest
```

36 tests exercising template resolution, service orchestration, REST endpoints, and rendering — no mocks on the DOCX layer.

## 🏗 Architecture

Modular monolith — one domain (`documents`) in one folder:

```
app/
├── main.py           # Composition root (FastAPI app)
├── core/             # Config, errors, middleware
└── modules/
    └── documents/    # Router, service, repository, models
```

Full architecture docs at [`docs/architecture.md`](docs/architecture.md).

## 📦 Shipped templates

| Type | Template | Version |
|---|---|---|
| Invoice | `invoice_v1.docx` | 1 |
| Quote | `quote_v1.docx` | 1 |
| Purchase Order | `purchase_order_v1.docx` | 1 |
| Contract | `contract_v1.docx` | 1 |
| Memo | `memo_v1.doc` (legacy) | 1 |

## 🛠 Tech stack

[FastAPI](https://fastapi.tiangolo.com/) · [docxtpl](https://github.com/elapouya/python-docx-template) (Jinja2-in-DOCX) · [LibreOffice](https://www.libreoffice.org/) (PDF conversion) · [Docker](https://www.docker.com/) · [Pydantic](https://docs.pydantic.dev/) · [Uvicorn](https://www.uvicorn.org/)

## 📜 License

[MIT](LICENSE) © 2026 Yoosuf

---

> **Status:** POC — no production dependencies (no DB, no S3, no auth, no queues). Ready to evolve into a full document service — see the [production-readiness guide](docs/production-readiness.md).
