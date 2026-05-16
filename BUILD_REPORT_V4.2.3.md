# BUILD_REPORT_V4.2.3

Data: 2026-05-15
Instalador: `electron/dist/ZapManager Pro Setup 4.2.3.exe` (178 MB / 186323743 bytes)

## Mudancas desde v4.2.2

```text
c776136 chore: pre-flight check de instalacao e checklist de distribuicao
dfca7e9 feat: diagnostico e robustez no launch do browser
```

## Incluido no snapshot

- `electron/package.json` atualizado para `4.2.3`.
- Janela Electron atualizada para `ZapManager Pro v4.2.3`.
- Browser launch mais robusto: Edge/Chrome x86/x64, Chrome user-local, Edge Beta/Dev.
- Diagnostico em runtime: Node `GET /diagnostics` e Python `GET /api/diagnostics`.
- `scripts/verify_install.ps1` para validar maquina destino antes da instalacao.
- `build.md` com checklist anti-stale para `whatsapp-motor/server.js`.

## Build executado

```text
Copy limpo: whatsapp-motor -> electron/resources/engine/whatsapp-motor
pyinstaller app.spec --distpath electron/resources/engine --clean
Copy limpo pos-PyInstaller: whatsapp-motor -> electron/resources/engine/whatsapp-motor
cd electron; npm run build:installer
```

## Checklist de validacao

```text
1. app.exe origem: LastWriteTime 15/05/2026 20:52:26, Length 55777629
2. diff fonte vs engine/server.js: vazio
2b. diff fonte vs win-unpacked/server.js: vazio
3. ZAP_ATTACHMENTS_ROOT no win-unpacked/server.js: 3 ocorrencias
4. resources/node/node.exe: 69804184 bytes
5. whatsapp-web.js/index.js no bundle: True
6. Smoke app.exe: / = 200, /api/diagnostics = 200
   Node reachable=True, browser found=True, browser=Microsoft Edge
```

## Validacao automatizada

```text
python -m pytest tests/ license/ -v -> 16 passed in 2.45s
bash scripts/ux_check.sh -> alvos zerados; alert/confirm = 23 (adiado)
```

## Pre-flight local

```text
powershell -ExecutionPolicy Bypass -File scripts/verify_install.ps1
Resultado: Windows 11 OK, Edge encontrado, disco OK, escrita OK,
portas 5050/3001 livres, .NET 4.5+ OK.
```

## Instrucoes para operador

1. Copiar `electron/dist/ZapManager Pro Setup 4.2.3.exe` para a maquina destino.
2. Antes de instalar, rodar `scripts/verify_install.ps1` nessa maquina.
3. Se o pre-flight passar, executar o instalador.
4. No SmartScreen, usar **More info -> Run anyway** (instalador nao assinado).
5. Abrir **ZapManager Pro**, conectar WhatsApp por QR e validar `/api/diagnostics` se houver falha.

## Avisos

- `author is missed in the package.json` do electron-builder segue nao-bloqueante.
- `DEP0190` vem do electron-builder/Node durante build, nao bloqueia o instalador.
