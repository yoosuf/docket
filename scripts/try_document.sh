#!/usr/bin/env bash
# Quick smoke test: generate a sample document against a locally running
# Docket instance (docker compose up, or uvicorn app.main:app), using
# the mock payloads in docs/examples/.
#
# Usage:
#   ./scripts/try_document.sh                        # invoice, docx (defaults)
#   ./scripts/try_document.sh quote                   # quote, docx
#   ./scripts/try_document.sh purchase_order pdf       # purchase_order, pdf
#   ./scripts/try_document.sh contract pdf
set -euo pipefail

HOST="${DOCKET_HOST:-http://localhost:8000}"
DOCUMENT_TYPE="${1:-invoice}"
FORMAT="${2:-docx}"
EXAMPLE_FILE="docs/examples/${DOCUMENT_TYPE}.json"

if [ ! -f "$EXAMPLE_FILE" ]; then
  echo "No sample payload for document type '$DOCUMENT_TYPE'." >&2
  available=$(ls docs/examples/*.json 2>/dev/null | xargs -n1 basename | sed 's/\.json$//' | tr '\n' ' ')
  echo "Available: ${available}" >&2
  exit 1
fi

curl -sS -X POST "$HOST/api/v1/documents" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
payload = json.load(open('$EXAMPLE_FILE'))
payload['output_format'] = '$FORMAT'
print(json.dumps(payload))
")"
echo
