import asyncio, asyncpg

async def check():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")
    for table in ["educations", "skills", "certifications", "languages"]:
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = $1 AND is_nullable = 'NO' ORDER BY ordinal_position",
            table
        )
        print(f"{table} NOT NULL: {[r['column_name'] for r in cols]}")
    await conn.close()

asyncio.run(check())
