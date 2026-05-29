"""Seed script — creates a default admin user for development."""
import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_ADMIN_EMAIL = "admin@inspections.local"


async def seed() -> None:
    settings = get_settings()
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD") or "change-me"

    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count and count > 0:
            print("Seed already applied, skipping.")
            return

        now = datetime.now(UTC)
        user_id = uuid4()
        await session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, created_at, updated_at) "
                "VALUES (:id, :email, :hash, :role, :created_at, :updated_at)"
            ),
            {
                "id": str(user_id),
                "email": DEFAULT_ADMIN_EMAIL,
                "hash": pwd_context.hash(admin_password),
                "role": "admin",
                "created_at": now,
                "updated_at": now,
            },
        )
        await session.commit()
        print(f"Seeded development admin user: {DEFAULT_ADMIN_EMAIL} (id={user_id})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
