from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_duplicate(
        self, *, email: str, external_id: str | None, phone: str | None
    ) -> Customer | None:
        conditions = [Customer.email == email]
        if external_id:
            conditions.append(Customer.external_id == external_id)
        if phone:
            conditions.append(Customer.phone == phone)
        return await self.session.scalar(select(Customer).where(or_(*conditions)).limit(1))
