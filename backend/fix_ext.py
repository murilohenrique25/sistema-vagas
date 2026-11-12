import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    print("Extension uuid-ossp created")
    await conn.close()

asyncio.run(fix())
