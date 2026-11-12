# Deploy na VPS iContainer

Este guia adapta o deploy do Recruta IA ao ambiente iContainer/OpenResty. A aplicacao roda em Docker Compose; PostgreSQL e Redis continuam no host e somente o OpenResty acessa as portas publicadas em loopback.

## Topologia

| Componente | Endereco |
|---|---|
| Frontend | `https://recruta.sienixsistemas.com.br` -> `127.0.0.1:18080` |
| API | `https://recruta-api.vps6912.panel.icontainer.net` -> `127.0.0.1:18000` |
| Backend (container) | `backend:8000` |
| IA (rede interna) | `ai-service:8001` |
| PostgreSQL do host | `host.docker.internal:5432` |
| Redis do host | `host.docker.internal:6379` |

## 1. Preparar DNS e VPS

Crie registros DNS para os dois dominios apontando para o IP da VPS. Na VPS, confirme:

```bash
docker --version
docker compose version
```

Crie o diretorio da aplicacao:

```bash
mkdir -p /opt/sistema-vagas
cd /opt/sistema-vagas
```

Envie o repositorio para esse diretorio por Git/SFTP. Nao envie os arquivos locais `backend/.env`, `ai-service/.env`, `.env.vps` ou qualquer chave real.

## 2. Banco e Redis

Crie no PostgreSQL do painel um banco e usuario exclusivos. Crie tambem uma senha forte para o Redis e escolha um database logico, por exemplo `/1`.

O acesso a PostgreSQL e Redis precisa aceitar conexoes originadas da bridge Docker. Nao abra `5432` ou `6379` para a internet; limite pelo firewall/configuracao local da VPS.

Antes de continuar, valide no host as portas em escuta:

```bash
ss -lnt | grep -E ':5432|:6379'
```

## 3. Variaveis de ambiente

```bash
cd /opt/sistema-vagas
cp .env.vps.example .env.vps
chmod 600 .env.vps
```

Gere os dois segredos independentemente:

```bash
openssl rand -hex 32
openssl rand -hex 32
```

Edite `.env.vps` e substitua todos os placeholders. Para senha com caracteres especiais dentro de `DATABASE_URL` ou `REDIS_URL`, use URL encoding (`@` vira `%40`, `#` vira `%23`). Valide sem imprimir os segredos:

```bash
docker compose --env-file .env.vps -f docker-compose.vps.yml config --quiet
```

## 4. Build e migracao

Construa as imagens:

```bash
docker compose --env-file .env.vps -f docker-compose.vps.yml build --pull
```

A migracao e deliberadamente separada. Execute antes de iniciar ou atualizar a API:

```bash
docker compose --env-file .env.vps -f docker-compose.vps.yml --profile tools run --rm migrate
```

Somente depois suba os servicos:

```bash
docker compose --env-file .env.vps -f docker-compose.vps.yml up -d
docker compose --env-file .env.vps -f docker-compose.vps.yml ps
```

Teste localmente na VPS:

```bash
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18000/ready
curl -fsSI http://127.0.0.1:18080/
```

## 5. OpenResty no painel iContainer

Crie dois dominios do tipo Proxy:

| Dominio | Endereco do proxy |
|---|---|
| `recruta.sienixsistemas.com.br` | `127.0.0.1:18080` |
| `recruta-api.vps6912.panel.icontainer.net` | `127.0.0.1:18000` |

Se o painel exigir arquivos de proxy, use como base:

- `deploy/openresty-frontend.conf.example`
- `deploy/openresty-api.conf.example`

Nao substitua configuracoes globais do OpenResty. Coloque apenas o bloco `location` no diretorio de proxy criado pelo painel e recarregue o OpenResty.

Teste HTTP antes de emitir os certificados:

```bash
curl -I http://recruta.sienixsistemas.com.br/
curl -fsS http://recruta-api.vps6912.panel.icontainer.net/health
```

## 6. HTTPS

No painel, emita certificados Let's Encrypt para ambos os dominios pelo metodo HTTP, habilite renovacao automatica e force redirecionamento HTTP -> HTTPS. Prefira deixar o painel criar e renovar os arquivos; nao copie chaves privadas manualmente salvo se o painel realmente exigir.

Depois valide:

```bash
curl -fsSI https://recruta.sienixsistemas.com.br/
curl -fsS https://recruta-api.vps6912.panel.icontainer.net/health
curl -fsS https://recruta-api.vps6912.panel.icontainer.net/ready
```

## 7. Integracoes externas

Configure no Mercado Pago:

```text
https://recruta-api.vps6912.panel.icontainer.net/v1/payments/webhooks/mercadopago
```

Os callbacks OAuth devem coincidir exatamente com `.env.vps`:

```text
https://recruta-api.vps6912.panel.icontainer.net/v1/auth/oauth/google/callback
https://recruta-api.vps6912.panel.icontainer.net/v1/auth/oauth/linkedin/callback
```

## 8. Atualizar a aplicacao

Antes de atualizar, faça backup do PostgreSQL. Depois atualize os arquivos e rode:

```bash
cd /opt/sistema-vagas
docker compose --env-file .env.vps -f docker-compose.vps.yml build --pull
docker compose --env-file .env.vps -f docker-compose.vps.yml --profile tools run --rm migrate
docker compose --env-file .env.vps -f docker-compose.vps.yml up -d --remove-orphans
docker compose --env-file .env.vps -f docker-compose.vps.yml ps
curl -fsS http://127.0.0.1:18000/ready
```

Nao use `docker compose down -v`: a opcao `-v` pode remover dados persistentes de outros modelos de deploy.

## 9. Operacao e diagnostico

```bash
# Estado e healthchecks
docker compose --env-file .env.vps -f docker-compose.vps.yml ps

# Logs recentes, sem modo follow infinito
docker compose --env-file .env.vps -f docker-compose.vps.yml logs --tail=200 backend ai-service frontend

# Reiniciar apenas a API
docker compose --env-file .env.vps -f docker-compose.vps.yml restart backend

# Conferir portas: devem aparecer somente em 127.0.0.1
ss -lnt | grep -E ':18000|:18080'
```

Configure backup diario do PostgreSQL fora do diretorio da aplicacao, teste restauracao periodicamente e monitore `/ready`, respostas 5xx, uso de disco/memoria e expiracao TLS.

## Checklist de go-live

- [ ] Credenciais locais antigas foram revogadas e rotacionadas.
- [ ] `.env.vps` esta com permissao `600` e fora do repositorio.
- [ ] PostgreSQL e Redis nao estao expostos publicamente.
- [ ] Migracao terminou com codigo zero.
- [ ] Todos os containers estao `healthy`.
- [ ] `/health` e `/ready` respondem por HTTPS.
- [ ] Frontend acessa a API sem erro de CORS.
- [ ] Webhook Mercado Pago foi testado sem credito duplicado.
- [ ] OAuth usa callbacks de producao.
- [ ] Backup e restauracao foram testados.
