from fastapi import APIRouter, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import SessionDep
from app.core.exceptions import AppError, NotFoundError
from app.repositories.mapping import MappingProfileRepository
from app.schemas.mapping import MappingProfileCreate, MappingProfileRead, MappingProfileUpdate

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.get("", response_model=list[MappingProfileRead])
async def list_mappings(session: SessionDep) -> list[MappingProfileRead]:
    profiles = await MappingProfileRepository(session).list()
    return [MappingProfileRead.model_validate(profile) for profile in profiles]


@router.post("", response_model=MappingProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mapping(payload: MappingProfileCreate, session: SessionDep) -> MappingProfileRead:
    try:
        profile = await MappingProfileRepository(session).create(
            name=payload.name, mapping=payload.mapping
        )
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "MAPPING_ERROR", "Mapping profile name already exists", status_code=409
        ) from exc
    return MappingProfileRead.model_validate(profile)


@router.get("/{profile_id}", response_model=MappingProfileRead)
async def get_mapping(profile_id: int, session: SessionDep) -> MappingProfileRead:
    profile = await MappingProfileRepository(session).get(profile_id)
    if profile is None:
        raise NotFoundError("Mapping profile")
    return MappingProfileRead.model_validate(profile)


@router.patch("/{profile_id}", response_model=MappingProfileRead)
async def update_mapping(
    profile_id: int, payload: MappingProfileUpdate, session: SessionDep
) -> MappingProfileRead:
    profile = await MappingProfileRepository(session).get(profile_id)
    if profile is None:
        raise NotFoundError("Mapping profile")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(profile, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "MAPPING_ERROR", "Mapping profile name already exists", status_code=409
        ) from exc
    await session.refresh(profile)
    return MappingProfileRead.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(profile_id: int, session: SessionDep) -> Response:
    profile = await MappingProfileRepository(session).get(profile_id)
    if profile is None:
        raise NotFoundError("Mapping profile")
    await session.delete(profile)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
