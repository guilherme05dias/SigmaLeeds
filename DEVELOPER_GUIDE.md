# ZapManager Pro — Guia do Desenvolvedor

Versão atual: **4.2.6**
Data: 2026-06-01

---

## Visão geral

ZapManager Pro é uma ferramenta desktop para envio em massa de mensagens pelo WhatsApp. Funciona como um aplicativo Electron que embute dois processos internos:

1. **Python/FastAPI** (`app.py`) — backend web, banco de dados, lógica de campanhas.
2. **Node.js/whatsapp-web.js** (`whatsapp-motor/server.js`) — motor que controla o WhatsApp Web via Puppeteer.

O usuário acessa a interface pelo próprio Electron (que abre a UI servida pelo FastAPI em `http://127.0.0.1:505x`).

---

## Arquitetura

```
Electron (main.js)
 ├── Inicia app.exe (Python/FastAPI) na porta 5050–5099
 ├── Aguarda HTTP 200 em GET / (health check público)
 └── Abre BrowserWindow apontando para http://127.0.0.1:{porta}

app.py (FastAPI — porta 5050)
 ├── Serve frontend estático (templates/index.html + static/)
 ├── REST API (/api/*)
 ├── SSE de logs (/api/logs)
 ├── Inicia whatsapp-motor/server.js via Node.js (porta 3001)
 └── CampaignRunner (thread) → AutomationEngine → HTTP POST /send (Node)

whatsapp-motor/server.js (Express — porta 3001, bind 127.0.0.1)
 ├── Instância única do Client whatsapp-web.js
 ├── GET  /status   — retorna {connected, qr}
 ├── POST /send     — envia mensagem/arquivo
 ├── POST /disconnect / /reset-session
 └── GET  /diagnostics — debug de browser detectado
```

### Fluxo de envio

```
Usuário inicia campanha
  → POST /api/campaign/start
  → _run_automation() (thread separada)
      → Para cada contato PENDENTE:
          render_template(msg, contact, índice)  ← substitui {nome}, {empresa}, extra cols
          apply_spintax(text, índice)            ← round-robin nas variações
          AutomationEngine.send_message(numero, mensagem_final)
          → POST http://127.0.0.1:3001/send
          → whatsapp-web.js envia pelo WhatsApp Web
```

---

## Estrutura de arquivos

```
SigmaLeeds/
├── app.py                          # FastAPI principal — todos os endpoints
├── automation_state.py             # CampaignRunner (controle de thread, progresso)
├── whatsapp_automation.py          # AutomationEngine (HTTP client p/ motor Node)
├── app.spec                        # Config PyInstaller
│
├── api/
│   └── models.py                   # Pydantic models (StartCampaignRequest, etc.)
│
├── database/
│   ├── schema.py                   # SQLite migrations + get_connection()
│   └── services/
│       ├── campaign_service.py     # CRUD campanhas e contatos
│       ├── template_service.py     # render_template() + apply_spintax()
│       ├── blacklist_service.py    # Lista negra de números
│       ├── config_service.py       # Configurações (key/value no banco)
│       ├── safety_service.py       # Anti-banimento: warm-up + safety limit
│       ├── send_window.py          # Janela de horário de envio
│       ├── account_service.py      # CRUD contas WhatsApp
│       └── template_xlsx.py        # Geração de planilha modelo
│
├── templates/
│   └── index.html                  # Frontend SPA (HTML + JS inline)
│
├── static/
│   ├── script.js                   # Toda lógica JS do frontend
│   └── style.css                   # CSS do frontend
│
├── whatsapp-motor/
│   ├── server.js                   # Motor Node.js (whatsapp-web.js)
│   └── package.json
│
├── electron/
│   ├── main.js                     # Electron entry point
│   ├── preload.js                  # Preload seguro (contextIsolation)
│   ├── splash.html                 # Tela de loading
│   ├── package.json                # Config electron-builder (versão aqui)
│   └── resources/
│       ├── engine/
│       │   ├── app.exe             # Python compilado (PyInstaller)
│       │   └── whatsapp-motor/     # Motor Node + node_modules
│       ├── node/node.exe           # Node.js portátil (v20)
│       └── chromium/chrome.exe    # Chromium embutido (v148)
│
├── license/
│   ├── validator.py                # Verificação Ed25519 (só chave pública)
│   ├── manager.py                  # check_license(), get_current_plan_limits()
│   ├── hardware.py                 # Hardware ID para ativação
│   └── keygen.py                  # Gerador de chaves (rodar localmente, nunca no repo)
│
├── scripts/
│   └── verify_install.ps1          # Script de pré-requisitos para o cliente
│
└── tests/
    └── test_database.py            # Testes de serviços de banco
```

---

## Banco de dados

SQLite em `%LOCALAPPDATA%\ZapManagerPro\zapmanager.db` (produção) ou `data/test_app.db` (testes com `ZAP_DB_MEMORY=1`).

Migrations sequenciais em `database/schema.py` (lista `MIGRATIONS`). Cada migration é um SQL executado uma vez. Para adicionar uma migration, basta **appender** à lista — nunca editar as existentes.

### Tabelas principais

| Tabela | Descrição |
|--------|-----------|
| `campaigns` | Campanhas com nome, template, status |
| `campaign_contacts` | Contatos de cada campanha (nome, fone, empresa, extra_fields JSON, status) |
| `blacklist` | Números bloqueados (nunca recebem mensagens) |
| `templates` | Templates salvos com variáveis |
| `system_config` | Configurações key/value (intervalos, warm-up, janela de envio) |
| `whatsapp_accounts` | Registro de contas conectadas (informativo) |
| `safety_consents` | Log de aceites de risco pelo operador |

### Status de contato

`PENDENTE` → `EM_PROCESSAMENTO` → `ENVIADO` / `INVÁLIDO` / `ERRO` / `BLACKLIST`

Contatos que ficam travados em `EM_PROCESSAMENTO` por crash são resetados para `PENDENTE` automaticamente no próximo start de campanha.

---

## Templates e variáveis

### Variáveis de substituição

Usam **chave simples** `{variavel}` — consistente com o preview do frontend em `static/script.js`.

| Tag | Fonte |
|-----|-------|
| `{nome}` | Coluna `Nome` / `Cliente` / `Contato` da planilha |
| `{empresa}` | Coluna `Empresa` / `Razao Social` da planilha |
| `{adicional1}` | Qualquer outra coluna (nome da coluna em minúsculo, sem acento) |
| `{adicional2}` | Idem |
| `{qualquer_coluna}` | Idem — todas as colunas extras viram tags automaticamente |

**Implementação:** `database/services/template_service.py` → `render_template()`

### Variações (spintax)

Usa **chave simples com pipe** `{opção1|opção2|opção3}`.

- Cada contato recebe uma opção diferente em **round-robin** (não aleatório puro).
- Com 3 opções e 10 contatos: A, B, C, A, B, C, A, B, C, A.

```
Exemplo de mensagem:
{Olá|Oi|Bom dia} {nome}! A {empresa} tem uma oferta especial hoje.
```

**Variáveis e spintax podem ser combinados:**
```
{Olá {nome}!|Oi {nome}, tudo bem?}
```
> Nota: variáveis DENTRO de opções spintax não funcionam quando as opções contêm `{` `}` internos, pois o regex do spintax usa `[^{}]+`. Use separado:
> `{Olá|Oi} {nome}!` ← funciona corretamente

**Implementação:** `apply_spintax(text, contact_index)` em `template_service.py`

---

## Anti-banimento

### Warm-up automático

Rastreia a data da primeira conexão WhatsApp (`whatsapp_first_connection_at` no `system_config`). Aplica limite escalonado por dia:

| Dia | Limite |
|-----|--------|
| 1 | 20 |
| 2 | 40 |
| 3 | 80 |
| 4–7 | 150 |
| 8–14 | 250 |
| 15+ | safety_limit (default 300) |

### Safety limit

Configurável em Configurações. Default: 300/dia. Quando atingido, a campanha **pausa** e exibe modal pedindo confirmação do operador ("Aceito o risco"). O aceite é registrado em `safety_consents`.

### Intervalo entre envios

Mínimo: 30s. Máximo: 180s. Configurável na UI. A sugestão de intervalo é proporcional ao volume da campanha.

---

## Segurança

| Item | Implementação |
|------|--------------|
| Session token | `SESSION_TOKEN = secrets.token_urlsafe(32)` por processo. Exigido em todos os endpoints exceto `/`, `/favicon.ico`, `/static/*` |
| Node bind | `app.listen(3001, '127.0.0.1')` — não expõe na LAN |
| Path traversal | `/send` do motor verifica que `filePath` está dentro de `ZAP_ATTACHMENTS_ROOT` |
| Navegação Electron | `will-navigate` e `did-start-navigation` bloqueiam URLs fora do servidor local |
| Licença | Ed25519 — só chave pública no código. Chave privada deve existir apenas offline |

---

## Motor WhatsApp (Node.js)

`whatsapp-motor/server.js` é um servidor Express que gerencia uma instância do `whatsapp-web.js`.

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/status` | `{connected, qr}` |
| GET | `/qr` | QR Code em base64 |
| GET | `/diagnostics` | Versão Node, browser detectado, caminhos |
| GET | `/ping` | Health check simples |
| POST | `/send` | `{number, message, filePath?}` |
| POST | `/disconnect` | Encerra sessão WhatsApp |
| POST | `/reset-session` | Apaga arquivos de sessão e reconecta |

### Detecção de browser

Ordem de prioridade:
1. `ZAP_BROWSER_PATH` (override manual)
2. `ZAP_BUNDLED_CHROMIUM` (Chromium embutido no instalador)
3. Google Chrome instalado no sistema
4. Microsoft Edge (fallback — pode ter problemas com WhatsApp)

### Watchdog

Se após 90s não houver QR nem `ready`, apaga a sessão salva e reinicializa o client. Tenta até 3 vezes antes de desistir.

---

## Como rodar em desenvolvimento

### Pré-requisitos

- Python 3.12+
- Node.js 18+ (ou usar o `electron/resources/node/node.exe` portátil)
- Google Chrome ou Edge instalado

### Setup

```powershell
# 1. Criar ambiente virtual e instalar dependências Python
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt   # ou instalar manualmente

# 2. Instalar dependências Node do motor
cd whatsapp-motor
npm install
cd ..

# 3. Rodar o backend
python app.py
# Abre em http://127.0.0.1:5050
```

O Python inicia automaticamente o `whatsapp-motor/server.js` na porta 3001.

### Rodar os testes

```powershell
python -m pytest tests/test_database.py -v
# Esperado: 7 passed
```

### Rodar o Electron (dev)

```powershell
cd electron
npm install
npm start
```

---

## Como buildar o instalador

### Passo 1 — Compilar o Python com PyInstaller

```powershell
cd C:\...\SigmaLeeds
.venv\Scripts\pyinstaller.exe --clean app.spec
# Gera: dist\app.exe (~53 MB)
```

### Passo 2 — Copiar app.exe para o engine

```powershell
Copy-Item dist\app.exe electron\resources\engine\app.exe -Force
```

### Passo 3 — Sincronizar server.js (se alterado)

```powershell
Copy-Item whatsapp-motor\server.js electron\resources\engine\whatsapp-motor\server.js -Force
```

### Passo 4 — Atualizar versão

- `electron/package.json` → campo `"version"`
- `electron/main.js` → campo `title` na `BrowserWindow`

### Passo 5 — Gerar instalador

```powershell
cd electron
npx electron-builder --win nsis --x64
# Gera: electron\dist\ZapManager Pro Setup X.X.X.exe (~310 MB)
```

---

## Adicionar uma nova coluna da planilha como variável

1. O usuário importa planilha com a nova coluna (ex: `Vendedor`).
2. O `import_contacts_from_xlsx` salva automaticamente em `extra_fields` como JSON: `{"vendedor": "João"}`.
3. O usuário usa `{vendedor}` no template — substituído automaticamente.
4. O preview no frontend (`static/script.js` → `updatePreview()`) também substitui automaticamente.

Não há nada a alterar no código para suportar novas colunas.

---

## Adicionar um novo endpoint

1. Criar modelo Pydantic em `api/models.py` se necessário.
2. Adicionar rota em `app.py` com `@app.get/post(...)`.
3. Usar `check_session_token(request)` no início se for rota protegida.

Exemplo:
```python
@app.get("/api/minha-rota")
async def minha_rota(request: Request):
    token = request.headers.get("X-Session-Token") or request.query_params.get("token")
    if token != SESSION_TOKEN:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return {"data": "..."}
```

---

## Licença

O sistema usa **Ed25519** para validar licenças.

- `license/validator.py` — contém apenas `PUBLIC_KEY_PEM`. Nunca deve ter a chave privada.
- `license/keygen.py` — gerador de chaves (rodar localmente, **nunca commitar a private key**).
- `license/manager.py` — `check_license()` retorna `{status, plan, message}`.
- Hardware ID: baseado em UUID da máquina (`license/hardware.py`).

Para emitir licença para um cliente:
1. Cliente informa o Hardware ID (aba Licença na UI).
2. Dev roda `python license/keygen.py --hwid <ID>` localmente.
3. Envia a chave gerada para o cliente.

> **IMPORTANTE:** A chave privada atual pode estar comprometida (foi commitada em versão anterior). Gerar novo par Ed25519, atualizar `PUBLIC_KEY_PEM` em `validator.py` e reemitir licenças antes de distribuir para novos clientes.

---

## Histórico de correções relevantes

| Versão | Correção |
|--------|----------|
| 4.2.6 | Variáveis `{nome}` substituídas corretamente; spintax em round-robin por contato |
| 4.2.5 | Warm-up automático; modal de consent; single-tier de licença; Chromium embutido |
| 4.2.4 | Chromium 148 portátil; watchdog do motor WhatsApp |
| Sprint anterior | C1: health check Electron; C2: bind 127.0.0.1; C3: path traversal; C4: private key removida; M1: intervalos; M2: timestamp localtime; M3: reset travados; M4: connection leak |

---

## Variáveis de ambiente relevantes

| Variável | Descrição |
|----------|-----------|
| `ZAP_NO_BROWSER` | `1` = não abre browser automaticamente ao subir (usado pelo Electron) |
| `ZAP_DB_MEMORY` | `1` = banco em memória para testes |
| `ZAP_NODE_EXE` | Caminho do Node.js portátil (passado pelo Electron ao Python) |
| `ZAP_BUNDLED_CHROMIUM` | Caminho do Chromium embutido (passado ao motor Node) |
| `ZAP_ATTACHMENTS_ROOT` | Diretório raiz para anexos (segurança de path traversal) |
| `ZAP_BROWSER_PATH` | Override manual do browser para o Puppeteer |

---

## Contato e repositório

Projeto: **SigmaLeeds / ZapManager Pro**
Dev original: guilherme08dias
