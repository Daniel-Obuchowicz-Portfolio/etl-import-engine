import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.database import SessionFactory
from app.models import Company, Customer, ImportJob, ImportStatus, MappingProfile, SourceType


async def seed() -> None:
    async with SessionFactory() as session:
        if await session.scalar(select(func.count(Customer.id))):
            print("Seed skipped: customers already exist")
            return
        companies = [
            Company(
                external_id=f"COMP-{i:03d}", name=f"Portfolio Company {i}", tax_id=f"PL{i:010d}"
            )
            for i in range(1, 21)
        ]
        session.add_all(companies)
        await session.flush()
        session.add_all(
            Customer(
                external_id=f"CUST-{i:04d}",
                full_name=f"Seed Customer {i}",
                email=f"seed.customer{i}@example.com",
                phone=f"+48200{i:06d}",
                company=companies[(i - 1) % len(companies)],
            )
            for i in range(1, 201)
        )
        session.add_all(
            [
                MappingProfile(
                    name="Legacy CRM customers",
                    mapping={
                        "crm_id": "external_id",
                        "customer_name": "full_name",
                        "mail_address": "email",
                        "telephone": "phone",
                        "company": "company_name",
                    },
                ),
                MappingProfile(
                    name="Simple JSON",
                    mapping={"name": "full_name", "email": "email", "phone": "phone"},
                ),
                MappingProfile(
                    name="Partner export",
                    mapping={
                        "contact": "full_name",
                        "e_mail": "email",
                        "organisation": "company_name",
                    },
                ),
            ]
        )
        now = datetime.now(UTC)
        for i in range(1, 6):
            session.add(
                ImportJob(
                    source_type=SourceType.csv if i % 2 else SourceType.json,
                    filename=f"historical-{i}.csv",
                    status=ImportStatus.completed,
                    total_records=i * 20,
                    processed_records=i * 20,
                    successful_records=i * 20,
                    started_at=now - timedelta(days=i, minutes=2),
                    finished_at=now - timedelta(days=i),
                )
            )
        await session.commit()
        print("Seeded 20 companies, 200 customers, 3 mappings and 5 import jobs")


if __name__ == "__main__":
    asyncio.run(seed())
