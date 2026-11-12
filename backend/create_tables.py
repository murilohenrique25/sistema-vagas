"""Create all tables using SQLAlchemy metadata.create_all (synchronous wrapper)."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models to register them with Base
from app.core.database import Base
from app.models import user, company, job, resume, application, token, subscription, notification, job_highlight, ai_analysis, audit_log


async def create_all():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_vagas",
        echo=True,
    )

    async with engine.begin() as conn:
        # Create uuid-ossp extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Drop all tables with CASCADE
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("\nAll tables created successfully from SQLAlchemy models!")


asyncio.run(create_all())
