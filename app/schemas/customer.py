import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    external_id: str | None = Field(default=None, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    company_name: str | None = Field(default=None, max_length=255)
    company_external_id: str | None = Field(default=None, max_length=100)
    tax_id: str | None = Field(default=None, max_length=50)
    birth_date: date | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"\+?[1-9]\d{6,14}", value):
            raise ValueError("Invalid phone number")
        return value
