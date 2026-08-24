from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, ImportError
from app.parsers.api_parser import ApiParser


@pytest.mark.asyncio
async def test_valid_csv_import_and_report(
    client: httpx.AsyncClient, session: AsyncSession, valid_csv: bytes
) -> None:
    response = await client.post(
        "/api/imports/csv", files={"file": ("customers.csv", valid_csv, "text/csv")}
    )
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "import_id": 1,
        "status": "completed",
        "total": 2,
        "successful": 2,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
    }
    assert await session.scalar(select(func.count(Customer.id))) == 2
    saved = await session.scalar(select(Customer).where(Customer.email == "jan@example.com"))
    assert saved is not None and saved.phone == "+48111222333"
    report = await client.get("/api/imports/1/report")
    assert report.json() == body


@pytest.mark.asyncio
async def test_partially_valid_csv_persists_good_rows(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    content = (
        b"customer_name,email\n"
        b"Good User,good@example.com\n"
        b"Bad User,bad@\n"
        b",missing.name@example.com\n"
    )
    response = await client.post(
        "/api/imports/csv", files={"file": ("mixed.csv", content, "text/csv")}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "completed_with_errors"
    assert response.json()["successful"] == 1
    assert response.json()["failed"] == 2
    assert await session.scalar(select(func.count(Customer.id))) == 1
    assert await session.scalar(select(func.count(ImportError.id))) == 2


@pytest.mark.asyncio
async def test_invalid_csv_file_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/imports/csv", files={"file": ("customers.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMPORT_FILE_INVALID"


@pytest.mark.asyncio
async def test_json_import_uses_same_pipeline(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/imports/json",
        json=[
            {"name": "Jan JSON", "email": " JAN.JSON@EXAMPLE.COM "},
            {"name": "Anna JSON", "email": "anna.json@example.com"},
        ],
    )
    assert response.status_code == 201
    assert response.json()["successful"] == 2


@pytest.mark.asyncio
async def test_mapping_profile_and_preview(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    mapping_response = await client.post(
        "/api/mappings",
        json={
            "name": "Test CRM",
            "mapping": {"contact": "full_name", "e_mail": "email"},
        },
    )
    profile_id = mapping_response.json()["id"]
    preview = await client.post(
        "/api/imports/preview",
        data={"mapping_profile_id": profile_id, "limit": 10},
        files={
            "file": (
                "legacy.csv",
                b"contact,e_mail\n Jan Legacy , JAN.LEGACY@EXAMPLE.COM \n",
                "text/csv",
            )
        },
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["detected_columns"] == ["contact", "e_mail"]
    assert body["preview"][0]["mapped"]["full_name"] == " Jan Legacy "
    assert body["preview"][0]["transformed"]["email"] == "jan.legacy@example.com"
    assert body["preview"][0]["validation"]["valid"] is True
    assert await session.scalar(select(func.count(Customer.id))) == 0


async def insert_customer(session: AsyncSession) -> Customer:
    customer = Customer(
        external_id="EXT-1",
        full_name="Existing",
        email="existing@example.com",
        phone="+48111111111",
    )
    session.add(customer)
    await session.commit()
    return customer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("strategy", "expected"),
    [("skip", (0, 0, 1, 0)), ("error", (0, 0, 0, 1))],
)
async def test_duplicate_skip_and_error(
    client: httpx.AsyncClient,
    session: AsyncSession,
    strategy: str,
    expected: tuple[int, int, int, int],
) -> None:
    await insert_customer(session)
    response = await client.post(
        f"/api/imports/json?duplicate_strategy={strategy}",
        json=[{"name": "Duplicate", "email": "existing@example.com"}],
    )
    body = response.json()
    assert (body["successful"], body["updated"], body["skipped"], body["failed"]) == expected


@pytest.mark.asyncio
async def test_duplicate_update(client: httpx.AsyncClient, session: AsyncSession) -> None:
    existing = await insert_customer(session)
    response = await client.post(
        "/api/imports/json?duplicate_strategy=update",
        json=[{"name": "Updated Name", "email": "existing@example.com"}],
    )
    assert response.json()["updated"] == 1
    await session.refresh(existing)
    assert existing.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_api_import(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(cls: type[ApiParser], url: str, *, timeout: float) -> ApiParser:
        assert timeout == 0.1
        return ApiParser([{"name": "Remote User", "email": "remote@example.com"}])

    monkeypatch.setattr(ApiParser, "fetch", classmethod(fake_fetch))
    response = await client.post(
        "/api/imports/api", json={"url": "http://mock-api:9000/mock/customers"}
    )
    assert response.status_code == 201
    assert response.json()["successful"] == 1


@pytest.mark.asyncio
async def test_history_filter_sort_and_pagination(
    client: httpx.AsyncClient, valid_csv: bytes
) -> None:
    await client.post("/api/imports/csv", files={"file": ("customers.csv", valid_csv, "text/csv")})
    response = await client.get(
        "/api/imports?status=completed&source_type=csv&page=1&page_size=1&sort_by=id&sort_order=desc"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert len(response.json()["items"]) == 1


@pytest.mark.asyncio
async def test_batch_processing_accumulates_all_records(client: httpx.AsyncClient) -> None:
    payload: list[dict[str, Any]] = [
        {"name": f"Batch User {index}", "email": f"batch{index}@example.com"} for index in range(5)
    ]
    response = await client.post("/api/imports/json", json=payload)
    assert response.status_code == 201
    assert response.json()["total"] == 5
    assert response.json()["successful"] == 5


@pytest.mark.asyncio
async def test_mapping_crud(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/api/mappings", json={"name": "CRUD", "mapping": {"name": "full_name"}}
    )
    profile_id = created.json()["id"]
    assert (await client.get("/api/mappings")).json()[0]["name"] == "CRUD"
    updated = await client.patch(f"/api/mappings/{profile_id}", json={"name": "CRUD updated"})
    assert updated.json()["name"] == "CRUD updated"
    assert (await client.delete(f"/api/mappings/{profile_id}")).status_code == 204
    assert (await client.get(f"/api/mappings/{profile_id}")).status_code == 404
