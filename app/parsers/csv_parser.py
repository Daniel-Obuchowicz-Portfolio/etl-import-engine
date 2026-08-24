import csv
import io
from collections.abc import Iterator
from typing import BinaryIO

from app.core.exceptions import AppError
from app.parsers.base import BinarySourceParser, Record


class CsvParser(BinarySourceParser):
    def __init__(self, source: BinaryIO, *, max_field_size: int = 1_000_000) -> None:
        super().__init__(source)
        self.max_field_size = max_field_size

    def parse(self) -> Iterator[Record]:
        self.source.seek(0)
        text = io.TextIOWrapper(self.source, encoding="utf-8-sig", newline="")
        try:
            sample = text.read(8192)
            if not sample.strip():
                raise AppError("IMPORT_FILE_INVALID", "Uploaded CSV is empty", status_code=422)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            text.seek(0)
            csv.field_size_limit(self.max_field_size)
            reader = csv.DictReader(text, dialect=dialect)
            if not reader.fieldnames or any(not column.strip() for column in reader.fieldnames):
                raise AppError(
                    "IMPORT_FILE_INVALID", "CSV must contain a valid header row", status_code=422
                )
            for row in reader:
                if None in row:
                    raise AppError(
                        "IMPORT_FILE_INVALID",
                        f"CSV row {reader.line_num} has more values than columns",
                        status_code=422,
                    )
                yield {str(key): value for key, value in row.items()}
        except UnicodeDecodeError as exc:
            raise AppError(
                "IMPORT_FILE_INVALID", "CSV must use UTF-8 encoding", status_code=422
            ) from exc
        except csv.Error as exc:
            raise AppError("IMPORT_FILE_INVALID", f"Invalid CSV: {exc}", status_code=422) from exc
        finally:
            text.detach()
