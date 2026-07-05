"""Wire contracts for the documents module.

Used directly as the service layer's input/output too — this is a
single-module monolith, not a multi-team API, so keeping one model
instead of a parallel domain-model copy is the simpler choice.
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_EXAMPLE_REQUEST = {
    "document_type": "invoice",
    "output_format": "pdf",
    "data": {
        "invoice_number": "INV-1001",
        "issue_date": "2026-07-04",
        "due_date": "2026-07-18",
        "customer_name": "Acme Corp",
        "line_items": [
            {"description": "Consulting", "quantity": 10, "unit_price": "150.00", "total": "1500.00"}
        ],
        "subtotal": "1500.00",
        "tax": "150.00",
        "total_due": "1650.00",
    },
}


class OutputFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"


class DocumentCreateRequest(BaseModel):
    # Pre-fills FastAPI/Swagger's "Try it out" with a known-correct,
    # working example — the request_type/data envelope is easy to get
    # wrong by hand (a flat body with no `data` wrapper is the single
    # most common mistake), so showing a real example beats explaining it.
    model_config = ConfigDict(json_schema_extra={"example": _EXAMPLE_REQUEST})

    document_type: str = Field(..., min_length=1, max_length=50, examples=["invoice"])
    version: str | None = Field(
        default=None,
        max_length=10,
        description="Defaults to the latest available version.",
        examples=["v1"],
    )
    output_format: OutputFormat = OutputFormat.DOCX
    data: dict[str, Any] = Field(..., description="Data rendered into the template.")


class DocumentResponse(BaseModel):
    """Representation of a generated document resource (`/documents/{id}`)."""

    document_id: str
    document_type: str
    version: str
    output_format: OutputFormat
    filename: str
    content_url: str = Field(..., description="Absolute URL — GET this to retrieve the file bytes.")
    size_bytes: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    count: int


class DocumentTypeResponse(BaseModel):
    document_type: str
    version: str


class DocumentTypeListResponse(BaseModel):
    items: list[DocumentTypeResponse]
    count: int
