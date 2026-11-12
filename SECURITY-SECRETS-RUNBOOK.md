# Proteção e rotação de segredos

- Nunca colocar `.env.vps`, tokens, chaves privadas ou dumps em pacotes, Git, logs ou mensagens.
- Manter `.env.vps` com permissão `600`, backup criptografado e acesso mínimo.
- Rotacionar imediatamente após suspeita de exposição e periodicamente conforme política interna.
- Ordem recomendada: credencial nova → atualizar serviço → recriar container → validar → revogar credencial antiga.
- Rotacionar separadamente `JWT_SECRET_KEY`, `INTERNAL_SERVICE_TOKEN`, banco, Redis, OpenAI, Mercado Pago, webhook, SMTP e chave de criptografia.
- A rotação de `JWT_SECRET_KEY` encerra todas as sessões. A chave de criptografia de configurações exige regravação segura dos segredos antes da revogação anterior.
- Registrar data, responsável, motivo e resultado sem registrar o valor do segredo.
