import io
import zipfile

from app.modules.documents.rendering import _dedupe_zip_entries


def _build_zip(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return buffer.getvalue()


def test_dedupe_zip_entries_is_noop_when_no_duplicates():
    data = _build_zip([("a.xml", b"A"), ("b.xml", b"B")])

    assert _dedupe_zip_entries(data) == data


def test_dedupe_zip_entries_keeps_last_occurrence():
    # Reproduces what python-docx can write when re-saving a document
    # that originated from a LibreOffice-exported .docx (see the legacy
    # .doc template path in service.py): a duplicate docProps/core.xml
    # entry that LibreOffice's own OOXML import filter later rejects.
    data = _build_zip(
        [
            ("docProps/core.xml", b"first"),
            ("other.xml", b"unchanged"),
            ("docProps/core.xml", b"second"),
        ]
    )

    result = _dedupe_zip_entries(data)

    with zipfile.ZipFile(io.BytesIO(result)) as zf:
        names = zf.namelist()
        assert names.count("docProps/core.xml") == 1
        assert zf.read("docProps/core.xml") == b"second"
        assert zf.read("other.xml") == b"unchanged"
