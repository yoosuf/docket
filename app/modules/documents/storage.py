"""Local disk storage for generated documents.

Stands in for the S3/blob-storage adapter a real deployment would use.

No database means the filename itself is the only record of a document's
identity (see docs/design-decisions.md ADR-010) — `service.py` embeds
the full `document_id` in every filename it writes, so `find_by_id`
below can resolve a REST resource id back to its file without any
external index.
"""
import re
from pathlib import Path

from app.modules.documents.exceptions import DocumentStorageError

_SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_DOCUMENT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes) -> Path:
        destination = self._safe_path(filename)
        try:
            destination.write_bytes(content)
        except OSError as exc:
            raise DocumentStorageError(f"Failed to write '{filename}' to disk: {exc}") from exc
        return destination

    def find_by_id(self, document_id: str) -> Path | None:
        """Resolves a document_id to its file, or None if unknown/invalid."""
        if not _DOCUMENT_ID_PATTERN.match(document_id):
            return None
        matches = [p for p in self._base_dir.glob(f"*_{document_id}.*") if p.is_file()]
        return matches[0] if len(matches) == 1 else None

    def delete_by_id(self, document_id: str) -> bool:
        path = self.find_by_id(document_id)
        if path is None:
            return False
        path.unlink()
        return True

    def list_all(self) -> list[Path]:
        return [p for p in self._base_dir.iterdir() if p.is_file() and not p.name.startswith(".")]

    def _safe_path(self, filename: str) -> Path:
        if not _SAFE_FILENAME_PATTERN.match(filename):
            raise DocumentStorageError(f"Refusing to access unsafe filename: {filename!r}")
        return self._base_dir / filename
