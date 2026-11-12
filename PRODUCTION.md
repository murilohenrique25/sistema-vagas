# Produção

## Pré-requisitos

- Docker Engine com Compose v2
- domínio com HTTPS terminado por um proxy/load balancer
- PostgreSQL e Redis com backup (ou os volumes do compose com rotina externa de backup)
- credenciais OpenAI e Mercado Pago

## Configuração

Crie um arquivo `.env` na raiz (não versionado):

```env
POSTGRES_PASSWORD=use-uma-senha-forte
REDIS_PASSWORD=use-uma-senha-forte
JWT_SECRET_KEY=CONFIGURE_NO_AMBIENTE
INTERNAL_SERVICE_TOKEN=gere-outro-segredo-de-32-caracteres
PUBLIC_URL=https://seu-dominio.com.br
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
MERCADOPAGO_ACCESS_TOKEN=...
MERCADOPAGO_WEBHOOK_SECRET=...
MERCADOPAGO_PAYER_EMAIL=financeiro@seu-dominio.com.br
```

Configure no Mercado Pago o webhook:

`https://seu-dominio.com.br/v1/payments/webhooks/mercadopago`

O backend valida `x-signature`, consulta o pagamento no provedor e somente então credita a carteira. Sandbox é recusado quando `ENVIRONMENT=production`.

## Subida

```bash
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

O backend executa `python -m alembic upgrade head` antes de iniciar. Verifique:

```bash
curl -f https://seu-dominio.com.br/health
curl -f https://seu-dominio.com.br/ready
```

## Antes de receber pagamentos

1. Execute uma recarga PIX de valor baixo com credenciais de produção.
2. Confirme que saldo não é creditado antes da aprovação no Mercado Pago.
3. Reenvie o webhook e confirme que não ocorre crédito duplicado.
4. Publique uma vaga com saldo zerado e confirme que nenhum débito foi criado.
5. Execute cada análise e valide débito de R$ 5,00.
6. Configure alertas para respostas 5xx, falha do `/ready`, saldo/conciliação e latência da IA.

Backups, TLS e retenção de logs devem ser configurados na infraestrutura onde o compose for executado.
