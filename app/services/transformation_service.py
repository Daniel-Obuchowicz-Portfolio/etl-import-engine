import re
import unicodedata
from datetime import date, datetime
from typing import Any


class TransformationService:
    def transform(self, record: dict[str, Any]) -> dict[str, Any]:
        transformed = {key: self._clean(value) for key, value in record.items()}
        if transformed.get("email"):
            transformed["email"] = transformed["email"].lower()
        if transformed.get("phone"):
            transformed["phone"] = self._normalize_phone(str(transformed["phone"]))
        if transformed.get("company_name"):
            transformed["company_name"] = self._normalize_company(str(transformed["company_name"]))
        for key in ("birth_date", "established_at"):
            if transformed.get(key):
                transformed[key] = self._parse_date(str(transformed[key]))
        return transformed

    def _clean(self, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        value = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()
        return value or None

    def _normalize_phone(self, value: str) -> str:
        prefix = "+" if value.strip().startswith("+") else ""
        digits = re.sub(r"\D", "", value)
        return prefix + digits

    def _normalize_company(self, value: str) -> str:
        value = re.sub(r"\s*\.\s*", ".", value)
        return re.sub(r"\s+", " ", value).strip()

    def _parse_date(self, value: str) -> date | str:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return value
