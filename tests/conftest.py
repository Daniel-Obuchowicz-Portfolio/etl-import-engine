from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    def override_settings() -> Settings:
        return Settings(
            database_url="sqlite+aiosqlite://",
            import_batch_size=2,
            api_request_timeout_seconds=0.1,
        )

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = override_settings
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def valid_csv() -> bytes:
    return (
        b"customer_name,email,phone,company\n"
        b" Jan Kowalski , JAN@EXAMPLE.COM ,+48 111 222 333, Example  Sp. z o.o. \n"
        b"Anna Nowak,anna@example.com,+48444555666,Demo SA\n"
    )
