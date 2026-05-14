# Build — ZapManager Pro v4.0

## Pré-requisitos
- Node.js 18+ instalado
- Python 3.8+ instalado
- PyInstaller: `pip install pyinstaller`
- Pillow (para gerar ícone): `pip install Pillow`

## Gerar ícone placeholder (primeira vez)

```powershell
pip install Pillow
python scripts/criar_icone.py
```

Isto cria `resources/icon.ico`.

## Modo desenvolvimento (sem empacotar)

```powershell
cd electron
npm install
npm start
```

O Electron irá:
1. Exibir splash screen
2. Spawnar `python app.py` em background
3. Fazer scan nas portas `5050–5099` até encontrar o FastAPI
4. Abrir a janela principal com a interface

> **Observação:** O `app.py` hoje abre o navegador padrão automaticamente (via `webbrowser.open()`).
> Quando rodado dentro do Electron, isso cria uma janela duplicada no Chrome.
> Para uma experiência limpa, remova o bloco `open_browser()` do final do `app.py` quando empacotar.

## Build do instalador Windows

```powershell
# 1. Build do frontend React (se aplicável)
npm run build  # na raiz do projeto

# 2. Empacotar Python com PyInstaller
pyinstaller --onefile --noconsole --name app `
  --distpath electron/resources/engine `
  --add-data "templates;templates" `
  --add-data "static;static" `
  --add-data "database;database" `
  --add-data "license;license" `
  --add-data "api;api" `
  --add-data "whatsapp-motor;whatsapp-motor" `
  app.py

# 3. Build do Electron
cd electron
npm install
npm run build:installer
```

Instalador gerado em: `electron/dist/ZapManager Pro Setup 4.0.0.exe`

## Arquitetura de processos

```
Electron (main.js)
  └─ spawn python app.py
       └─ spawn node whatsapp-motor/server.js  (já feito pelo app.py)
```

O Electron NÃO spawna o Node diretamente, porque o `app.py` já faz isso em
`@app.on_event("startup")`. Isso evita conflito na porta 3001.

## Verificar após instalar
- App abre com splash screen
- Interface carrega normalmente
- QR Code aparece ao conectar WhatsApp
- Fechar o app encerra o Python em background (e o Node por consequência, pois é spawned pelo Python)

## Teste de aceitação em modo desenvolvimento

```powershell
cd electron
npm install
npm start
```

Verificar:
- Splash screen "Iniciando o servidor..." aparece
- Após alguns segundos, janela principal abre com a interface
- Interface funciona normalmente (QR Code, campanhas, etc.)
- Fechar a janela encerra Python e Node:

```powershell
# Após fechar — não deve aparecer nada:
Get-Process python -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue
```
