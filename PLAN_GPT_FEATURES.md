# Plano para ChatGPT 5.5 — Features pendentes Sprint 2

**Projeto:** ZapManager Pro v4.0 (Python/FastAPI + Node.js whatsapp-web.js + SQLite + Electron).
**Estado de partida:** working tree limpo no commit `1b1f1cb`, 7/7 testes verdes, vulnerabilidades npm zeradas.

Você vai implementar três features pendentes, **nesta ordem**:

1. **Modal de planilha modelo** (pequeno, ~30min)
2. **M7 — Wizard de onboarding** (médio, ~1-2h)
3. **M8 — Janela de horário de envio** (médio-grande, ~2h)

---

## Regras gerais — leia antes de começar

- Leia [AGENTS.md](AGENTS.md) e [DESIGN.md](DESIGN.md) por inteiro antes de tocar em qualquer arquivo de UI. Eles são **lei do projeto**.
- **Não invente estilos.** Use exclusivamente os tokens CSS definidos em `DESIGN.md`. Se faltar token, registre a divergência no relatório final em vez de criar hex novo.
- **Não use frameworks CSS externos** (Bootstrap, Tailwind, etc.).
- **Não execute `python app.py` puro** — ele abre browser automaticamente. Use boot test programático se precisar validar (veja exemplos no [AUDIT_REPORT_V4.1.md](AUDIT_REPORT_V4.1.md)).
- **Não execute `git push`** em nenhum momento. Só commits locais.
- **Não use `--no-verify`, não amend, não force.** Se um hook falhar, pare e reporte.
- **Sem feature flags ou backwards-compat shims.** Se algo está obsoleto, troque pelo novo.
- **Sem comentários explicando o que o código faz.** Só comente o "porquê" se não for óbvio (ex.: workaround de bug específico).
- **Toda escrita de arquivo precisa passar por `safe_filename()` + `resolve_under()`** ([app.py:211-224](app.py#L211-L224)). Não escreva fora de `data/`.
- **Todas as rotas novas (exceto GETs públicos que servem HTML/asset) devem ser protegidas pelo middleware de sessão.**
- **Ao final de cada feature, rode `python -m pytest tests/ license/ -v` — deve continuar 7/7 (ou mais, se você adicionar testes).**

---

## Quando usar agentes (importante)

Você tem agentes especializados disponíveis. Use-os:

- **`Explore` agent** — quando precisar mapear código que ainda não conhece. Ex.: "onde está a lógica de upload de planilha hoje?", "como o runner consome a config?". **Não** invoque para tarefa que cabe em 1-2 greps diretos.
- **`Plan` agent** — antes de **M8** especificamente. A janela de horário toca runner, scheduler, persistência e UI; vale gastar 1 chamada ao Plan agent para desenhar a arquitetura antes de codar. Para o modal e o M7, pode ir direto.
- **`general-purpose` agent** — se precisar fazer uma pesquisa multi-passo que vai consumir contexto (ex.: "leia todos os handlers de campanha e me devolva um resumo das dependências").

Regra prática: **use agente quando o trabalho de descoberta vai contaminar seu contexto principal com material que você não vai precisar lembrar depois.** Caso contrário, faça direto.

---

# Feature 1 — Modal de planilha modelo

## Objetivo

Adicionar na UI um botão "Baixar planilha modelo" que dispara o download de `contatos_modelo.xlsx` (planilha de exemplo com headers e linhas de exemplo).

## Estado atual

- O script [criar_planilha_modelo.py](criar_planilha_modelo.py) **já gera** o arquivo `contatos_modelo.xlsx` quando executado manualmente.
- O arquivo `contatos_modelo.xlsx` **já existe** na raiz do projeto.
- Não há rota de download nem botão na UI.
- O audit [AUDIT_REPORT_V4.1.md](AUDIT_REPORT_V4.1.md) confirmou que o modal/fluxo não existe.

## Tarefas

### 1.1 — Backend: rota de download

Em [app.py](app.py), adicione uma rota `GET /api/template/contacts.xlsx` que:
- Está sob o middleware de sessão (não adicione em `public_paths`).
- Gera a planilha **em memória** chamando uma função extraída de [criar_planilha_modelo.py](criar_planilha_modelo.py) — **não** sirva o arquivo da raiz, ele é gerado e versionado mas não é a fonte de verdade.
- Responde com `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` e `Content-Disposition: attachment; filename="contatos_modelo.xlsx"`.

**Refatoração:** extraia a lógica de geração de [criar_planilha_modelo.py](criar_planilha_modelo.py) para uma função `build_template_workbook() -> openpyxl.Workbook` em um módulo apropriado (sugestão: criar `services/template_xlsx.py` ou colocar em `database/services/campaign_service.py` se fizer sentido). Mantenha o `criar_planilha_modelo.py` funcionando para uso CLI (que ele chame a nova função).

Use `StreamingResponse` com um buffer `io.BytesIO` que recebe `wb.save(buffer)`.

### 1.2 — Frontend: botão

Em [templates/index.html](templates/index.html), localize a seção/aba de **importação de contatos** (onde fica o upload de XLSX). Adicione, **ao lado** do input de upload, um botão secundário "📥 Baixar planilha modelo" (use o ícone correto do design system — sem emoji se o DESIGN.md proibir).

Em [static/script.js](static/script.js), o botão deve:
- Chamar `api('/api/template/contacts.xlsx')` via `fetch` direto (porque é binário, o wrapper `api()` pode não servir — confira primeiro como [static/script.js](static/script.js) trata downloads existentes).
- Pegar o blob, criar URL com `URL.createObjectURL` e disparar `<a download>` programático.

Não abra modal pesado — é só um botão de download. Se quiser dar feedback, use o `showToast()` existente.

### 1.3 — Validação

- Stage e commit:
  ```
  feat: botao de download da planilha modelo

  Adiciona GET /api/template/contacts.xlsx protegido pelo middleware
  de sessao, gerando o xlsx em memoria via openpyxl. UI ganha botao
  ao lado do upload de contatos que dispara o download.
  ```
- Manualmente (em ambiente do operador, não nesta sessão headless): subir o app, clicar no botão, conferir que o arquivo baixa e abre no Excel. Como você não vai abrir browser, **deixe documentado** no relatório que o smoke test ficou para o operador rodar.

---

# Feature 2 — M7 Wizard de onboarding

## Objetivo

Na **primeira execução** do app (banco recém-criado, nenhuma config gravada), exibir um wizard de 3-4 passos guiando o usuário até estar pronto para a primeira campanha. Após concluído, marcar como feito e não exibir mais.

## Passos do wizard (escopo mínimo)

1. **Boas-vindas** — explicação curta (1 parágrafo) do que o ZapManager faz e do aviso legal do WhatsApp (copiar do [README.md](README.md) seção 1).
2. **Conectar WhatsApp** — instrui o usuário a clicar em "Conectar" e ler o QR Code. Mostra o QR (reaproveite o componente existente em [static/script.js](static/script.js); procure por "QR" / "qrcode"). Avança automaticamente quando a sessão fica `ready`.
3. **Baixar planilha modelo** — botão grande disparando o download da feature 1 (reuso da rota `/api/template/contacts.xlsx`). Avança quando o usuário clica.
4. **Pronto** — mensagem "Você está pronto" + botão "Concluir" que fecha o wizard e marca como feito.

## Persistência

Use a tabela `system_config` (já existe, [database/schema.py:88-92](database/schema.py#L88-L92)) com chave `onboarding_completed = "1"`. Use `set_config` / `get_config` de [database/services/config_service.py](database/services/config_service.py).

## Tarefas

### 2.1 — Backend

- Em [app.py](app.py), adicione rota `GET /api/onboarding/status` (protegida) que retorna `{"completed": bool}` lendo `get_config("onboarding_completed", "0") == "1"`.
- Adicione rota `POST /api/onboarding/complete` (protegida) que faz `set_config("onboarding_completed", "1")` e retorna `{"success": True}`.
- **Não** invente endpoints novos para QR / conexão se já existirem — reaproveite.

### 2.2 — Frontend

- Em [templates/index.html](templates/index.html), adicione o markup do wizard como um overlay/modal full-screen com 4 telas (use CSS para mostrar uma de cada vez — variável `data-step="1|2|3|4"` no container). Esconda por padrão (`display: none` ou `hidden`).
- Em [static/script.js](static/script.js), na inicialização:
  - Chame `/api/onboarding/status`.
  - Se `completed == false`, abra o wizard antes do resto do app.
  - Implemente lógica de navegação (botão "Avançar" / "Voltar").
  - No passo 2, observe o estado de conexão WhatsApp já existente; quando virar `ready`, libere o botão "Avançar".
  - No passo final, chame `POST /api/onboarding/complete` e esconda o wizard.
- Em [static/style.css](static/style.css), estilize o wizard usando **somente tokens** do [DESIGN.md](DESIGN.md). Sem hex hardcoded.

### 2.3 — Como testar

- Reset manual: `delete from system_config where key = 'onboarding_completed'` no SQLite (ou apague `%LOCALAPPDATA%/ZapManagerPro/zapmanager.db` para começar do zero).
- Como você não vai abrir browser, valide:
  - `python -c "import app"` sem erro.
  - `curl -H "X-Session-Token: $TOK" http://127.0.0.1:5050/api/onboarding/status` retorna 200 com JSON (precisa subir o app em background; veja exemplo de boot programático no audit anterior).
  - Inspeção visual do HTML/CSS por leitura — confirme estrutura de 4 telas e tokens corretos.

### 2.4 — Commit

```
feat: wizard de onboarding (M7)

Primeira execucao (system_config.onboarding_completed != "1") exibe
wizard de 4 passos: boas-vindas, conectar WhatsApp via QR, baixar
planilha modelo, conclusao. Estado persistido em system_config.
```

---

# Feature 3 — M8 Janela de horário de envio

## Objetivo

Permitir ao usuário configurar uma janela de horário (ex.: 08:00–18:00, dias úteis) durante a qual envios são permitidos. Fora da janela, o runner **pausa automaticamente** e retoma quando a janela reabre.

## Antes de codar — invoque o `Plan` agent

Esta feature toca runner, persistência, scheduler e UI. **Use o agente `Plan`** com este prompt:

> Desenhe a arquitetura para uma janela de horário de envio no ZapManager Pro v4.0. A campanha tem um `CampaignRunner` thread-based em `automation_state.py` que itera contatos pendentes e envia via Node motor. Preciso adicionar: (1) configuração persistida da janela (horário início, horário fim, dias da semana habilitados), (2) checagem dentro do loop do runner que pausa se fora da janela e retoma quando reabre, (3) endpoint REST para ler/escrever a config, (4) UI mínima para configurar. Leia `app.py`, `automation_state.py` e `database/services/config_service.py` antes de propor. Quero o plano com arquivos a alterar, snippets-chave e ordem de implementação. Não escreva código, só o plano.

Aplique o plano que ele retornar. Se ele propuser algo que viole as regras gerais deste documento, **ignore essa parte** e siga as regras.

## Esqueleto esperado (caso o Plan agent volte com algo muito diferente, ajuste)

### 3.1 — Persistência

A janela pode caber em `system_config` como JSON único, chave `send_window`:

```json
{
  "enabled": true,
  "start": "08:00",
  "end": "18:00",
  "days": [1, 2, 3, 4, 5]
}
```

(`days` em formato `datetime.weekday()`: 0=segunda … 6=domingo)

### 3.2 — Helper

Crie `services/send_window.py` (ou onde fizer sentido) com:

```python
def is_within_window(now: datetime, window: dict) -> bool:
    """Retorna True se now está dentro da janela configurada, ou se enabled=False."""

def seconds_until_window_opens(now: datetime, window: dict) -> int:
    """Retorna segundos até a próxima abertura da janela. 0 se já está dentro."""
```

Cubra com pytest em `tests/test_send_window.py`:
- Janela 08-18 num dia útil às 10h → dentro
- Janela 08-18 num dia útil às 19h → fora, próxima abertura no dia seguinte 08h
- Janela 08-18 num sábado com `days=[1-5]` → fora, próxima abertura na segunda 08h
- `enabled=False` → sempre dentro
- Janela 22-06 (cruza meia-noite) → cuidado

### 3.3 — Integração no runner

Em [automation_state.py](automation_state.py), dentro do loop principal do `CampaignRunner` (provavelmente onde itera pending contacts), antes de enviar:

```python
window = get_config("send_window", {"enabled": False})
if window.get("enabled") and not is_within_window(datetime.now(), window):
    wait_s = seconds_until_window_opens(datetime.now(), window)
    self.update_progress(status=f"Aguardando janela de horario ({wait_s//60} min)")
    if self._stop_event.wait(timeout=min(wait_s, 60)):
        return  # parou manualmente
    continue  # checa de novo
```

(Adapte aos nomes reais do `CampaignRunner` — leia o arquivo antes.)

### 3.4 — Backend

Em [app.py](app.py):

- `GET /api/config/send-window` → retorna a config atual (default `{"enabled": false, "start": "08:00", "end": "18:00", "days": [1,2,3,4,5]}`).
- `POST /api/config/send-window` → recebe JSON, valida (start < end OU cruza meia-noite com flag explícita; days é lista de int 0-6; horário no formato `HH:MM`), grava.

Validação rigorosa — não confie no cliente.

### 3.5 — Frontend

Em [templates/index.html](templates/index.html), na aba de configurações (ou crie uma se não houver), adicione:

- Checkbox "Habilitar janela de envio"
- Dois inputs `type="time"` (início, fim)
- Sete checkboxes de dia da semana
- Botão "Salvar"

Em [static/script.js](static/script.js):
- Carregar config no boot.
- Salvar via POST.
- Mostrar toast de confirmação.

Em [static/style.css](static/style.css):
- Layout dos campos usando tokens.

### 3.6 — Commit

```
feat: janela de horario de envio (M8)

Permite configurar janela (HH:MM inicio/fim + dias da semana) onde
envios sao permitidos. Runner pausa fora da janela e retoma na proxima
abertura. Config persistida em system_config.send_window. Inclui
helpers is_within_window/seconds_until_window_opens cobertos por
pytest.
```

---

## Validação final (após as 3 features)

```
python -m pytest tests/ license/ -v
# esperado: pelo menos 7 passed, mais os novos testes de send_window
python -c "import app; print('OK')"
git log --oneline -15
git status --short    # deve estar vazio
```

## Relatório final

Crie `FEATURES_REPORT_V4.2.md` na raiz, ≤ 250 linhas, com:

- Tabela: feature | status (✅/⚠️) | arquivos alterados | testes adicionados | smoke test pendente (sim/não)
- Decisões de design que você tomou (especialmente as do Plan agent)
- Pendências para o operador testar manualmente (subir o app e clicar)
- Diff resumido por feature (≤ 30 linhas de hunk principal por feature)
- Como reverter cada feature se der problema (qual commit reverter)

---

## Checklist mental antes de cada commit

- [ ] Tokens do DESIGN.md em vez de hex?
- [ ] Rota nova está sob middleware de sessão (ou justificadamente pública)?
- [ ] Sem `print()` — usar logger?
- [ ] Sem `--no-verify` no commit?
- [ ] `python -m pytest tests/ license/ -v` passa?
- [ ] Mensagem de commit explica o **porquê**, não o **o quê**?
- [ ] Arquivo escrito via `safe_filename` + `resolve_under` se for upload?

Boa sorte. Se em qualquer ponto algo bloquear (teste quebra, arquitetura proposta pelo Plan agent não cabe, etc.), **pare e reporte** — não tente forçar.
