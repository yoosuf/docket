from app.core.exceptions import AppError


class TemplateNotFoundError(AppError):
    status_code = 404
    code = "TEMPLATE_NOT_FOUND"


class TemplateRenderError(AppError):
    status_code = 422
    code = "TEMPLATE_RENDER_ERROR"


class ConversionUnavailableError(AppError):
    status_code = 503
    code = "CONVERSION_UNAVAILABLE"


class DocumentConversionError(AppError):
    status_code = 502
    code = "DOCUMENT_CONVERSION_FAILED"


class DocumentStorageError(AppError):
    status_code = 500
    code = "DOCUMENT_STORAGE_FAILED"


class DocumentNotFoundError(AppError):
    status_code = 404
    code = "DOCUMENT_NOT_FOUND"
