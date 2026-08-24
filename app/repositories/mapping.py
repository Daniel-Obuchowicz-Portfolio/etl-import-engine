from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mapping_profile import MappingProfile


class MappingProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[MappingProfile]:
        result = await self.session.scalars(select(MappingProfile).order_by(MappingProfile.id))
        return list(result)

    async def get(self, profile_id: int) -> MappingProfile | None:
        return await self.session.get(MappingProfile, profile_id)

    async def create(self, *, name: str, mapping: dict[str, str]) -> MappingProfile:
        profile = MappingProfile(name=name, mapping=mapping)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
