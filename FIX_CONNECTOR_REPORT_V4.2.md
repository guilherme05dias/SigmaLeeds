# FIX_CONNECTOR_REPORT_V4.2

## Escopo

Correcoes aplicadas no fluxo de conexao do motor Node para evitar limbo de sessao LocalAuth corrompida, padronizar o contrato do conector e permitir reset manual pela UI.

## Commits

1. `0c673d7 fix: watchdog de sessao corrompida no motor WhatsApp`
2. `549f1a9 fix: padroniza contrato de /api/connector com envelope success/data`
3. `44d670d feat: botao de resetar sessao + propagacao de logs do motor`

## Diff resumido

- `whatsapp-motor/server.js`
  - Adicionado watchdog de 45s apos `client.initialize()`.
  - Se nao houver `qr` nem `ready`, remove `appDataDir/session`, destroi o client e reinicializa.
  - Limite de 2 tentativas; depois disso registra erro claro e aguarda intervencao.
  - Adicionada rota `POST /reset-session` para limpar sessao e gerar novo QR.

- `app.py`
  - `/api/connector` agora sempre retorna `{success, data}`.
  - `data` contem `connected`, `status`, `qr` e `node_online`.
  - Adicionada rota protegida `POST /api/whatsapp/reset`.
  - stdout/stderr do Node agora sao filtrados e enviados ao `publish_log_threadsafe`.

- `templates/index.html`
  - Adicionado aviso de Node offline no modal do conector.
  - Adicionado aviso de Node offline no wizard de onboarding.
  - Adicionado link discreto: `Sessao travada? Resetar e gerar novo QR`.

- `static/script.js`
  - Removida defesa contra contrato antigo de `/api/connector`.
  - Modal e onboarding agora usam `res.data`.
  - Adicionada funcao `resetWhatsAppSession()`.

- `static/style.css`
  - Adicionada classe `.btn-reset-session` usando tokens CSS existentes.

## Validacao executada

- Antes das alteracoes: `python -m pytest tests/ license/ -v`
  - Resultado: `13 passed`.

- Node: `node --version`
  - Resultado: `v24.12.0`; `fs.rmSync(..., { recursive: true, force: true })` e seguro.

- Sintaxe Node: `node --check whatsapp-motor/server.js`
  - Resultado: OK.

- Import Python: `python -c "import app; print('OK')"`
  - Resultado: `OK`.

- Depois das alteracoes: `python -m pytest tests/ license/ -v`
  - Resultado: `13 passed`.

- Smoke programatico sem abrir navegador:
  - Porta `5050`: havia instancia antiga em background retornando contrato antigo.
  - Porta `5051`: validou a versao atual.
  - `unauth_status: 401`
  - `/api/connector`: retornou `{success: true, data: {..., node_online: true}}`.

## Instrucao ao operador

Antes do primeiro uso da nova versao, apagar a sessao atual em `%LOCALAPPDATA%/ZapManagerPro/session/` ou usar o link `Sessao travada? Resetar e gerar novo QR` no modal do conector. Isso evita reaproveitar uma sessao criada antes do watchdog.

## Observacao

Nao foi feito `git push`, nao foi usado `--no-verify`, e nao foi usado `git commit --amend`.

## Ajuste de placeholders do preview

- Chamadas `insertVar` alteradas:
  - `templates/index.html:121` -> `{nome}`
  - `templates/index.html:122` -> `{empresa}`
  - `templates/index.html:123` -> `{numero}`
  - `templates/index.html:124` -> `{adicional1}`
  - `templates/index.html:125` -> `{adicional2}`
  - `templates/index.html:126` -> `{adicional3}`
  - `static/script.js:291` -> chips dinamicos de extras usam `{<key>}`

- Regex de spintax do frontend:
  - `static/script.js:456`: `/\{([^{}]+\|[^{}]*)\}/g`
  - Bate com o backend em `database/services/template_service.py`, que usa `r'\{([^{}]+\|[^{}]*)\}'`.
  - O preview escolhe sempre a primeira opcao para ficar previsivel enquanto o usuario digita.

- Validacao:
  - `python -m pytest tests/ license/ -v` -> `13 passed`
  - `python -c "import app; print('OK')"` -> `OK`
