from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_TARGET_FIELDS = {
    "external_id",
    "full_name",
    "email",
    "phone",
    "company_name",
    "company_external_id",
    "tax_id",
    "birth_date",
}


class MappingProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    mapping: dict[str, str]

    @field_validator("mapping")
    @classmethod
    def validate_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("Mapping cannot be empty")
        unknown = set(value.values()) - ALLOWED_TARGET_FIELDS
        if unknown:
            raise ValueError(f"Unsupported target fields: {', '.join(sorted(unknown))}")
        return value


class MappingProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    mapping: dict[str, str] | None = None

    @field_validator("mapping")
    @classmethod
    def validate_mapping(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        return MappingProfileCreate(name="validation", mapping=value).mapping


class MappingProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    mapping: dict[str, str]
    created_at: datetime
    updated_at: datetime
