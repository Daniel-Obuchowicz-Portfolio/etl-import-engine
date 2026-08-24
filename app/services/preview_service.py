from collections.abc import Iterable
from itertools import islice
from typing import Any

from app.parsers.base import Record
from app.schemas.imports import PreviewRecord, PreviewResponse, ValidationPreview
from app.services.mapping_service import MappingService
from app.services.transformation_service import TransformationService
from app.services.validation_service import ValidationService


class PreviewService:
    def __init__(self) -> None:
        self.mapping = MappingService()
        self.transformation = TransformationService()
        self.validation = ValidationService()

    def run(
        self,
        records: Iterable[Record],
        *,
        mapping: dict[str, str],
        limit: int = 10,
    ) -> PreviewResponse:
        preview: list[PreviewRecord] = []
        detected_columns: list[str] = []
        for raw in islice(records, limit):
            if not detected_columns:
                detected_columns = list(raw.keys())
            mapped = self.mapping.apply(raw, mapping)
            transformed = self.transformation.transform(mapped)
            _, errors = self.validation.validate(transformed)
            preview.append(
                PreviewRecord(
                    raw=raw,
                    mapped=mapped,
                    transformed=self._serialize(transformed),
                    validation=ValidationPreview(valid=not errors, errors=errors),
                )
            )
        return PreviewResponse(detected_columns=detected_columns, preview=preview)

    def _serialize(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in record.items()
        }
