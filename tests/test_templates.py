import pytest

from app.modules.documents.exceptions import TemplateNotFoundError
from app.modules.documents.templates import FilesystemTemplateRepository


def test_resolve_picks_latest_version_when_unspecified(templates_dir):
    repo = FilesystemTemplateRepository(templates_dir)

    descriptor = repo.resolve("sample")

    assert descriptor.version == "v2"


def test_resolve_honors_explicit_version(templates_dir):
    repo = FilesystemTemplateRepository(templates_dir)

    descriptor = repo.resolve("sample", version="v1")

    assert descriptor.version == "v1"


def test_resolve_unknown_document_type_raises(templates_dir):
    repo = FilesystemTemplateRepository(templates_dir)

    with pytest.raises(TemplateNotFoundError):
        repo.resolve("does_not_exist")


def test_resolve_unknown_version_raises(templates_dir):
    repo = FilesystemTemplateRepository(templates_dir)

    with pytest.raises(TemplateNotFoundError):
        repo.resolve("sample", version="v99")


def test_list_available_returns_all_versions(templates_dir):
    repo = FilesystemTemplateRepository(templates_dir)

    descriptors = repo.list_available()

    versions = {d.version for d in descriptors if d.document_type == "sample"}
    assert versions == {"v1", "v2"}


def test_new_document_type_discovered_without_code_changes(templates_dir):
    from docx import Document

    doc = Document()
    doc.add_paragraph("{{ anything }}")
    doc.save(templates_dir / "brand_new_type_v1.docx")

    repo = FilesystemTemplateRepository(templates_dir)
    descriptor = repo.resolve("brand_new_type")

    assert descriptor.document_type == "brand_new_type"
    assert descriptor.version == "v1"


def test_resolve_discovers_legacy_doc_extension(templates_dir):
    (templates_dir / "legacy_v1.doc").write_bytes(b"not a real .doc file, just needs to exist")

    repo = FilesystemTemplateRepository(templates_dir)
    descriptor = repo.resolve("legacy")

    assert descriptor.path.suffix == ".doc"
    assert descriptor.version == "v1"


def test_docx_preferred_over_doc_when_both_exist_for_same_version(templates_dir):
    (templates_dir / "dual_v1.doc").write_bytes(b"legacy content")
    (templates_dir / "dual_v1.docx").write_bytes(b"modern content")

    repo = FilesystemTemplateRepository(templates_dir)
    descriptor = repo.resolve("dual")

    assert descriptor.path.suffix == ".docx"
