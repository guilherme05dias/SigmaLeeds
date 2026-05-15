# BUILD_REPORT_V4.2

## Versoes usadas

- Python: 3.12.10
- PyInstaller: 6.20.0
- Node.js de build: v24.12.0
- Node.js portatil embutido: v20.18.0
- Electron: ^42.0.1
- electron-builder: ^26.8.1

## Artefato final

- Instalador: `electron/dist/ZapManager Pro Setup 4.2.0.exe`
- Tamanho: 177.40 MB
- Bundle unpacked: `electron/dist/win-unpacked/`

## Checklist executado

- `python -m pytest tests/ license/ -v` -> 16 passed
- `python -m PyInstaller app.spec --distpath electron/resources/engine --clean` -> OK
- `electron/resources/engine/app.exe` -> existe, 53.01 MB
- Smoke direto do `app.exe` com `ZAP_NODE_EXE=electron/resources/node/node.exe` -> HTTP 200 em `127.0.0.1:5050`
- `cd electron; npm run build:installer` -> OK
- `electron/dist/win-unpacked/resources/engine/app.exe` -> True
- `electron/dist/win-unpacked/resources/engine/whatsapp-motor/server.js` -> True
- `electron/dist/win-unpacked/resources/engine/whatsapp-motor/node_modules/whatsapp-web.js` -> True
- `electron/dist/win-unpacked/resources/node/node.exe` -> True
- `electron/dist/win-unpacked/ZapManager Pro.exe` -> True

## Observacoes

- `electron/resources/node/node.exe`, `electron/resources/engine/` e `electron/dist/` ficam fora do git por `.gitignore`.
- O smoke do `.exe` unpacked do Electron nao foi executado para evitar abrir janela local; o backend empacotado foi validado diretamente.
- O build do electron-builder registrou aviso de `author` ausente e um deprecation warning do Node; ambos nao bloquearam o instalador.

## Instrucao ao operador

1. Copiar `electron/dist/ZapManager Pro Setup 4.2.0.exe` para a maquina destino.
2. Executar o instalador.
3. Se o SmartScreen aparecer, clicar em `More info` e depois `Run anyway`.
4. Escolher o diretorio no instalador NSIS.
5. Abrir `ZapManager Pro` pelo menu Iniciar.
6. Conectar o WhatsApp pelo QR code.
