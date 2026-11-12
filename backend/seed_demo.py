"""Seed demo data: 3 employers with companies, 2 candidates with resumes, 10 jobs."""
import asyncio
import uuid
from datetime import date, timedelta
from decimal import Decimal
import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DB = "postgresql://postgres:postgres@localhost:5432/sistema_vagas"


async def seed():
    conn = await asyncpg.connect(DB)

    # === 3 Employers ===
    employers = [
        {"id": uuid.uuid4(), "email": "rh@techcorp.com", "name": "Maria Silva", "pw": "Empresa@123", "company": "TechCorp Brasil", "cnpj": "11.222.333/0001-01", "desc": "Empresa líder em desenvolvimento de software"},
        {"id": uuid.uuid4(), "email": "contato@fooddelivery.com", "name": "Carlos Oliveira", "pw": "Empresa@123", "company": "Food Delivery SA", "cnpj": "22.333.444/0001-02", "desc": "Plataforma de entregas de comida"},
        {"id": uuid.uuid4(), "email": "vagas@construtora.com", "name": "Ana Souza", "pw": "Empresa@123", "company": "Construtora Horizonte", "cnpj": "33.444.555/0001-03", "desc": "Construtora com 20 anos de mercado"},
    ]

    companies = []
    for emp in employers:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", emp["email"])
        if existing:
            emp["id"] = existing["id"]
        else:
            await conn.execute(
                "INSERT INTO users (id, email, name, password_hash, role, is_active, failed_login_attempts) VALUES ($1,$2,$3,$4,'employer',true,0)",
                emp["id"], emp["email"], emp["name"], pwd_context.hash(emp["pw"])
            )
        cid = uuid.uuid4()
        existing_comp = await conn.fetchrow("SELECT id FROM companies WHERE cnpj = $1", emp["cnpj"])
        if existing_comp:
            cid = existing_comp["id"]
        else:
            await conn.execute(
                "INSERT INTO companies (id, owner_id, name, cnpj, description, is_active) VALUES ($1,$2,$3,$4,$5,true)",
                cid, emp["id"], emp["company"], emp["cnpj"], emp["desc"]
            )
        companies.append({"id": cid, "owner": emp["id"], "name": emp["company"]})

    print(f"✓ 3 empregadores criados")

    # === 2 Candidates ===
    candidates = [
        {"id": uuid.uuid4(), "email": "pedro@email.com", "name": "Pedro Santos", "pw": "Candidato@123"},
        {"id": uuid.uuid4(), "email": "julia@email.com", "name": "Júlia Ferreira", "pw": "Candidato@123"},
    ]

    for cand in candidates:
        # Check if user already exists
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", cand["email"])
        if existing:
            cand["id"] = existing["id"]
        else:
            await conn.execute(
                "INSERT INTO users (id, email, name, password_hash, role, is_active, failed_login_attempts) VALUES ($1,$2,$3,$4,'candidate',true,0)",
                cand["id"], cand["email"], cand["name"], pwd_context.hash(cand["pw"])
            )
        # Check if resume exists
        existing_resume = await conn.fetchrow("SELECT id FROM resumes WHERE user_id = $1", cand["id"])
        if existing_resume:
            continue
        # Create resume
        rid = uuid.uuid4()
        await conn.execute(
            "INSERT INTO resumes (id, user_id, full_name, contact_email, phone, location) VALUES ($1,$2,$3,$4,$5,$6)",
            rid, cand["id"], cand["name"], cand["email"], "(62) 99999-0000", "Goiânia, GO"
        )
        await conn.execute(
            "INSERT INTO experiences (id, resume_id, company, position, start_date, end_date, description, sort_order) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            uuid.uuid4(), rid, "Empresa Anterior", "Analista", date(2021,1,1), date(2024,12,1), "Experiência diversa na área", 1
        )
        await conn.execute(
            "INSERT INTO skills (id, resume_id, name, proficiency) VALUES ($1,$2,$3,$4)",
            uuid.uuid4(), rid, "Comunicação", "advanced"
        )
        await conn.execute(
            "INSERT INTO skills (id, resume_id, name, proficiency) VALUES ($1,$2,$3,$4)",
            uuid.uuid4(), rid, "Trabalho em equipe", "intermediate"
        )

    print(f"✓ 2 candidatos criados com currículo")

    # === 10 Jobs ===
    jobs_data = [
        {"title": "Desenvolvedor Python Senior", "mod": "remote", "loc": "São Paulo, SP", "ct": "clt", "smin": 12000, "smax": 18000, "resp": "Desenvolver APIs REST, arquitetura de microsserviços", "req": "Python, FastAPI, PostgreSQL, Docker, 5+ anos", "opt": "AWS, Kubernetes", "ben": "VR, VT, Plano de saúde, Gympass", "comp": 0},
        {"title": "Atendente de Loja", "mod": "onsite", "loc": "Goiânia, GO", "ct": "clt", "smin": 1500, "smax": 2000, "resp": "Atender clientes, organizar prateleiras, operar caixa", "req": "Ensino médio completo, boa comunicação", "opt": "Experiência em varejo", "ben": "VT, VR, Comissão", "comp": 1},
        {"title": "Designer UX/UI", "mod": "hybrid", "loc": "Belo Horizonte, MG", "ct": "pj", "smin": 8000, "smax": 14000, "resp": "Criar interfaces, protótipos, pesquisas com usuários", "req": "Figma, Adobe XD, Design Thinking", "opt": "HTML, CSS, conhecimento em React", "ben": "Horário flexível, Home office 3x/semana", "comp": 0},
        {"title": "Pedreiro Profissional", "mod": "onsite", "loc": "Aparecida de Goiânia, GO", "ct": "temporary", "smin": 2500, "smax": 3500, "resp": "Construção de alvenaria, reboco, assentamento", "req": "Experiência comprovada em construção civil", "opt": "NR-35, trabalho em altura", "ben": "Insalubridade, VT", "comp": 2},
        {"title": "Analista de Marketing Digital", "mod": "remote", "loc": "Qualquer lugar do Brasil", "ct": "clt", "smin": 5000, "smax": 8000, "resp": "Gerenciar campanhas, SEO, redes sociais, Google Ads", "req": "Marketing digital, Google Analytics, Meta Ads", "opt": "Certificação Google, experiência com e-commerce", "ben": "VR, Plano dental, Day off aniversário", "comp": 0},
        {"title": "Entregador de Moto", "mod": "onsite", "loc": "Goiânia, GO", "ct": "pj", "smin": 2000, "smax": 4000, "resp": "Realizar entregas em tempo hábil, manter veículo", "req": "CNH A/B, moto própria, celular com internet", "opt": "Experiência com apps de delivery", "ben": "Comissão por entrega, flexibilidade de horário", "comp": 1},
        {"title": "Gerente de Projetos", "mod": "hybrid", "loc": "São Paulo, SP", "ct": "clt", "smin": 15000, "smax": 22000, "resp": "Coordenar equipes, gerenciar prazos e orçamento", "req": "PMP ou Scrum Master, 8+ anos de experiência", "opt": "MBA, experiência em TI", "ben": "PLR, Previdência privada, Carro corporativo", "comp": 0},
        {"title": "Cozinheiro(a)", "mod": "onsite", "loc": "Anápolis, GO", "ct": "clt", "smin": 1800, "smax": 2500, "resp": "Preparar pratos do cardápio, manter higiene da cozinha", "req": "Experiência em cozinha profissional, curso de manipulação de alimentos", "opt": "Experiência com cozinha italiana", "ben": "Alimentação no local, VT, Gorjeta", "comp": 2},
        {"title": "Desenvolvedor React Frontend", "mod": "remote", "loc": "Rio de Janeiro, RJ", "ct": "pj", "smin": 9000, "smax": 15000, "resp": "Desenvolver interfaces web responsivas e acessíveis", "req": "React, TypeScript, CSS-in-JS, 3+ anos", "opt": "Next.js, Testes automatizados, Design System", "ben": "Horário flexível, Budget para cursos", "comp": 0},
        {"title": "Auxiliar Administrativo", "mod": "onsite", "loc": "Goiânia, GO", "ct": "internship", "smin": 800, "smax": 1200, "resp": "Apoio em rotinas administrativas, atendimento telefônico", "req": "Cursando Administração ou áreas afins", "opt": "Conhecimento em Excel", "ben": "VT, Bolsa auxílio, Possibilidade de efetivação", "comp": 1},
    ]

    for i, job in enumerate(jobs_data):
        comp = companies[job["comp"]]
        deadline = date.today() + timedelta(days=30 + i*10)
        await conn.execute("""
            INSERT INTO jobs (id, company_id, title, modality, location, contract_type, salary_min, salary_max, responsibilities, required_skills, optional_skills, benefits, status, deadline)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'active', $13)
        """,
            uuid.uuid4(), comp["id"], job["title"], job["mod"], job["loc"], job["ct"],
            Decimal(str(job["smin"])), Decimal(str(job["smax"])),
            job["resp"], job["req"], job["opt"], job["ben"], deadline
        )

    print(f"✓ 10 vagas criadas")

    # Summary
    print("\n=== Resumo ===")
    print("\nEmpregadores:")
    for emp in employers:
        print(f"  {emp['name']} ({emp['company']}): {emp['email']} / {emp['pw']}")
    print("\nCandidatos:")
    for cand in candidates:
        print(f"  {cand['name']}: {cand['email']} / {cand['pw']}")
    print("\n10 vagas ativas criadas com prazos variados.")

    await conn.close()


asyncio.run(seed())
