# FIX_REPORT_V4.1.md - ZapManager Pro v4.0

Data: 2026-05-13  
Escopo: correções solicitadas pós `AUDIT_REPORT_V4.1.md`.  
Observação operacional: não executei `python app.py` puro, não abri navegador e não rodei instalador.

## Tabela de verificação

| Tarefa | Status | Evidência |
|---|---|---|
| 1 - `render_template` `{}` | ✅ | `python -m pytest tests/test_database.py::test_template -v` -> `1 passed`; linhas `database/services/template_service.py:72-78`. |
| 2 - opt-out PT-BR | ✅ | `python -m pytest tests/test_database.py::test_blacklist -v` -> `1 passed`; linhas `database/services/blacklist_service.py:3`, `:63`, `:66`. |
| 3 - Electron audit/build | ✅ | `npm audit fix --force` -> `found 0 vulnerabilities`; `npm ls electron electron-builder --depth=0` -> `electron@42.0.1`, `electron-builder@26.8.1`; `npm run build` concluiu e gerou `electron/dist/ZapManager Pro Setup 4.0.1.exe`. |
| 4 - `.bat` sem caminho hardcoded | ✅ | `rg -n "c:\\Users\\user" Instalar_Motor.bat SigmaHub.bat` -> `hardcoded_user_path=0`; linhas `Instalar_Motor.bat:27`, `SigmaHub.bat:3-10`. |
| 5 - circuit breaker sem `print(msg)` | ✅ | `python -c "import app; print('import_app=OK')"` -> `import_app=OK`; linhas `app.py:501`, `app.py:507`. |
| 6 - hex CSS auditados | ✅ | `rg -n "#[0-9A-Fa-f]{3,6}" static/style.css` retorna apenas tokens em `:root`; linhas auditadas `269-271`, `326`, `332`, `337`, `350`, `431`, `447`, `490`, `519` usam `var(...)`. |
| 7 - conferência final | ✅ | `python -m pytest tests/ license/ -v` -> `7 passed`; `npm audit` em `whatsapp-motor/` -> `found 0 vulnerabilities`; `npm audit` em `electron/` -> `found 0 vulnerabilities`. |

## Avisos e pendências

- Electron build passou, mas reportou avisos não bloqueantes:
  - `author is missed in the package.json`.
  - `DeprecationWarning [DEP0190]` do Node durante o build.
- Não ficaram divergências de CSS nas linhas auditadas; os demais hex remanescentes são os próprios tokens em `:root`.
- O build baixou dependências do Electron/NSIS e gerou artefatos em `electron/dist/`; o instalador não foi executado.

## Diff resumido por arquivo

### `database/services/template_service.py`

- `render_template()` agora substitui `{nome}`, `{empresa}` e campos extras no formato `{ticket}`.
- `apply_spintax()` permanece compatível, pois a regex só consome blocos com pipe (`{a|b}`).

Hunk:
```diff
- text = text.replace('{{nome}}', ...)
- text = text.replace('{{empresa}}', ...)
- text = text.replace('{{' + k + '}}', str(v))
+ text = text.replace('{nome}', ...)
+ text = text.replace('{empresa}', ...)
+ text = text.replace('{' + k + '}', str(v))
```

### `database/services/blacklist_service.py`

- Adicionado `unicodedata`.
- Opt-out normaliza acentos antes da comparação.
- Novos termos: `nao quero`, `cancelar`, `bloquear`.

Hunk:
```diff
+ import unicodedata
- keywords = ['sair', 'parar', 'remover', 'descadastrar', 'stop', 'unsubscribe']
- msg_clean = message.lower().strip()
+ keywords = ['sair', 'parar', 'remover', 'descadastrar', 'nao quero', 'cancelar', 'bloquear', 'stop', 'unsubscribe']
+ msg_clean = unicodedata.normalize('NFKD', message.lower().strip())
+ msg_clean = msg_clean.encode('ASCII', 'ignore').decode()
```

### `electron/package.json` e `electron/package-lock.json`

- `npm audit fix --force` atualizou dependências com breaking major:
  - `electron`: `^30.0.0` -> `^42.0.1`
  - `electron-builder`: `^25.0.0` -> `^26.8.1`
- `npm run build` validou o empacotamento.

### `Instalar_Motor.bat`

Hunk:
```diff
- cd /d "c:\Users\user\Desktop\SigmaLeeds\whatsapp-motor"
+ cd /d "%~dp0whatsapp-motor"
```

### `SigmaHub.bat`

- Usa `%~dp0` para a raiz do projeto.
- Remove PATH absoluto de Python 3.11.
- Valida Python com `where python` e `python --version`.

Hunk:
```diff
- cd /d "C:\Users\user\Desktop\SigmaLeeds"
- set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311\;%LOCALAPPDATA%\Programs\Python\Python311\Scripts\
+ cd /d "%~dp0"
+ where python >nul 2>&1
+ python --version >nul 2>&1
```

### `app.py`

Hunk:
```diff
- print(msg)
+ logger.warning(msg)
- print(msg2)
+ logger.info(msg2)
```

### `static/style.css`

- Linhas auditadas foram trocadas para tokens existentes.

Hunks principais:
```diff
- background: #fff1f0;
+ background: var(--color-danger-bg);
- color: #cf1322;
+ color: var(--color-danger-text);
- background: #E5DDD5;
+ background: var(--color-bg-tertiary);
- background: #DCF8C6;
+ background: var(--color-success-bg);
- color: #111;
+ color: var(--color-text-primary);
- color: #FFFFFF;
+ color: var(--color-bg-primary);
- background: #fff;
+ background: var(--color-bg-primary);
- background: #ffe399;
+ background: var(--color-warning-bg);
- border: 1px solid #ffd066;
+ border: 1px solid var(--color-warning);
- background: #ffc8d0;
+ background: var(--color-danger-bg);
```

