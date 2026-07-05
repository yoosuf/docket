"""HTTP routes for the documents module.

RESTful resource model — nouns in the path, verbs via HTTP method:

    POST   /documents               create a document (render + optionally convert)
    GET    /documents               list previously generated documents
    GET    /documents/{id}          read one document's metadata
    GET    /documents/{id}/content  fetch the actual file bytes
    DELETE /documents/{id}          delete a generated document
    GET    /document-types          list available document types/versions

No PUT/PATCH: a generated document is an immutable artifact — to get a
different rendering, POST a new one rather than mutating an existing one.
`document-types` is its own top-level resource (not nested under
`documents`) because a type/template isn't a document — it's what a
document is generated *from*.

Thin by design: handlers translate HTTP <-> service calls, nothing else.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path as PathParam, Request, Response, status
from fastapi.responses import FileResponse

from app.modules.documents.exceptions import DocumentNotFoundError
from app.modules.documents.schemas import (
    DocumentCreateRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentTypeListResponse,
    DocumentTypeResponse,
)
from app.modules.documents.service import DocumentGenerationService, GeneratedDocument, get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])
document_types_router = APIRouter(prefix="/document-types", tags=["document-types"])

ServiceDep = Annotated[DocumentGenerationService, Depends(get_document_service)]
DocumentId = Annotated[
    str,
    PathParam(pattern=r"^[0-9a-f]{32}$", description="The document_id returned when the document was created."),
]


def _to_response(document: GeneratedDocument, request: Request) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        document_type=document.document_type,
        version=document.version,
        output_format=document.output_format,
        filename=document.file_path.name,
        content_url=str(request.url_for("get_document_content", document_id=document.document_id)),
        size_bytes=document.size_bytes,
        created_at=document.created_at,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreateRequest, request: Request, response: Response, service: ServiceDep
) -> DocumentResponse:
    document = service.generate(payload)
    response.headers["Location"] = str(request.url_for("get_document", document_id=document.document_id))
    return _to_response(document, request)


@router.get("", response_model=DocumentListResponse)
def list_documents(request: Request, service: ServiceDep) -> DocumentListResponse:
    items = [_to_response(d, request) for d in service.list_documents()]
    return DocumentListResponse(items=items, count=len(items))


@router.get("/{document_id}", response_model=DocumentResponse, name="get_document")
def get_document(document_id: DocumentId, request: Request, service: ServiceDep) -> DocumentResponse:
    document = service.get_document(document_id)
    if document is None:
        raise DocumentNotFoundError(f"No document found with id '{document_id}'.")
    return _to_response(document, request)


@router.get("/{document_id}/content", name="get_document_content")
def get_document_content(document_id: DocumentId, service: ServiceDep) -> FileResponse:
    document = service.get_document(document_id)
    if document is None:
        raise DocumentNotFoundError(f"No document found with id '{document_id}'.")
    return FileResponse(document.file_path)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: DocumentId, service: ServiceDep) -> None:
    if not service.delete_document(document_id):
        raise DocumentNotFoundError(f"No document found with id '{document_id}'.")


@document_types_router.get("", response_model=DocumentTypeListResponse)
def list_document_types(service: ServiceDep) -> DocumentTypeListResponse:
    items = [
        DocumentTypeResponse(document_type=d.document_type, version=d.version)
        for d in service.list_supported_document_types()
    ]
    return DocumentTypeListResponse(items=items, count=len(items))
