from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.import_job import ImportJob


class ImportError(Base):
    __tablename__ = "import_errors"
    __table_args__ = (Index("ix_import_errors_job_row", "import_job_id", "row_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    import_job_id: Mapped[int] = mapped_column(
        ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    field: Mapped[str | None] = mapped_column(String(100))
    raw_value: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_record: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    import_job: Mapped["ImportJob"] = relationship(back_populates="errors")
