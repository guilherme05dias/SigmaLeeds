# AUDIT_REPORT_V4.1.md - ZapManager Pro v4.0

Data da auditoria: 2026-05-13  
Base: `AUDIT_REPORT_V4.0.md` e diff desde `21365c9`  
Modo: somente leitura de codigo; criado apenas este relatorio.

## Resumo executivo

O backend FastAPI sobe em `127.0.0.1:5050` sem stacktrace e o motor Node responde em `127.0.0.1:3001/ping`. SQLite inicializa em banco temporario e as protecoes centrais de token, CORS local, `safe_filename` e `resolve_under` continuam presentes.  
As falhas principais sao: testes de database quebrados por funcao ausente, arquivos `.pyc` ainda versionados, validador de licenca nao usa `public_key.pem`, Electron nao carrega a URL com token, e `npm audit` aponta vulnerabilidades high em Electron/whatsapp-motor.  
Severidade geral: ⚠️ Atenção alta, com regressao objetiva em testes e pendencias de empacotamento/seguranca.

## Fase 1 - Inventario e sanidade

| Status | Item | Evidencia |
|---|---|---|
| ⚠️ Atenção | Working tree tem muitas alteracoes desde `21365c9`. | `git diff --stat 21365c9`: 428 files changed, 2683 insertions, 7754 deletions. `git status --short`: `M 22`, `D 406`, `?? 17`. |
| ⚠️ Atenção | Arquivos modificados principais fora de `.wwebjs_auth`: `.gitignore`, `AGENTS.md`, `app.py`, `database/schema.py`, servicos SQLite, `license/*`, `requirements.txt`, `static/*`, `templates/index.html`, `whatsapp-motor/server.js`. | Comando: `git status --short`. |
| ✅ OK | Arquivos obrigatorios existem e nao estao vazios. | `Get-Item ...`: `app.py` 44591, `automation_state.py` 2689, `whatsapp_automation.py` 36591, `database/schema.py` 5295, `whatsapp-motor/server.js` 7177, `electron/main.js` 6593, `license/manager.py` 3992, `static/script.js` 44079, `templates/index.html` 29054, `criar_planilha_modelo.py` 1944 bytes. |
| ✅ OK | `.gitignore` contem os padroes obrigatorios. | `.gitignore:5-10`, `.gitignore:14`, `.gitignore:22-23`: `data/`, `*.db`, `node_modules/`, `.wwebjs_auth/`, `.wwebjs_cache/`, `__pycache__/`, `dist/`, `build/`. |
| ❌ Falha | Arquivos `__pycache__/*.pyc` continuam versionados. | `git ls-files | rg "(^|/)__pycache__/|\.pyc$"` listou `__pycache__/app.cpython-311.pyc`, `database/__pycache__/schema.cpython-312.pyc`, `license/__pycache__/manager.cpython-312.pyc`, `tests/__pycache__/test_database...pyc`, entre outros. |

## Fase 2 - Backend FastAPI (`app.py`)

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | Boot test subiu em `127.0.0.1:5050` sem stacktrace. | Comando equivalente com `webbrowser.open` desabilitado: `boot_ok=True status=200 elapsed_ms=4104`; stderr: `Uvicorn running on http://127.0.0.1:5050`. |
| ⚠️ Atenção | `python app.py` puro abre navegador automaticamente, entao nao foi executado literalmente para cumprir a regra do projeto. | `app.py:1154`: `webbrowser.open(f"http://127.0.0.1:{port}")`. |
| ✅ OK | `SESSION_TOKEN`, middleware de sessao e CORS local continuam presentes. | `app.py:206`, `app.py:318-328`, `app.py:330-336`. |
| ✅ OK | `safe_filename` e `resolve_under` continuam presentes. | `app.py:211-224`. |
| ✅ OK | Spawn e health check do Node continuam presentes. | `app.py:88-103`, `app.py:171-181`, `app.py:298-303`. |
| ✅ OK | `reset_stuck_contacts()` roda no lifespan. | `app.py:276-288`. |
| ⚠️ Atenção | Circuit breaker existe, mas usa `print()` em producao. | `app.py:497-503`: `error_rate >= 0.10`, pausa `1800`; `app.py:501`: `print(msg)`. |
| ✅ OK | Rotas registradas estao protegidas pelo middleware, exceto `/` e estaticos. | `python -c "import app; ... app.app.routes"`: todas as rotas `/api/*`, `/docs`, `/redoc`, `/openapi.json` com `protected=True`; `/` com `protected=False`. |
| ✅ OK | Rotas de escrita/upload exigem token via middleware. | Mesmo comando de `app.routes`: `POST /api/contacts/import`, `POST /api/upload-excel`, `POST /api/upload-attachment`, `POST /api/campaign/start`, `POST /api/license/activate`, `POST /api/config` com `protected=True`. |
| ✅ OK | Escritas de upload usam `safe_filename` + `resolve_under`. | `app.py:601-604`, `app.py:659-662`, `app.py:880-888`. |
| ⚠️ Atenção | `uploads/` legado ainda e criado, mas uploads atuais gravam em `data/attachments`. | `app.py:342-343` cria `UPLOAD_FOLDER`; `app.py:208` define `UPLOAD_ROOT = data/attachments`. |

## Fase 3 - Banco SQLite (`database/`)

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout` presentes. | `database/schema.py:105-111`. |
| ✅ OK | `MIGRATIONS` sequencial e indice unico por campanha/telefone presentes. | `database/schema.py:17-103`, `database/schema.py:57-58`: `ON campaign_contacts(campaign_id, phone)`. |
| ✅ OK | Schema inicializa em DB temporario. | `python -c "... s.DB_PATH=path; s.init_db(); ..."`: `init_db_temp=OK`. Observacao: `init_db(':memory:')` falha porque `init_db()` nao recebe argumento. |
| ✅ OK | `campaign_service.py` contem normalizacao, DDDs validos, `INSERT OR IGNORE`, reset e exportacao XLSX. | `database/services/campaign_service.py:12-24`, `database/services/campaign_service.py:132-144`, `database/services/campaign_service.py:242-248`, `database/services/campaign_service.py:288-339`. |
| ✅ OK | `template_service.py` contem spintax e renderizacao. | `database/services/template_service.py:9-13`, `database/services/template_service.py:70-80`. |
| ✅ OK | Nao foram encontrados SQLs com f-string nos servicos auditados. | `rg 'execute\(\s*f|executemany\(\s*f|f"' database/services/*.py` retornou apenas f-strings nao SQL em `campaign_service.py:104` e `campaign_service.py:126`. |
| ❌ Falha | Teste de database quebra na coleta por import ausente. | `python -m pytest tests/test_database.py -v`: `ImportError: cannot import name 'remove_from_blacklist'`; `tests/test_database.py:8` importa `remove_from_blacklist`, mas `database/services/blacklist_service.py` nao define a funcao. |

## Fase 4 - Motor Node (`whatsapp-motor/server.js`)

| Status | Item | Evidencia |
|---|---|---|
| ⚠️ Atenção | Versoes instaladas divergem do range declarado, mas satisfazem semver. | `whatsapp-motor/package.json:10-14` declara `express ^4.19.2`, `whatsapp-web.js ^1.23.0`; `npm ls --depth=0`: `express@4.22.1`, `whatsapp-web.js@1.34.6`. |
| ✅ OK | `node_modules` esta instalado. | `Test-Path whatsapp-motor/node_modules`: `True`; `npm ls --depth=0` executou com sucesso. |
| ✅ OK | Boot isolado respondeu health check em `127.0.0.1:3001`. | `node whatsapp-motor/server.js` via `Start-Process`: `node_boot_ok=True status=200 elapsed_ms=3335`. |
| ✅ OK | Bind restrito a loopback. | `whatsapp-motor/server.js:201-204`: `app.listen(PORT, '127.0.0.1', ...)`. |
| ✅ OK | QR Code, reconexao e logout tratados. | QR: `server.js:46-56`; reconexao: `server.js:79-91`; logout: `server.js:120-136`. |
| ⚠️ Atenção | Sessao nao usa mais `.wwebjs_auth/` como unico local; usa AppData. Fora do git, mas divergente da expectativa. | `server.js:17-19`, `server.js:35-37`: `LocalAuth({ dataPath: appDataDir })`; `.wwebjs_auth/` aparece deletado no `git status`. |

## Fase 5 - Licenca (`license/`)

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | Testes de licenca passam. | `python -m pytest license/test_license.py -v`: `3 passed in 3.79s`. |
| ❌ Falha | `validator.py` nao usa `license/public_key.pem`; chave publica esta embutida no codigo. | `license/validator.py:8-13`: `PUBLIC_KEY_PEM = ...`; `get_public_key()` carrega a constante. |
| ✅ OK | Licenca com hardware divergente e rejeitada quando `hardware_id` existe no payload. | `license/validator.py:49-56`. |
| ✅ OK | `manager.py` nao loga chave de licenca nem expoe chave privada. | `license/manager.py:35-47`, `license/manager.py:49-100`; grep por `PRIVATE KEY` nao encontrou chave privada no workspace. |

## Fase 6 - Frontend (`templates/`, `static/`)

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | Override de `window.fetch` injeta token. | `static/script.js:12-24`. |
| ✅ OK | Wrapper `api()` e `apiBg()` injetam `X-Session-Token`. | `static/script.js:31-39`, `static/script.js:61-68`. |
| ✅ OK | Editor/modal de spintax existe. | `templates/index.html:448-477`, `static/script.js:1076-1155`. |
| ❌ Falha | Modal/fluxo de planilha modelo nao foi encontrado na UI. | `rg "modelo|planilha|contatos_modelo|xlsx"` retornou `criar_planilha_modelo.py:51` e upload XLSX, mas nenhum modal/botao de modelo em `templates/index.html` ou `static/script.js`. |
| ❌ Falha | `static/style.css` tem hex hardcoded fora dos tokens. | Exemplos: `static/style.css:269-271`, `static/style.css:326`, `static/style.css:332`, `static/style.css:337`, `static/style.css:350`, `static/style.css:431`, `static/style.css:447`, `static/style.css:490`, `static/style.css:519`. |
| ⚠️ Atenção | Smoke test manual nao executado por regra de nao abrir navegador. | Passos sugeridos: subir backend, abrir `http://127.0.0.1:5050/?token=...`, criar campanha, importar `contatos_modelo.xlsx`, iniciar, conferir atualizacao de status. |

## Fase 7 - Electron e empacotamento

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | Janela principal usa `nodeIntegration: false`, `contextIsolation: true`, `webSecurity: true`. | `electron/main.js:96-102`. |
| ❌ Falha | Janela carrega `127.0.0.1` sem token na URL. | `electron/main.js:86`, `electron/main.js:123`: `mainWindow.loadURL(allowedOrigin)`. |
| ✅ OK | Navegacao fora da origem local e bloqueada. | `electron/main.js:107-121`, `electron/main.js:133-135`. |
| ⚠️ Atenção | `electron/package.json` e coerente, mas a raiz ainda e Vite/React. | `electron/package.json:2-13`; `package.json:2`: `"name": "react-example"`; `package.json:7-9`: scripts Vite. |
| ❌ Falha | Scripts batch contem caminhos hardcoded quebrados. | `Instalar_Motor.bat:27`: `c:\Users\user\Desktop\SigmaLeeds\whatsapp-motor`; `SigmaHub.bat:3-4`: `C:\Users\user\Desktop\SigmaLeeds` e Python 3.11 local. |
| ⚠️ Atenção | `build.md` manda rodar `npm run build` na raiz, mas a raiz e Vite/React e nao Electron. | `build.md:40`; `package.json:2`, `package.json:7-9`. |
| ✅ OK | Referencias essenciais existem. | `Test-Path electron/preload.js`, `electron/splash.html`, `resources/icon.ico`, `electron/resources/engine`, `app.spec`: todos `True`. |

## Fase 8 - Dependencias e seguranca

| Status | Item | Evidencia |
|---|---|---|
| ✅ OK | Pacotes Python instalados atendem `requirements.txt`. | `python -c "... packaging.requirements ..."`: todos `OK`, incluindo `selenium 4.43.0`, `fastapi 0.136.0`, `uvicorn 0.44.0`, `cryptography 46.0.7`, `WMI 1.5.1`. |
| ❌ Falha | `npm audit` em `whatsapp-motor/` tem vulnerabilidade high. | `npm audit --json`: `basic-ftp` high, total high=1, critical=0. |
| ❌ Falha | `npm audit` em `electron/` tem 10 vulnerabilidades high. | `npm audit --json`: high em `electron`, `electron-builder`, `app-builder-lib`, `tar`, `node-gyp`, `cacache`, `make-fetch-happen`, etc.; critical=0. |
| ✅ OK | Nenhuma chave privada PEM foi encontrada no workspace. | `Get-ChildItem -Recurse -Filter private_key.pem`: sem resultados; `rg "BEGIN ... PRIVATE KEY"` sem achados reais. |
| ⚠️ Atenção | Grep de segredos encontrou geradores e textos de relatorio, nao segredo material. | `rg "api_key|secret|password|BEGIN PRIVATE KEY|ZMPRO-"`: achados em `app.py:206` (`SESSION_TOKEN`), `keygen.py`, `license/keygen.py`, docs/relatorios. |

## Top 5 problemas criticos

1. ❌ Testes de database quebrados por funcao ausente.  
   Evidencia: `tests/test_database.py:8` importa `remove_from_blacklist`; `python -m pytest tests/test_database.py -v` falha na coleta.  
   Sugestao: implementar `remove_from_blacklist(phone: str) -> bool` em `database/services/blacklist_service.py` ou ajustar o teste se a API publica mudou.

2. ❌ Artefatos `.pyc` continuam versionados.  
   Evidencia: `git ls-files | rg "(^|/)__pycache__/|\.pyc$"` lista varios `.pyc`; `git status --short` mostra `.pyc` modificados.  
   Sugestao: remover do indice com `git rm --cached` nos `.pyc` rastreados e manter `__pycache__/` no `.gitignore`.

3. ❌ Electron nao passa token ao carregar a janela.  
   Evidencia: `electron/main.js:123` usa `mainWindow.loadURL(allowedOrigin)` sem `?token=...`.  
   Sugestao: propagar o token da sessao para a URL ou via preload seguro, mantendo o bloqueio de origem.

4. ❌ `license/validator.py` ignora `license/public_key.pem`.  
   Evidencia: `license/validator.py:8-13` embute `PUBLIC_KEY_PEM`; nao ha leitura do arquivo PEM.  
   Sugestao: carregar `public_key.pem` em runtime/empacotamento, com erro tratado quando ausente.

5. ❌ Dependencias npm com vulnerabilidades high.  
   Evidencia: `npm audit --json` em `whatsapp-motor/` reporta `basic-ftp` high; em `electron/` reporta 10 high, incluindo `electron` e `electron-builder`.  
   Sugestao: atualizar dependencias afetadas dentro dos ranges seguros e repetir `npm audit` antes do build.

## Pendencias de fases anteriores

| Status | Item | Evidencia |
|---|---|---|
| ⚠️ Atenção | M7 - Wizard onboarding segue pendente. | `AUDIT_REPORT_V4.0.md:129-132`: M7 marcado como `PENDENTE`; nao foi encontrado wizard novo nesta auditoria. |
| ⚠️ Atenção | M8 - Janela de horario segue pendente. | `AUDIT_REPORT_V4.0.md:129-132`: M8 marcado como `PENDENTE`; regra de janela padrao nao apareceu como fluxo de produto novo nesta auditoria. |

