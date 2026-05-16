# Auditoria anti-banimento WhatsApp — ZapManager Pro

Data: 2026-05-16
Fonte das medidas: leitura do código em `app.py`, `automation_state.py`,
`whatsapp-motor/server.js`, `database/services/template_service.py`.

## Por que WhatsApp bane

Não há doc oficial pública com regras exatas. Os triggers abaixo são consenso
de comunidades de automação (whatsapp-web.js, Baileys, integradores BSP),
ordenados por **probabilidade de causar ban**:

| # | Trigger | Quanto pesa |
|---|---|---|
| 1 | Volume diário muito alto (especialmente nas primeiras semanas do número) | Crítico |
| 2 | Velocidade não-humana / rajada de envios sem pausa | Crítico |
| 3 | Mensagens idênticas em massa (mesmo texto exato) | Crítico |
| 4 | Reports de spam pelos destinatários | Crítico (qualquer report pesa) |
| 5 | Bloqueios consecutivos pelos destinatários | Alto |
| 6 | Muitos envios para números que **não** te mandaram mensagem antes | Alto |
| 7 | Conversa só-saída (nunca respondem, número fica "frio") | Médio-Alto |
| 8 | Detecção de cliente automatizado / sessão Web suspeita | Médio |
| 9 | Conta nova sem "warm-up" (envios pesados nos primeiros dias) | Alto |
| 10 | Envios em horário não-comercial / madrugada | Médio |
| 11 | Mudança rápida de IP / muitos dispositivos | Médio |
| 12 | Conteúdo proibido (golpe, ódio, conteúdo adulto) | Crítico mas fora do escopo técnico |

---

## O que o sistema TEM hoje

| Medida | Onde | Eficácia |
|---|---|---|
| Intervalo aleatório entre envios (15-45s default) | [app.py:626](app.py#L626) | ✅ Bom — quebra rajadas, mas pode ser baixo para volume alto |
| Spintax `{a\|b\|c}` para variar mensagem | [template_service.py:9](database/services/template_service.py#L9) | ✅ Bom — varia texto, mas só funciona se o usuário usar |
| Personalização `{nome}` / `{empresa}` / `{adicional}` | [template_service.py:70](database/services/template_service.py#L70) | ✅ Bom — cada mensagem fica única |
| Circuit breaker: >10% de erros nos últimos 10+ envios → pausa 30 min | [app.py:612-618](app.py#L612-L618) | ✅ Crítico — para sangria se algo dá errado |
| Validação prévia do número via `getNumberId` antes de enviar | [server.js:321](whatsapp-motor/server.js#L321) | ✅ Bom — evita tentar enviar pra número sem WhatsApp |
| Blacklist persistente para opt-outs | [blacklist_service.py](database/services/blacklist_service.py) | ✅ Bom |
| Detecção de keywords de opt-out (sair/parar/cancelar/etc) | [blacklist_service.py:59](database/services/blacklist_service.py#L59) | ⚠️ Existe mas só é útil **se a mensagem for monitorada** (e o app só envia, não lê respostas) |
| Limite diário de segurança (configurável, default 500) | [app.py:478](app.py#L478) + UI | ✅ Recém-adicionado — avisa mas não bloqueia |
| Reconexão automática após queda de sessão | [server.js:182-191](whatsapp-motor/server.js#L182) | ✅ |
| Pausa no envio se motor desconectar (até 60s aguardando reconexão) | [app.py:573-590](app.py#L573-L590) | ✅ |
| Janela de horário de envio (08-18, dias úteis) | Backend funciona, **UI desativada** | ⚠️ Backend pronto mas não acessível pro usuário |

---

## O que o sistema NÃO TEM (gaps)

### Críticos (alto risco de ban)

| # | Gap | Impacto | Sugestão |
|---|---|---|---|
| A | **Sem warm-up de número novo**. Um número novo manda 500 msg no primeiro dia → ban quase certo. | Crítico em onboarding de cliente | Adicionar "modo aquecimento": limite escalonado (dia 1: 20 msgs, dia 2: 40, dia 3: 80, …) que o sistema sugere/aplica |
| B | **Velocidade ainda alta para volume**. Intervalo min de 15s permite ~240 msg/h — rajada perceptível. Para 500/dia sem rajadas precisaria de média de ~3 min entre envios. | Alto em campanhas grandes | UI sugerir intervalo proporcional ao volume da campanha. Min absoluto subir para 30s. |
| C | **Não simula "typing"** (puppeteer pode chamar `page.type` com delay). Envio instantâneo após delay é detectável. | Médio | Antes do `client.sendMessage`, simular digitação de N segundos proporcional ao tamanho da msg |
| D | **Não lê respostas** → keyword opt-out (sair/cancelar) é inútil. Cliente responde "PARA" e continua recebendo. | Alto longo prazo (reports acumulam) | Habilitar `client.on('message')` no Node, detectar opt-out e adicionar à blacklist automaticamente |

### Importantes

| # | Gap | Impacto | Sugestão |
|---|---|---|---|
| E | **Sem rate limit por hora** (só daily). Cliente pode mandar 500 às 8h da manhã. | Médio | Limite secundário: max N msg/h (default 80) |
| F | **Janela de horário desativada na UI** (apesar do backend funcionar) | Médio | Reativar UI; envios fora de 08-21h são forte sinal de bot |
| G | **Sem rotação de número** (só 1 WhatsApp por vez) | Médio para volume alto | Suporte multi-conta com round-robin (já tem `max_accounts: 999` na licença, mas runner não usa) |
| H | **Não trackeia bloqueios pelo destinatário**. Não há sinal "fulano me bloqueou". | Médio | whatsapp-web.js tem `message_revoke_everyone` e estado de chat. Detectar ban da conta como rate-limit interno |
| I | **Histórico de envios não distingue novo destinatário vs recorrente**. Mandar pro mesmo número 1x/mês é seguro; 1x/semana ainda; 1x/dia já é alarme. | Médio | Tabela `recipient_history` com last_sent timestamp; cool-down de N dias por número |

### Polimento

| # | Gap | Sugestão |
|---|---|---|
| J | Sem retry/backoff progressivo (1 erro = 1 erro definitivo). | Em erro recuperável, tentar de novo após delay maior |
| K | Sem aviso de "número novo, considere começar com volume baixo" | Detectar primeira campanha do usuário e mostrar dica |
| L | Sem split de campanha grande em vários dias | Botão "agendar para X dias" que cria N campanhas com batches |

---

## Comparativo com o que o mercado faz

Soluções comerciais sérias (Take Blip, Sinch, Twilio MAU oficial) **não fazem isso via whatsapp-web** — usam a **WhatsApp Business API oficial**, que tem regras claras, número verificado, custo por mensagem, mas zero risco de ban (a Meta cobra e libera o envio).

Soluções "cinzas" (concorrentes diretas do ZapManager) que usam whatsapp-web.js geralmente implementam:

- ✅ Warm-up automático (gap **A**)
- ✅ Simulação de digitação (gap **C**)
- ✅ Listener de respostas com opt-out automático (gap **D**)
- ✅ Limite por hora além do diário (gap **E**)
- ✅ Multi-conta com rotação (gap **G**)
- ✅ Janela de horário ativa por padrão (gap **F**)

---

## Recomendação prioritizada

Se você puder fazer **só uma coisa**: ative o **listener de respostas** (gap **D**)
e o **warm-up automático** (gap **A**). Esses dois sozinhos reduzem ~70% do risco.

| Prioridade | Item | Custo estimado |
|---|---|---|
| 🔴 1 | **D**: Listener de respostas + opt-out automático | ~2h |
| 🔴 2 | **A**: Modo warm-up (limite escalonado por dia do número) | ~3h |
| 🟡 3 | **F**: Reativar UI da janela de horário | ~30 min |
| 🟡 4 | **E**: Limite por hora além do diário | ~1h |
| 🟡 5 | **C**: Simular typing antes do send | ~1h |
| 🟢 6 | **I**: Cool-down por destinatário (N dias entre envios pro mesmo número) | ~2h |
| 🟢 7 | **B**: Min absoluto de intervalo subir + UI sugerir intervalo proporcional | ~1h |
| 🔵 8 | **G**: Multi-conta com rotação | ~6h+ |
| 🔵 9 | **L**: Split de campanha grande em dias | ~3h |

Total se fizer só os 🔴+🟡: **~7.5h** de trabalho. Cobre os gaps de maior impacto.

---

## Avisos pro cliente final (deveria ir em algum lugar visível)

Independente das melhorias técnicas, o cliente final precisa ser instruído:

1. **Usar número dedicado**, nunca número pessoal
2. **Aquecer número novo**: 1ª semana mande para conhecidos, baixo volume
3. **Não use o mesmo texto pra todos** — use `{nome}` e spintax `{Olá|Oi|Tudo bem}`
4. **Não mande de madrugada** — horário comercial reduz reports
5. **Responda quem responde** — conversa de mão-dupla é o melhor anti-ban
6. **Aceite "PARA"/"CANCELAR" sempre** — adicione à blacklist na hora
7. **Volume diário gradual**: comece em 50, aumente +20% por dia se zero reports
8. **Se o WhatsApp pedir verificação por SMS no celular**, **pare imediatamente** — é sinal de pré-ban
