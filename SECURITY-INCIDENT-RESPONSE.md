# Plano de resposta a incidentes — Recruta IA

## Contenção imediata
1. Registrar horário, origem do alerta, sistemas e dados possivelmente afetados.
2. Isolar o componente comprometido sem apagar evidências; revogar credenciais expostas e incrementar versões de sessão dos usuários afetados.
3. Preservar logs, imagens dos containers e trilhas de auditoria com acesso restrito.

## Avaliação e comunicação
1. Classificar impacto, titulares, volume, categorias de dados e risco de dano relevante.
2. Acionar responsável técnico, direção e encarregado de dados.
3. Avaliar, com assessoria jurídica, comunicação à ANPD e aos titulares nos termos e prazos aplicáveis.
4. Mensagens devem explicar natureza, dados atingidos, riscos, medidas adotadas e canal de contato, sem ocultar fatos materiais.

## Recuperação
1. Corrigir a causa raiz, rotacionar JWT, banco, Redis, OpenAI, Mercado Pago, SMTP e webhook quando aplicável.
2. Restaurar somente backups verificados; validar integridade, `/health`, `/ready`, pagamentos e autenticação.
3. Monitorar reincidência e documentar todas as decisões.

## Pós-incidente
Produzir relatório de causa raiz, linha do tempo, impacto, evidências, comunicações, ações corretivas, responsáveis e prazos. Realizar simulação semestral e teste periódico de restauração.

## Contatos a preencher antes da produção
- Responsável técnico:
- Direção:
- Encarregado/DPO:
- Jurídico:
- Provedor VPS:
- Mercado Pago:
