from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.import_job import ImportJob


class MappingProfile(TimestampMixin, Base):
    __tablename__ = "mapping_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    import_jobs: Mapped[list["ImportJob"]] = relationship(back_populates="mapping_profile")
