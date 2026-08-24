import json
from collections.abc import Iterable
from datetime import UTC, datetime
from itertools import islice
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import logger
from app.models.customer import Customer
from app.models.import_error import ImportError
from app.models.import_job import (
    DuplicateStrategy,
    ImportJob,
    ImportStatus,
    SourceType,
)
from app.parsers.api_parser import ApiParser
from app.parsers.base import Record
from app.repositories.company import CompanyRepository
from app.repositories.customer import CustomerRepository
from app.services.deduplication_service import DeduplicationService
from app.services.mapping_service import MappingService
from app.services.transformation_service import TransformationService
from app.services.validation_service import ValidationService


class ImportService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.mapping = MappingService()
        self.transformation = TransformationService()
        self.validation = ValidationService()
        self.deduplication = DeduplicationService()
        self.customers = CustomerRepository(session)
        self.companies = CompanyRepository(session)

    async def run(
        self,
        records: Iterable[Record],
        *,
        source_type: SourceType,
        filename: str | None,
        mapping_profile_id: int | None,
        duplicate_strategy: DuplicateStrategy,
    ) -> ImportJob:
        job = await self._create_job(
            source_type=source_type,
            filename=filename,
            mapping_profile_id=mapping_profile_id,
            duplicate_strategy=duplicate_strategy,
        )
        return await self._execute(job, records)

    async def run_api(
        self,
        *,
        url: str,
        mapping_profile_id: int | None,
        duplicate_strategy: DuplicateStrategy,
    ) -> ImportJob:
        job = await self._create_job(
            source_type=SourceType.api,
            filename=url[:255],
            mapping_profile_id=mapping_profile_id,
            duplicate_strategy=duplicate_strategy,
        )
        try:
            parser = await ApiParser.fetch(url, timeout=self.settings.api_request_timeout_seconds)
            return await self._execute(job, parser.parse())
        except Exception:
            if job.status not in {
                ImportStatus.completed,
                ImportStatus.completed_with_errors,
                ImportStatus.failed,
            }:
                await self._mark_failed(job)
            raise

    async def _create_job(
        self,
        *,
        source_type: SourceType,
        filename: str | None,
        mapping_profile_id: int | None,
        duplicate_strategy: DuplicateStrategy,
    ) -> ImportJob:
        job = ImportJob(
            source_type=source_type,
            filename=filename,
            mapping_profile_id=mapping_profile_id,
            duplicate_strategy=duplicate_strategy,
        )
        self.session.add(job)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise NotFoundError("Mapping profile") from exc
        await self.session.refresh(job)
        return job

    async def _execute(self, job: ImportJob, records: Iterable[Record]) -> ImportJob:
        try:
            mapping = await self._load_mapping(job.mapping_profile_id)
            job.status = ImportStatus.processing
            job.started_at = datetime.now(UTC)
            await self.session.commit()

            iterator = iter(records)
            batch_number = 0
            row_number = 0
            while True:
                raw_batch = list(islice(iterator, self.settings.import_batch_size))
                if not raw_batch:
                    break
                batch_number += 1
                batch = []
                for raw_record in raw_batch:
                    row_number += 1
                    batch.append((row_number, raw_record))
                counters = await self._process_batch(job, batch, mapping)
                await self.session.commit()
                await logger.ainfo(
                    "import_batch_processed",
                    import_id=job.id,
                    batch=batch_number,
                    records=len(batch),
                    **counters,
                )

            job.status = (
                ImportStatus.completed_with_errors if job.failed_records else ImportStatus.completed
            )
            job.finished_at = datetime.now(UTC)
            await self.session.commit()
            await self.session.refresh(job)
            return job
        except Exception:
            await self.session.rollback()
            await self._mark_failed(job)
            raise

    async def _load_mapping(self, profile_id: int | None) -> dict[str, str]:
        if profile_id is None:
            return {}
        from app.models.mapping_profile import MappingProfile

        profile = await self.session.get(MappingProfile, profile_id)
        if profile is None:
            raise NotFoundError("Mapping profile")
        return {str(key): str(value) for key, value in profile.mapping.items()}

    async def _process_batch(
        self,
        job: ImportJob,
        batch: list[tuple[int, Record]],
        mapping: dict[str, str],
    ) -> dict[str, int]:
        counters = {"successful": 0, "updated": 0, "skipped": 0, "failed": 0}
        for row_number, raw in batch:
            try:
                mapped = self.mapping.apply(raw, mapping)
                transformed = self.transformation.transform(mapped)
            except AppError as exc:
                self._add_error(job.id, row_number, raw, None, None, exc.code, exc.message)
                counters["failed"] += 1
                continue

            data, validation_errors = self.validation.validate(transformed)
            if data is None:
                for error in validation_errors:
                    self._add_error(
                        job.id,
                        row_number,
                        raw,
                        error["field"],
                        error["value"],
                        error["code"],
                        error["message"],
                    )
                counters["failed"] += 1
                continue

            existing = await self.customers.find_duplicate(
                email=str(data.email), external_id=data.external_id, phone=data.phone
            )
            decision = self.deduplication.decision(existing, job.duplicate_strategy)
            if decision == "skip":
                counters["skipped"] += 1
                continue
            if decision == "error":
                self._add_error(
                    job.id,
                    row_number,
                    raw,
                    self._duplicate_field(existing, data),
                    str(data.email),
                    "DUPLICATE_ERROR",
                    "Customer already exists",
                )
                counters["failed"] += 1
                continue

            company = await self.companies.get_or_create(
                name=data.company_name,
                external_id=data.company_external_id,
                tax_id=data.tax_id,
            )
            if decision == "update" and existing is not None:
                existing.external_id = data.external_id or existing.external_id
                existing.full_name = data.full_name
                existing.email = str(data.email)
                existing.phone = data.phone or existing.phone
                existing.company = company or existing.company
                await self.session.flush()
                counters["updated"] += 1
            else:
                customer = Customer(
                    external_id=data.external_id,
                    full_name=data.full_name,
                    email=str(data.email),
                    phone=data.phone,
                    company_id=company.id if company else None,
                )
                try:
                    async with self.session.begin_nested():
                        self.session.add(customer)
                        await self.session.flush()
                except IntegrityError:
                    self._add_error(
                        job.id,
                        row_number,
                        raw,
                        None,
                        None,
                        "DUPLICATE_ERROR",
                        "Unique constraint conflict while loading customer",
                    )
                    counters["failed"] += 1
                    continue
                counters["successful"] += 1

        job.total_records += len(batch)
        job.processed_records += len(batch)
        job.successful_records += counters["successful"]
        job.updated_records += counters["updated"]
        job.skipped_records += counters["skipped"]
        job.failed_records += counters["failed"]
        return counters

    def _add_error(
        self,
        job_id: int,
        row_number: int,
        raw_record: Record,
        field: str | None,
        raw_value: Any,
        code: str,
        message: str,
    ) -> None:
        if raw_value is None:
            serialized = None
        elif isinstance(raw_value, str):
            serialized = raw_value
        else:
            serialized = json.dumps(raw_value, ensure_ascii=False, default=str)
        self.session.add(
            ImportError(
                import_job_id=job_id,
                row_number=row_number,
                field=field,
                raw_value=serialized,
                error_code=code,
                message=message,
                raw_record=raw_record,
            )
        )

    def _duplicate_field(self, existing: Customer | None, data: Any) -> str | None:
        if existing is None:
            return None
        if existing.email == str(data.email):
            return "email"
        if data.external_id and existing.external_id == data.external_id:
            return "external_id"
        if data.phone and existing.phone == data.phone:
            return "phone"
        return None

    async def _mark_failed(self, job: ImportJob) -> None:
        job.status = ImportStatus.failed
        job.finished_at = datetime.now(UTC)
        self.session.add(job)
        await self.session.commit()
