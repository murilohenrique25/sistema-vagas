"""Seed a fake resume for the candidate user."""
import asyncio
import uuid
from datetime import date
import asyncpg


async def seed():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")

    # Get candidate user ID
    row = await conn.fetchrow("SELECT id FROM users WHERE email = 'candidato@teste.com'")
    if not row:
        print("Candidate user not found!")
        await conn.close()
        return

    candidate_id = row["id"]
    resume_id = uuid.uuid4()

    # Check if already exists - delete and recreate
    existing = await conn.fetchrow("SELECT id FROM resumes WHERE user_id = $1", candidate_id)
    if existing:
        rid = existing['id']
        await conn.execute("DELETE FROM languages WHERE resume_id = $1", rid)
        await conn.execute("DELETE FROM certifications WHERE resume_id = $1", rid)
        await conn.execute("DELETE FROM skills WHERE resume_id = $1", rid)
        await conn.execute("DELETE FROM educations WHERE resume_id = $1", rid)
        await conn.execute("DELETE FROM experiences WHERE resume_id = $1", rid)
        await conn.execute("DELETE FROM resumes WHERE id = $1", rid)
        print(f"Deleted old resume {rid}")

    await conn.execute("""
        INSERT INTO resumes (id, user_id, full_name, contact_email, phone, location)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, resume_id, candidate_id, "João Candidato Silva", "candidato@teste.com", "(11) 99999-8888", "São Paulo, SP")

    # Experiences
    experiences = [
        (uuid.uuid4(), resume_id, "Tech Solutions LTDA", "Desenvolvedor Full Stack", date(2022, 1, 15), date(2025, 6, 1), "Desenvolvimento de aplicações web com React e Node.js. Manutenção de APIs REST.", 1),
        (uuid.uuid4(), resume_id, "StartupXYZ", "Desenvolvedor Junior", date(2020, 3, 1), date(2021, 12, 30), "Desenvolvimento frontend com Vue.js. Integração com APIs de pagamento.", 2),
        (uuid.uuid4(), resume_id, "Restaurante Sabor & Arte", "Chapeiro / Cozinheiro", date(2018, 6, 1), date(2020, 2, 28), "Preparo de lanches e pratos na chapa. Atendimento ao cliente. Controle de estoque.", 3),
    ]
    for exp in experiences:
        await conn.execute("""
            INSERT INTO experiences (id, resume_id, company, position, start_date, end_date, description, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, *exp)

    # Education
    educations = [
        (uuid.uuid4(), resume_id, "Universidade Federal de São Paulo", "Ciência da Computação", "bachelor", date(2016, 2, 1), date(2020, 12, 15), 1),
        (uuid.uuid4(), resume_id, "Senac SP", "Técnico em Informática", "technical", date(2014, 2, 1), date(2015, 12, 15), 2),
    ]
    for edu in educations:
        await conn.execute("""
            INSERT INTO educations (id, resume_id, institution, course, degree, start_date, end_date, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, *edu)

    # Skills
    skills = [
        (uuid.uuid4(), resume_id, "JavaScript", "advanced"),
        (uuid.uuid4(), resume_id, "TypeScript", "advanced"),
        (uuid.uuid4(), resume_id, "React", "advanced"),
        (uuid.uuid4(), resume_id, "Node.js", "intermediate"),
        (uuid.uuid4(), resume_id, "Python", "intermediate"),
        (uuid.uuid4(), resume_id, "PostgreSQL", "intermediate"),
        (uuid.uuid4(), resume_id, "Docker", "beginner"),
        (uuid.uuid4(), resume_id, "Git", "advanced"),
    ]
    for skill in skills:
        await conn.execute("""
            INSERT INTO skills (id, resume_id, name, proficiency)
            VALUES ($1, $2, $3, $4)
        """, *skill)

    # Certifications
    certs = [
        (uuid.uuid4(), resume_id, "AWS Cloud Practitioner", "Amazon", date(2023, 6, 15)),
        (uuid.uuid4(), resume_id, "React Professional", "Meta", date(2022, 9, 1)),
    ]
    for cert in certs:
        await conn.execute("""
            INSERT INTO certifications (id, resume_id, name, issuer, obtained_at)
            VALUES ($1, $2, $3, $4, $5)
        """, *cert)

    # Languages
    langs = [
        (uuid.uuid4(), resume_id, "Português", "native"),
        (uuid.uuid4(), resume_id, "Inglês", "advanced"),
        (uuid.uuid4(), resume_id, "Espanhol", "intermediate"),
    ]
    for lang in langs:
        await conn.execute("""
            INSERT INTO languages (id, resume_id, language, fluency)
            VALUES ($1, $2, $3, $4)
        """, *lang)

    print(f"Resume created for candidato@teste.com (ID: {resume_id})")
    print(f"  - 3 experiences")
    print(f"  - 2 educations")
    print(f"  - 8 skills")
    print(f"  - 2 certifications")
    print(f"  - 3 languages")

    await conn.close()


asyncio.run(seed())
