from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self,
        *,
        name: str | None,
        external_id: str | None = None,
        tax_id: str | None = None,
    ) -> Company | None:
        if not name:
            return None
        conditions = [Company.name == name]
        if external_id:
            conditions.append(Company.external_id == external_id)
        if tax_id:
            conditions.append(Company.tax_id == tax_id)
        company = await self.session.scalar(select(Company).where(or_(*conditions)).limit(1))
        if company:
            return company
        company = Company(name=name, external_id=external_id, tax_id=tax_id)
        self.session.add(company)
        await self.session.flush()
        return company
