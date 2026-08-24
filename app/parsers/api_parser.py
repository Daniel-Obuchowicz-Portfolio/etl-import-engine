from collections.abc import Iterator
from typing import Any

import httpx

from app.core.exceptions import ImportSourceError
from app.parsers.base import BaseParser, Record
from app.parsers.json_parser import JsonParser


class ApiParser(BaseParser):
    def __init__(self, payload: list[Any]) -> None:
        self.payload = payload

    @classmethod
    async def fetch(cls, url: str, *, timeout: float) -> "ApiParser":
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ImportSourceError("External API request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise ImportSourceError(
                f"External API returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise ImportSourceError(f"Could not reach external API: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise ImportSourceError("External API returned invalid JSON") from exc
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            payload = payload["items"]
        if not isinstance(payload, list):
            raise ImportSourceError("External API response must be a JSON array")
        return cls(payload)

    def parse(self) -> Iterator[Record]:
        yield from JsonParser(self.payload).parse()
