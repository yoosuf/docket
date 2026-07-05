"""DOCX rendering backed by docxtpl (Jinja2 templating inside .docx files).

Accepts either a file path (the common case — a `.docx` template
resolved straight from disk) or in-memory bytes (a legacy `.doc`
template that `service.py` already converted to `.docx` via
LibreOffice before handing it here). docxtpl's `DocxTemplate` natively
accepts either.
"""
import io
import zipfile
from pathlib import Path
from typing import IO, Any, Union

from docxtpl import DocxTemplate
from jinja2 import TemplateError

from app.modules.documents.exceptions import TemplateRenderError


def _dedupe_zip_entries(data: bytes) -> bytes:
    """Collapses duplicate zip entries, keeping the last occurrence of each.

    python-docx (which docxtpl saves through) can write a duplicate
    `docProps/core.xml` entry when re-saving a document that originated
    from a LibreOffice-exported .docx rather than one authored by Word
    or python-docx itself — reproducible via the legacy `.doc` template
    path, which round-trips through LibreOffice before ever reaching
    docxtpl. Most zip readers silently tolerate duplicate names
    (last-entry-wins), but LibreOffice's own OOXML import filter rejects
    them outright ("source file could not be loaded") — which matters
    here because a rendered .docx may be handed straight back to
    LibreOffice for PDF conversion. This is a no-op (single zip
    read+recompress) in the common case where there's nothing to dedupe.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as source:
        names = source.namelist()
        if len(names) == len(set(names)):
            return data

        order: list[str] = []
        content_by_name: dict[str, bytes] = {}
        for info in source.infolist():
            if info.filename not in content_by_name:
                order.append(info.filename)
            content_by_name[info.filename] = source.read(info.filename)

        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for name in order:
                target.writestr(name, content_by_name[name])
        return output.getvalue()


class DocxtplRenderer:
    def render(self, template_source: Union[Path, IO[bytes]], data: dict[str, Any], *, label: str = "template") -> bytes:
        try:
            document = DocxTemplate(template_source)
            document.render(data)
        except TemplateError as exc:
            raise TemplateRenderError(f"Failed to render {label}: {exc}") from exc
        except Exception as exc:  # docxtpl/lxml can raise a variety of low-level errors
            raise TemplateRenderError(f"Unexpected error rendering {label}: {exc}") from exc

        buffer = io.BytesIO()
        document.save(buffer)
        return _dedupe_zip_entries(buffer.getvalue())
