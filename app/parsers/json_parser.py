from collections.abc import Iterator, Sequence
from typing import Any

from app.core.exceptions import AppError
from app.parsers.base import BaseParser, Record


class JsonParser(BaseParser):
    def __init__(self, payload: Sequence[Any]) -> None:
        self.payload = payload

    def parse(self) -> Iterator[Record]:
        for index, item in enumerate(self.payload, start=1):
            if not isinstance(item, dict):
                raise AppError(
                    "IMPORT_FILE_INVALID",
                    f"JSON item {index} must be an object",
                    status_code=422,
                )
            yield item
