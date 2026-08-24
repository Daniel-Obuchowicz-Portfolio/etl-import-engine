from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_error import ImportError
from app.models.import_job import ImportJob, ImportStatus, SourceType


class ImportRepository:
    SORT_FIELDS = {
        "id": ImportJob.id,
        "created_at": ImportJob.created_at,
        "finished_at": ImportJob.finished_at,
        "status": ImportJob.status,
        "total_records": ImportJob.total_records,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _filters(
        self, statement: Select, status: ImportStatus | None, source_type: SourceType | None
    ) -> Select:
        if status:
            statement = statement.where(ImportJob.status == status)
        if source_type:
            statement = statement.where(ImportJob.source_type == source_type)
        return statement

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        status: ImportStatus | None,
        source_type: SourceType | None,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ImportJob], int]:
        sort_column = self.SORT_FIELDS[sort_by]
        ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        query = self._filters(select(ImportJob), status, source_type)
        query = query.order_by(ordering).offset((page - 1) * page_size).limit(page_size)
        count_query = self._filters(select(func.count(ImportJob.id)), status, source_type)
        items = list(await self.session.scalars(query))
        total = int(await self.session.scalar(count_query) or 0)
        return items, total

    async def errors(
        self, import_id: int, *, page: int, page_size: int
    ) -> tuple[list[ImportError], int]:
        base = ImportError.import_job_id == import_id
        query = (
            select(ImportError)
            .where(base)
            .order_by(ImportError.row_number, ImportError.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(await self.session.scalars(query))
        total = int(await self.session.scalar(select(func.count(ImportError.id)).where(base)) or 0)
        return items, total
