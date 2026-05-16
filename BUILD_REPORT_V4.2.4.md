# BUILD_REPORT_V4.2.4

Data: 2026-05-16
Instalador: `electron/dist/ZapManager Pro Setup 4.2.4.exe` (310 MB)

## Por que essa versão

A v4.2.3 falhava em algumas máquinas porque o Puppeteer tentava lançar o Microsoft Edge stable, e o handshake do whatsapp-web.js com Edge headless **silenciosamente não completava** (Edge abria, mas nem `qr` nem `ready` event disparavam). Como o Puppeteer foi desenvolvido contra Chrome, a única forma de garantir funcionamento em qualquer máquina Windows é **embutir o Chromium** no instalador.

## Mudanças

| Arquivo | O que mudou |
|---|---|
| `electron/resources/chromium/` | **Novo**: Chrome for Testing 148.0.7778.167 (414 MB descomprimido) |
| `whatsapp-motor/server.js` | `getChromePath()` agora prioriza: `ZAP_BROWSER_PATH` env > `ZAP_BUNDLED_CHROMIUM` env > Chrome do sistema > Edge (fallback). Watchdog ampliado para 90s × 3 tentativas (cold start de Chromium pode ser lento) |
| `app.py` | `_spawn_node_with_job` infere `ZAP_BUNDLED_CHROMIUM` automaticamente quando frozen (PyInstaller) e passa para o Node |
| `electron/main.js` | Passa `ZAP_BUNDLED_CHROMIUM=<resources>/chromium/chrome.exe` ao spawn do app.exe |
| `electron/package.json` | Versão 4.2.4, `extraResources` inclui `chromium/` |
| `.gitignore` | Adiciona `electron/resources/chromium/` (artefato de build, não vai pro git) |
| `scripts/verify_install.ps1` | Browser do sistema vira **opcional**. Espaço em disco mínimo subiu para 800MB |

## Validação executada

| Check | Resultado |
|---|---|
| `python -m pytest tests/ license/ -v` | 16 passed |
| `node --check whatsapp-motor/server.js` | OK |
| `node --check electron/main.js` | OK |
| `python -c "import app; print('OK')"` | OK |
| PyInstaller `--clean` | OK (app.exe 53MB) |
| `server.js` sync source ↔ engine | OK |
| `electron-builder` | OK (310 MB) |
| **Smoke do app.exe**: Chromium embutido detectado | ✅ `browser.name: "Google Chrome"`, path apontando para `resources/chromium/chrome.exe` |
| **Smoke do app.exe**: QR Code gerado | ✅ em ~30-50s no boot inicial |

## Conteúdo do bundle

```
electron/dist/win-unpacked/
├── ZapManager Pro.exe                    (217 MB, Electron + Chromium do Electron)
├── resources/
│   ├── engine/
│   │   ├── app.exe                       (53 MB, Python+FastAPI bundle)
│   │   └── whatsapp-motor/
│   │       ├── server.js                 (com fix ZAP_BUNDLED_CHROMIUM, 5 ocorrências)
│   │       └── node_modules/             (puppeteer, whatsapp-web.js)
│   ├── node/
│   │   └── node.exe                      (67 MB, Node 20.18 portátil)
│   └── chromium/                         ← NOVO
│       └── chrome.exe                    (414 MB descomprimido, Chrome 148.0.7778.167)
```

## Instruções para o operador

1. Copiar `ZapManager Pro Setup 4.2.4.exe` (310 MB) para máquina destino.
2. (Opcional) Rodar `scripts/verify_install.ps1` antes de instalar.
3. Executar instalador. SmartScreen → Mais informações → Executar mesmo assim.
4. Após instalar, abrir do menu Iniciar. Splash screen aparece, depois UI.
5. Sidebar → Conectar WhatsApp → aguardar QR (até 90s no primeiro boot porque Chromium nunca rodou nessa máquina).
6. Escanear QR no celular → status fica "Conectado".

## Garantias

- **Funciona em máquina sem Chrome nem Edge instalados** (Chromium do bundle é usado).
- **Funciona em máquina com Chrome instalado** (`getChromePath` ainda pode usar o do sistema, mas o env var do Electron tem prioridade).
- **Funciona em máquina onde Edge falhou (caso v4.2.3)** — agora ignora Edge e usa Chromium próprio.

## Limitações conhecidas

- Instalador ficou maior (178 → 310 MB) por causa do Chromium embutido. Trade-off aceito em troca de robustez.
- Primeiro boot do WhatsApp é ~30-50s (Chromium precisa baixar/cachear assets do WhatsApp Web). Boots subsequentes são <10s.
- Avisos não-bloqueantes no build: `author is missed` no package.json (cosmético), `DEP0190` do Node (vem do electron-builder, não do código próprio).

## Reversão

- Voltar para v4.2.3 (sem Chromium embutido): `git checkout 9c3e3dc` e rebuild. Mas v4.2.3 só funciona em máquinas onde Edge stable consegue completar o handshake do whatsapp-web.js — sem garantia.
