"""Script to recreate the database and create tables directly (for PG 10 compatibility)."""
import asyncio
import asyncpg


async def setup():
    # Connect to postgres default db
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/postgres")

    # Terminate other connections
    await conn.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = 'sistema_vagas' AND pid <> pg_backend_pid()
    """)

    # Recreate database
    await conn.execute("DROP DATABASE IF EXISTS sistema_vagas")
    await conn.execute("CREATE DATABASE sistema_vagas")
    await conn.close()
    print("Database recreated")

    # Connect to the new database and create enum types + tables
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/sistema_vagas")

    # Enable uuid-ossp extension
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    print("uuid-ossp extension enabled")

    # Create enum types
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('candidate', 'employer', 'admin');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE jobmodality AS ENUM ('remote', 'hybrid', 'onsite');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE contracttype AS ENUM ('clt', 'pj', 'temporary', 'internship');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE jobstatus AS ENUM ('draft', 'active', 'inactive', 'closed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE applicationstatus AS ENUM ('received', 'in_review', 'interview', 'technical_test', 'proposal', 'hired', 'rejected', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE tokentransactiontype AS ENUM ('credit', 'debit', 'refund');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionplan AS ENUM ('free', 'professional', 'enterprise');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE subscriptionstatus AS ENUM ('active', 'suspended', 'cancelled', 'expired');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod AS ENUM ('pix', 'credit_card');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentstatus AS ENUM ('pending', 'confirmed', 'failed', 'expired', 'cancelled');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE notificationchannel AS ENUM ('platform', 'email', 'both');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE deliverystatus AS ENUM ('pending', 'sent', 'failed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE aianalysistype AS ENUM ('candidate_analysis', 'job_matching');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE aianalysisstatus AS ENUM ('pending', 'completed', 'failed', 'refunded');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE educationdegree AS ENUM ('high_school', 'technical', 'bachelor', 'postgraduate', 'master', 'doctorate');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE proficiencylevel AS ENUM ('beginner', 'intermediate', 'advanced', 'expert');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE languagefluency AS ENUM ('basic', 'intermediate', 'advanced', 'fluent', 'native');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    print("Enum types created")

    # Create tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) NOT NULL UNIQUE,
            name VARCHAR(200) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role userrole NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            owner_id UUID NOT NULL REFERENCES users(id),
            name VARCHAR(255) NOT NULL,
            cnpj VARCHAR(18) NOT NULL UNIQUE,
            description TEXT,
            website VARCHAR(500),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            company_id UUID NOT NULL REFERENCES companies(id),
            title VARCHAR(255) NOT NULL,
            modality jobmodality NOT NULL,
            location VARCHAR(255),
            responsibilities TEXT,
            required_skills TEXT,
            optional_skills TEXT,
            benefits TEXT,
            contract_type contracttype NOT NULL,
            salary_min NUMERIC(12, 2),
            salary_max NUMERIC(12, 2),
            status jobstatus NOT NULL DEFAULT 'active',
            deadline DATE,
            search_vector TSVECTOR,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL UNIQUE REFERENCES users(id),
            full_name VARCHAR(200),
            contact_email VARCHAR(255),
            phone VARCHAR(20),
            location VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            company VARCHAR(255),
            position VARCHAR(255),
            start_date DATE,
            end_date DATE,
            description TEXT
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS educations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            institution VARCHAR(255),
            course VARCHAR(255),
            degree educationdegree,
            start_date DATE,
            end_date DATE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            proficiency proficiencylevel
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            issuer VARCHAR(255),
            obtained_at DATE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS languages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
            language VARCHAR(100) NOT NULL,
            fluency languagefluency
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            job_id UUID NOT NULL REFERENCES jobs(id),
            candidate_id UUID NOT NULL REFERENCES users(id),
            status applicationstatus NOT NULL DEFAULT 'received',
            applied_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(job_id, candidate_id)
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS application_status_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            application_id UUID NOT NULL REFERENCES applications(id),
            previous_status applicationstatus,
            new_status applicationstatus NOT NULL,
            changed_by UUID REFERENCES users(id),
            changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS token_transactions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL,
            type tokentransactiontype NOT NULL,
            reason TEXT,
            reference_id UUID,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id),
            plan subscriptionplan NOT NULL DEFAULT 'free',
            status subscriptionstatus NOT NULL DEFAULT 'active',
            current_period_start DATE,
            current_period_end DATE,
            retry_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id),
            amount NUMERIC(12, 2) NOT NULL,
            method paymentmethod NOT NULL,
            status paymentstatus NOT NULL DEFAULT 'pending',
            external_reference VARCHAR(255),
            pix_code TEXT,
            expires_at TIMESTAMP WITH TIME ZONE,
            confirmed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id),
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            channel notificationchannel NOT NULL DEFAULT 'both',
            is_read BOOLEAN NOT NULL DEFAULT false,
            delivery_attempts INTEGER DEFAULT 0,
            delivery_status deliverystatus NOT NULL DEFAULT 'pending',
            sent_at TIMESTAMP WITH TIME ZONE,
            read_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS job_highlights (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            job_id UUID NOT NULL REFERENCES jobs(id),
            activated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_analyses (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            requester_id UUID NOT NULL REFERENCES users(id),
            job_id UUID REFERENCES jobs(id),
            type aianalysistype NOT NULL,
            result JSONB,
            tokens_consumed INTEGER DEFAULT 0,
            status aianalysisstatus NOT NULL DEFAULT 'pending',
            completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS token_packages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            token_amount INTEGER NOT NULL,
            price NUMERIC(12, 2) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS token_configs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            feature_key VARCHAR(100) NOT NULL UNIQUE,
            feature_name VARCHAR(255) NOT NULL,
            tokens_required INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN NOT NULL DEFAULT true,
            updated_at TIMESTAMP WITH TIME ZONE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            admin_id UUID NOT NULL REFERENCES users(id),
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id UUID NOT NULL,
            previous_value JSONB,
            new_value JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    """)

    # Create indexes
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_token_transactions_user ON token_transactions(user_id)")

    print("All tables and indexes created")

    # Create a test admin user
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin_hash = pwd_context.hash("Admin@123")

    await conn.execute("""
        INSERT INTO users (email, name, password_hash, role, is_active)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO NOTHING
    """, "admin@sistema-vagas.com", "Administrador", admin_hash, "admin", True)

    # Create employer user
    employer_hash = pwd_context.hash("Empresa@123")
    await conn.execute("""
        INSERT INTO users (email, name, password_hash, role, is_active)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO NOTHING
    """, "empresa@teste.com", "Empresa Teste", employer_hash, "employer", True)

    # Create candidate user
    candidate_hash = pwd_context.hash("Candidato@123")
    await conn.execute("""
        INSERT INTO users (email, name, password_hash, role, is_active)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO NOTHING
    """, "candidato@teste.com", "João Candidato", candidate_hash, "candidate", True)

    print("Test users created:")
    print("  Admin: admin@sistema-vagas.com / Admin@123")
    print("  Employer: empresa@teste.com / Empresa@123")
    print("  Candidate: candidato@teste.com / Candidato@123")

    await conn.close()
    print("\nSetup complete!")


asyncio.run(setup())
