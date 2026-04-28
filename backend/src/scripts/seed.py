"""Seed script — creates a default admin user for development."""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.config.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed() -> None:
    settings = get_settings()
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy import text

    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count and count > 0:
            print("Seed already applied, skipping.")
            return

        now = datetime.now(timezone.utc)
        user_id = uuid4()
        await session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, created_at, updated_at) "
                "VALUES (:id, :email, :hash, :role, :created_at, :updated_at)"
            ),
            {
                "id": str(user_id),
                "email": "admin@inspections.local",
                "hash": pwd_context.hash("admin1234"),
                "role": "admin",
                "created_at": now,
                "updated_at": now,
            },
        )
        await session.commit()
        print(f"Seeded admin user: admin@inspections.local / admin1234 (id={user_id})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
