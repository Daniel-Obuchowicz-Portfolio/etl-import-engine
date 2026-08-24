from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep, SettingsDep
from app.core.exceptions import AppError, NotFoundError
from app.models.import_job import DuplicateStrategy, ImportJob, ImportStatus, SourceType
from app.models.mapping_profile import MappingProfile
from app.parsers.csv_parser import CsvParser
from app.parsers.json_parser import JsonParser
from app.repositories.imports import ImportRepository
from app.schemas.imports import (
    ApiImportRequest,
    ImportErrorList,
    ImportJobRead,
    ImportList,
    ImportReport,
    PreviewResponse,
)
from app.services.import_service import ImportService
from app.services.preview_service import PreviewService

router = APIRouter(prefix="/imports", tags=["imports"])


def report(job: ImportJob) -> ImportReport:
    return ImportReport(
        import_id=job.id,
        status=job.status,
        total=job.total_records,
        successful=job.successful_records,
        updated=job.updated_records,
        skipped=job.skipped_records,
        failed=job.failed_records,
    )


def validate_csv_upload(file: UploadFile, max_size_mb: int | None = None) -> None:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise AppError("IMPORT_FILE_INVALID", "A .csv file is required", status_code=422)
    allowed_types = {"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain", ""}
    if (file.content_type or "") not in allowed_types:
        raise AppError("IMPORT_FILE_INVALID", "Uploaded file is not a CSV", status_code=422)
    if max_size_mb is not None and file.size is not None and file.size > max_size_mb * 1024 * 1024:
        raise AppError(
            "IMPORT_FILE_INVALID",
            f"Uploaded file exceeds the {max_size_mb} MB limit",
            status_code=413,
        )


@router.post("/csv", response_model=ImportReport, status_code=status.HTTP_201_CREATED)
async def import_csv(
    session: SessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="UTF-8 encoded CSV")],
    mapping_profile_id: Annotated[int | None, Form()] = None,
    duplicate_strategy: Annotated[DuplicateStrategy, Form()] = DuplicateStrategy.skip,
) -> ImportReport:
    validate_csv_upload(file, settings.max_upload_size_mb)
    job = await ImportService(session, settings).run(
        CsvParser(file.file).parse(),
        source_type=SourceType.csv,
        filename=file.filename,
        mapping_profile_id=mapping_profile_id,
        duplicate_strategy=duplicate_strategy,
    )
    return report(job)


@router.post("/json", response_model=ImportReport, status_code=status.HTTP_201_CREATED)
async def import_json(
    payload: list[dict[str, Any]],
    session: SessionDep,
    settings: SettingsDep,
    mapping_profile_id: int | None = None,
    duplicate_strategy: DuplicateStrategy = DuplicateStrategy.skip,
) -> ImportReport:
    job = await ImportService(session, settings).run(
        JsonParser(payload).parse(),
        source_type=SourceType.json,
        filename=None,
        mapping_profile_id=mapping_profile_id,
        duplicate_strategy=duplicate_strategy,
    )
    return report(job)


@router.post("/api", response_model=ImportReport, status_code=status.HTTP_201_CREATED)
async def import_api(
    payload: ApiImportRequest, session: SessionDep, settings: SettingsDep
) -> ImportReport:
    job = await ImportService(session, settings).run_api(
        url=str(payload.url),
        mapping_profile_id=payload.mapping_profile_id,
        duplicate_strategy=payload.duplicate_strategy,
    )
    return report(job)


@router.post("/preview", response_model=PreviewResponse)
async def preview_csv(
    session: SessionDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="UTF-8 encoded CSV")],
    mapping_profile_id: Annotated[int | None, Form()] = None,
    limit: Annotated[int, Form(ge=1, le=100)] = 10,
) -> PreviewResponse:
    validate_csv_upload(file, settings.max_upload_size_mb)
    mapping: dict[str, str] = {}
    if mapping_profile_id is not None:
        profile = await session.get(MappingProfile, mapping_profile_id)
        if profile is None:
            raise NotFoundError("Mapping profile")
        mapping = profile.mapping
    return PreviewService().run(CsvParser(file.file).parse(), mapping=mapping, limit=limit)


@router.get("", response_model=ImportList)
async def list_imports(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    import_status: Annotated[ImportStatus | None, Query(alias="status")] = None,
    source_type: SourceType | None = None,
    sort_by: Annotated[
        str, Query(pattern="^(id|created_at|finished_at|status|total_records)$")
    ] = "created_at",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> ImportList:
    items, total = await ImportRepository(session).list(
        page=page,
        page_size=page_size,
        status=import_status,
        source_type=source_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ImportList(items=items, total=total, page=page, page_size=page_size)


async def get_job(session: AsyncSession, import_id: int) -> ImportJob:
    job = await session.get(ImportJob, import_id)
    if job is None:
        raise NotFoundError("Import")
    return job


@router.get("/{import_id}", response_model=ImportJobRead)
async def get_import(import_id: int, session: SessionDep) -> ImportJob:
    return await get_job(session, import_id)


@router.get("/{import_id}/errors", response_model=ImportErrorList)
async def get_import_errors(
    import_id: int,
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ImportErrorList:
    await get_job(session, import_id)
    items, total = await ImportRepository(session).errors(import_id, page=page, page_size=page_size)
    return ImportErrorList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{import_id}/report", response_model=ImportReport)
async def get_import_report(import_id: int, session: SessionDep) -> ImportReport:
    return report(await get_job(session, import_id))
