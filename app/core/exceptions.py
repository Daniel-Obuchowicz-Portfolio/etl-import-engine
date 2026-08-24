from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str) -> None:
        super().__init__("NOT_FOUND", f"{resource} not found", status_code=404)


class ImportSourceError(AppError):
    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__("IMPORT_SOURCE_ERROR", message, status_code=422, details=details)


class MappingError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("MAPPING_ERROR", message, status_code=422)
