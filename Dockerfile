FROM python:3.12-slim

# LibreOffice (headless) is what powers DOCX -> PDF conversion — see
# docs/design-decisions.md (ADR-004). Baking it into the image means PDF
# generation works out of the box in the container even on machines
# (like a bare local venv) that don't have LibreOffice installed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY scripts/ scripts/

# Bake in the sample templates so the image is runnable standalone;
# docker-compose.yml bind-mounts ./templates over this in local dev so
# new templates are picked up without a rebuild.
RUN mkdir -p templates generated \
    && python scripts/create_sample_templates.py

RUN useradd --create-home --uid 1000 docket \
    && chown -R docket:docket /app
USER docket

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
