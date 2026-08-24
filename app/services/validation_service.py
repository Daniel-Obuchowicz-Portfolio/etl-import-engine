from typing import Any

from pydantic import ValidationError

from app.schemas.customer import CustomerInput


class ValidationService:
    def validate(self, record: dict[str, Any]) -> tuple[CustomerInput | None, list[dict[str, Any]]]:
        try:
            return CustomerInput.model_validate(record), []
        except ValidationError as exc:
            errors = []
            for item in exc.errors(include_url=False):
                field = ".".join(str(part) for part in item["loc"])
                errors.append(
                    {
                        "field": field or None,
                        "value": record.get(field),
                        "message": item["msg"],
                        "code": "VALIDATION_ERROR",
                    }
                )
            return None, errors
