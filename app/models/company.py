from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.customer import Customer


class Company(TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_external_id", "external_id", unique=True),
        Index("ix_companies_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    customers: Mapped[list["Customer"]] = relationship(back_populates="company")
