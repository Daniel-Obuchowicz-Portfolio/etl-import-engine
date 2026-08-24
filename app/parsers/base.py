from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any, BinaryIO

Record = dict[str, Any]


class BaseParser(ABC):
    @abstractmethod
    def parse(self) -> Iterator[Record]:
        """Yield source records without loading the complete source into memory."""


class BinarySourceParser(BaseParser, ABC):
    def __init__(self, source: BinaryIO) -> None:
        self.source = source
