"""Orchestrates document generation.

No Protocol/port layer: this module owns all four collaborators
(template resolution, rendering, conversion, storage) outright, so the
concrete classes are the contract. Swapping one out later — e.g.
LocalFileStorage for S3 — means changing the constructor call in
`get_document_service()` below and nothing else, which is the only
flexibility this single-module monolith actually needs.
"""
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.modules.documents.conversion import LibreOfficeConverter
from app.modules.documents.rendering import DocxtplRenderer
from app.modules.documents.schemas import DocumentCreateRequest, OutputFormat
from app.modules.documents.storage import LocalFileStorage
from app.modules.documents.templates import FilesystemTemplateRepository, TemplateDescriptor


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    document_id: str
    document_type: str
    version: str
    output_format: OutputFormat
    file_path: Path
    size_bytes: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Mirrors _build_filename below. The full document_id (not truncated) is
# embedded so a document is addressable by id with no database — see
# docs/design-decisions.md ADR-012. Microsecond precision (not just
# seconds) so GET /documents can sort by created_at without ties between
# documents generated in quick succession.
_TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S%fZ"
_FILENAME_PATTERN = re.compile(
    r"^(?P<document_type>[a-z0-9]+(?:_[a-z0-9]+)*)_(?P<version>v\d+)_"
    r"(?P<timestamp>\d{8}T\d{12}Z)_(?P<document_id>[0-9a-f]{32})\.(?P<ext>docx|pdf)$"
)


def _build_filename(document_type: str, version: str, output_format: OutputFormat, document_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime(_TIMESTAMP_FORMAT)
    return f"{document_type}_{version}_{timestamp}_{document_id}.{output_format.value}"


def _parse_generated_file(path: Path) -> GeneratedDocument | None:
    """Reconstructs a document's metadata purely from its filename and
    stat info — the inverse of `_build_filename`. This is what lets
    GET/DELETE /documents/{id} and GET /documents work without a
    database: the filename *is* the record.
    """
    match = _FILENAME_PATTERN.match(path.name)
    if not match:
        return None
    parts = match.groupdict()
    created_at = datetime.strptime(parts["timestamp"], _TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    return GeneratedDocument(
        document_id=parts["document_id"],
        document_type=parts["document_type"],
        version=parts["version"],
        output_format=OutputFormat(parts["ext"]),
        file_path=path,
        size_bytes=path.stat().st_size,
        created_at=created_at,
    )


class DocumentGenerationService:
    def __init__(
        self,
        template_repository: FilesystemTemplateRepository,
        renderer: DocxtplRenderer,
        converter: LibreOfficeConverter,
        storage: LocalFileStorage,
    ) -> None:
        self.template_repository = template_repository
        self.renderer = renderer
        self.converter = converter
        self.storage = storage

    def generate(self, request: DocumentCreateRequest) -> GeneratedDocument:
        template = self.template_repository.resolve(request.document_type, request.version)

        if template.path.suffix.lower() == ".doc":
            # docxtpl only understands the OOXML .docx structure — a
            # legacy .doc template is converted to .docx first, entirely
            # in memory, then rendered exactly like a native .docx one.
            docx_source = self.converter.convert_to_docx(template.path.read_bytes())
            docx_bytes = self.renderer.render(io.BytesIO(docx_source), request.data, label=template.path.name)
        else:
            docx_bytes = self.renderer.render(template.path, request.data, label=template.path.name)

        if request.output_format is OutputFormat.PDF:
            content = self.converter.convert_to_pdf(docx_bytes)
        else:
            content = docx_bytes

        document_id = uuid4().hex
        filename = _build_filename(template.document_type, template.version, request.output_format, document_id)
        stored_path = self.storage.save(filename, content)

        return GeneratedDocument(
            document_id=document_id,
            document_type=template.document_type,
            version=template.version,
            output_format=request.output_format,
            file_path=stored_path,
            size_bytes=len(content),
        )

    def get_document(self, document_id: str) -> GeneratedDocument | None:
        path = self.storage.find_by_id(document_id)
        return _parse_generated_file(path) if path is not None else None

    def list_documents(self) -> list[GeneratedDocument]:
        parsed = (_parse_generated_file(path) for path in self.storage.list_all())
        documents = [d for d in parsed if d is not None]
        return sorted(documents, key=lambda d: d.created_at, reverse=True)

    def delete_document(self, document_id: str) -> bool:
        return self.storage.delete_by_id(document_id)

    def list_supported_document_types(self) -> list[TemplateDescriptor]:
        return self.template_repository.list_available()


@lru_cache
def get_document_service() -> DocumentGenerationService:
    settings = get_settings()
    return DocumentGenerationService(
        template_repository=FilesystemTemplateRepository(settings.templates_dir, settings.template_extensions),
        renderer=DocxtplRenderer(),
        converter=LibreOfficeConverter(settings.libreoffice_binary, settings.conversion_timeout_seconds),
        storage=LocalFileStorage(settings.generated_dir),
    )
