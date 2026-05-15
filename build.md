# Build - ZapManager Pro v4.2.0

## Pre-requisitos
- Node.js 18+ instalado (apenas para BUILD; o instalador final nao exige Node no destino)
- Python 3.10+ com pip
- PyInstaller: `pip install pyinstaller pillow`

## Setup unico (primeira vez)

### 1. Icone

```powershell
python scripts/criar_icone.py
```

### 2. Node.js portatil (sera embutido no instalador)

```powershell
New-Item -ItemType Directory -Force -Path electron/resources/node
Invoke-WebRequest -Uri "https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip" -OutFile "node.zip"
Expand-Archive -Path node.zip -DestinationPath tmp_node
Copy-Item tmp_node/node-v20.18.0-win-x64/node.exe electron/resources/node/node.exe
Remove-Item -Recurse -Force tmp_node, node.zip
```

### 3. Dependencias do motor (serao empacotadas)

```powershell
cd whatsapp-motor
npm install --production
cd ..
```

### 4. Dependencias do Electron

```powershell
cd electron
npm install
cd ..
```

## Build completo

```powershell
# 1. PyInstaller - empacota Python em app.exe (com whatsapp-motor + node_modules)
pyinstaller app.spec --distpath electron/resources/engine --clean

# 2. Electron builder - gera o instalador NSIS
cd electron
npm run build:installer
cd ..
```

Instalador gerado em: `electron/dist/ZapManager Pro Setup 4.2.0.exe` (~150 MB).

## Validacao local (sem instalar)

Apos o build, verificar que:

```powershell
Test-Path electron/dist/win-unpacked/resources/engine/app.exe
Test-Path electron/dist/win-unpacked/resources/engine/whatsapp-motor/node_modules/whatsapp-web.js
Test-Path electron/dist/win-unpacked/resources/node/node.exe
```

Todos devem retornar `True`.

## Instalacao em outra maquina

1. Copiar `ZapManager Pro Setup 4.2.0.exe` para a maquina destino.
2. Executar. Windows SmartScreen vai mostrar "Windows protected your PC" - clique em "More info" -> "Run anyway" (instalador nao esta assinado).
3. NSIS pergunta diretorio de instalacao.
4. Apos instalar, abre pelo menu Iniciar "ZapManager Pro".
5. Splash screen aparece, depois a janela principal.
6. Conectar WhatsApp via QR code.

## Arquitetura de processos (runtime)

```text
Electron (ZapManager Pro.exe)
  -> spawn app.exe  (env: ZAP_NO_BROWSER=1, ZAP_NODE_EXE=<resources>/node/node.exe)
       -> spawn <resources>/node/node.exe server.js
```

## Troubleshooting

- "Servidor nao respondeu em 60s": o `app.exe` nao subiu. Cheque se ha antivirus bloqueando (PyInstaller bundles as vezes sao marcados como falso positivo).
- QR Code nao aparece: motor Node travou no startup. Use o botao "Resetar sessao" no modal de conector, ou apague `%LOCALAPPDATA%/ZapManagerPro/session/`.
- Mensagens nao enviam: confirme que Chrome ou Edge esta instalado na maquina.

## Validacao

```powershell
Test-Path electron/resources/node/node.exe
Test-Path whatsapp-motor/node_modules/whatsapp-web.js
python -m pytest tests/ license/ -v
```

Esperado: `node.exe` existe (~85 MB), `whatsapp-web.js` existe e a suite retorna `16 passed`.
