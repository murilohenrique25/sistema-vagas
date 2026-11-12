"""Add missing columns to the database for PG 10 compatibility."""
import asyncio
import asyncpg


async def fix():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")

    # Add missing columns to users table
    try:
        await conn.execute("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)")
    except asyncpg.exceptions.DuplicateColumnError:
        pass

    try:
        await conn.execute("ALTER TABLE users ADD COLUMN oauth_id VARCHAR(255)")
    except asyncpg.exceptions.DuplicateColumnError:
        pass

    print("Added oauth_provider and oauth_id columns to users table")
    await conn.close()


asyncio.run(fix())
