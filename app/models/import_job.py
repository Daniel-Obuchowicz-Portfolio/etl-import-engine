from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.import_error import ImportError
    from app.models.mapping_profile import MappingProfile


class SourceType(StrEnum):
    csv = "csv"
    json = "json"
    api = "api"


class DuplicateStrategy(StrEnum):
    skip = "skip"
    update = "update"
    error = "error"


class ImportStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    completed_with_errors = "completed_with_errors"
    failed = "failed"


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        Index("ix_import_jobs_status_created", "status", "created_at"),
        Index("ix_import_jobs_source_created", "source_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus), default=ImportStatus.pending, nullable=False
    )
    mapping_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("mapping_profiles.id", ondelete="SET NULL")
    )
    duplicate_strategy: Mapped[DuplicateStrategy] = mapped_column(
        Enum(DuplicateStrategy), default=DuplicateStrategy.skip, nullable=False
    )
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mapping_profile: Mapped["MappingProfile | None"] = relationship(back_populates="import_jobs")
    errors: Mapped[list["ImportError"]] = relationship(
        back_populates="import_job", cascade="all, delete-orphan"
    )
