from datetime import datetime
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from app.models.import_job import DuplicateStrategy, ImportStatus, SourceType


class ApiImportRequest(BaseModel):
    url: AnyHttpUrl
    mapping_profile_id: int | None = None
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.skip


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: SourceType
    filename: str | None
    status: ImportStatus
    mapping_profile_id: int | None
    duplicate_strategy: DuplicateStrategy
    total_records: int
    processed_records: int
    successful_records: int
    updated_records: int
    failed_records: int
    skipped_records: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ImportErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_job_id: int
    row_number: int
    field: str | None
    raw_value: str | None
    error_code: str
    message: str
    raw_record: dict[str, Any]
    created_at: datetime


class ImportReport(BaseModel):
    import_id: int
    status: ImportStatus
    total: int
    successful: int
    updated: int
    skipped: int
    failed: int


class ImportList(BaseModel):
    items: list[ImportJobRead]
    total: int
    page: int
    page_size: int


class ImportErrorList(BaseModel):
    items: list[ImportErrorRead]
    total: int
    page: int
    page_size: int


class ValidationPreview(BaseModel):
    valid: bool
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PreviewRecord(BaseModel):
    raw: dict[str, Any]
    mapped: dict[str, Any]
    transformed: dict[str, Any]
    validation: ValidationPreview


class PreviewResponse(BaseModel):
    detected_columns: list[str]
    preview: list[PreviewRecord]
