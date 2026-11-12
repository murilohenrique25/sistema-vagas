"""Seed a company for the employer user."""
import asyncio
import uuid
import asyncpg


async def seed():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")

    # Get employer user ID
    row = await conn.fetchrow("SELECT id FROM users WHERE email = 'empresa@teste.com'")
    if not row:
        print("Employer user not found!")
        await conn.close()
        return

    employer_id = row["id"]
    company_id = uuid.uuid4()

    await conn.execute("""
        INSERT INTO companies (id, owner_id, name, cnpj, description, is_active)
        VALUES ($1, $2, $3, $4, $5, true)
        ON CONFLICT (cnpj) DO NOTHING
    """, company_id, employer_id, "Empresa Teste LTDA", "12.345.678/0001-99", "Empresa de testes para recrutamento")

    print(f"Company created: Empresa Teste LTDA (ID: {company_id})")
    print(f"  Owner: empresa@teste.com (ID: {employer_id})")

    await conn.close()


asyncio.run(seed())
