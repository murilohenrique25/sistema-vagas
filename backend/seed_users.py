"""Seed test users into the database."""
import asyncio
import uuid
import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")

    users = [
        (str(uuid.uuid4()), "admin@sistema-vagas.com", "Administrador", pwd_context.hash("Admin@123"), "admin"),
        (str(uuid.uuid4()), "empresa@teste.com", "Empresa Teste", pwd_context.hash("Empresa@123"), "employer"),
        (str(uuid.uuid4()), "candidato@teste.com", "João Candidato", pwd_context.hash("Candidato@123"), "candidate"),
    ]

    for uid, email, name, pw_hash, role in users:
        await conn.execute("""
            INSERT INTO users (id, email, name, password_hash, role, is_active, failed_login_attempts)
            VALUES ($1, $2, $3, $4, $5, true, 0)
            ON CONFLICT (email) DO NOTHING
        """, uuid.UUID(uid), email, name, pw_hash, role)

    print("Users created:")
    print("  Admin:     admin@sistema-vagas.com / Admin@123")
    print("  Employer:  empresa@teste.com / Empresa@123")
    print("  Candidate: candidato@teste.com / Candidato@123")

    await conn.close()


asyncio.run(seed())
