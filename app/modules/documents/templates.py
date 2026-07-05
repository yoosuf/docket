"""Filesystem-backed template resolution.

Convention over configuration: any file named `{document_type}_v{N}.docx`
(or `.doc`) dropped into the templates directory is automatically
discovered — new document types need no code changes anywhere in this
module. Legacy `.doc` templates are supported transparently: the
renderer pipeline (see `service.py`) pre-converts them to `.docx` via
LibreOffice before the same Jinja2/docxtpl rendering step runs — this
module only needs to know they exist and resolve like any other template.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from app.modules.documents.exceptions import TemplateNotFoundError

_TEMPLATE_NAME_PATTERN = re.compile(r"^(?P<doc_type>[a-z0-9]+(?:_[a-z0-9]+)*)_v(?P<version>\d+)$")


@dataclass(frozen=True, slots=True)
class TemplateDescriptor:
    document_type: str
    version: str
    path: Path


def _normalize_version(version: str) -> str:
    """Accepts 'v1', '1', or 'V1' and normalizes to 'v1'."""
    stripped = version.strip().lower().removeprefix("v")
    if not stripped.isdigit():
        raise TemplateNotFoundError(f"Invalid version identifier: {version!r}")
    return f"v{int(stripped)}"


class FilesystemTemplateRepository:
    def __init__(self, templates_dir: Path, extensions: tuple[str, ...] = (".docx", ".doc")) -> None:
        self._templates_dir = templates_dir
        self._extensions = tuple(e if e.startswith(".") else f".{e}" for e in extensions)

    def _scan(self) -> list[TemplateDescriptor]:
        if not self._templates_dir.exists():
            return []

        # First extension in self._extensions wins when both a .docx and
        # a .doc exist for the same document_type/version.
        by_key: dict[tuple[str, str], TemplateDescriptor] = {}
        for extension in self._extensions:
            for path in self._templates_dir.glob(f"*{extension}"):
                match = _TEMPLATE_NAME_PATTERN.match(path.stem.lower())
                if not match:
                    continue
                key = (match.group("doc_type"), f"v{int(match.group('version'))}")
                if key not in by_key:
                    by_key[key] = TemplateDescriptor(document_type=key[0], version=key[1], path=path)
        return list(by_key.values())

    def resolve(self, document_type: str, version: str | None = None) -> TemplateDescriptor:
        normalized_type = document_type.strip().lower()
        candidates = [d for d in self._scan() if d.document_type == normalized_type]

        if not candidates:
            raise TemplateNotFoundError(f"No template found for document type '{document_type}'.")

        if version is not None:
            normalized_version = _normalize_version(version)
            for candidate in candidates:
                if candidate.version == normalized_version:
                    return candidate
            raise TemplateNotFoundError(
                f"No template found for document type '{document_type}' "
                f"at version '{normalized_version}'."
            )

        return max(candidates, key=lambda d: int(d.version.removeprefix("v")))

    def list_available(self) -> list[TemplateDescriptor]:
        return sorted(self._scan(), key=lambda d: (d.document_type, int(d.version.removeprefix("v"))))
