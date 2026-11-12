"""
Seed script to create the payment_settings table.
Run: python seed_payment_settings.py
"""

import asyncio

import asyncpg


DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/sistema_vagas"


async def create_payment_settings_table():
    """Create the payment_settings table if it doesn't exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Ensure uuid-ossp extension exists
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_settings (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                -- PIX settings
                pix_key_type VARCHAR(20),
                pix_key VARCHAR(255),
                pix_beneficiary_name VARCHAR(255),
                -- Gateway settings
                gateway_provider VARCHAR(50),
                gateway_api_key VARCHAR(500),
                gateway_secret_key VARCHAR(500),
                gateway_webhook_url VARCHAR(500),
                -- Bank account
                bank_name VARCHAR(100),
                bank_agency VARCHAR(20),
                bank_account VARCHAR(30),
                bank_account_type VARCHAR(20),
                -- Status
                is_active BOOLEAN DEFAULT true,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_by UUID REFERENCES users(id)
            );
        """)
        print("✓ Table 'payment_settings' created successfully.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_payment_settings_table())
