from typing import Any

from app.core.exceptions import MappingError

DEFAULT_MAPPING = {
    "name": "full_name",
    "customer_name": "full_name",
    "mail": "email",
    "mail_address": "email",
    "telephone": "phone",
    "company": "company_name",
}


class MappingService:
    def apply(
        self, record: dict[str, Any], mapping: dict[str, str] | None = None
    ) -> dict[str, Any]:
        mapping = {**DEFAULT_MAPPING, **(mapping or {})}
        output: dict[str, Any] = {}
        for source_field, value in record.items():
            target_field = mapping.get(source_field, source_field)
            if target_field in output and output[target_field] not in (None, ""):
                raise MappingError(f"Multiple populated source fields map to '{target_field}'")
            output[target_field] = value
        return output
