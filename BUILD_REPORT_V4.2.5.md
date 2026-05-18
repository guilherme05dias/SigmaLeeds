# BUILD_REPORT_V4.2.5

Data: 2026-05-18
Instalador: `electron/dist/ZapManager Pro Setup 4.2.5.exe` (310 MB)

## Mudanças desde v4.2.4

```
4589566 chore: label da sidebar reflete status real da licenca
74ca6e2 docs: registra validacao intervalo e modal
dbcf415 refactor: alert/confirm nativos -> showToast/confirmAsync
e863327 feat: intervalo minimo 30s + sugestao proporcional ao volume
6395836 feat: warm-up + consent obrigatorio para passar do limite de seguranca
1c70621 feat: single-tier de licenca + aviso de seguranca anti-banimento
```

## Destaques funcionais

### Anti-banimento (proteções novas)
- **Warm-up automático**: rastreia data da 1ª conexão WhatsApp, aplica limite escalonado (dia 1: 20 envios, dia 2: 40, dia 3: 80, dia 4-7: 150, dia 8-14: 250, dia 15+: usa safety_limit).
- **Consent modal obrigatório**: ao ultrapassar limite (warm-up ou safety), worker pausa campanha e abre modal "Aceito o risco" no frontend. Aceite registrado em `safety_consents` (data, tipo, contagem, timestamp).
- **Safety limit configurável**: default 300/dia. Usuário ajusta em Configurações de intervalo.
- **Intervalo mínimo 30s**: piso anti-rajada. Sugestão proporcional na UI baseada em volume da campanha + limite efetivo do dia.

### Modelo de licença
- **Single-tier**: 1 plano só (`pro`), todas features liberadas. Sem enforcement de limite por licença — só warm-up + safety.
- **Sidebar dinâmica**: label "Plano Business" estático sumiu. Agora mostra status real (`Trial: N dias`, `Licença ativa`, `Licença expirada`) com cor adequada.

### UX
- **Modal de confirmação reusável** (`confirmAsync`): 23 chamadas a `alert()` e `confirm()` nativos do browser substituídas por toast/modal alinhados ao design system.

### Mantido de v4.2.4
- Chromium 148.0.7778.167 embutido (414 MB descomprimido) — funciona em máquina sem Chrome nem Edge instalados.
- `ZAP_BUNDLED_CHROMIUM` env var passada pelo Electron ao Python ao Node motor.
- Watchdog 90s × 3 tentativas.

## Validação executada

| Check | Resultado |
|---|---|
| `python -m pytest tests/ license/ -v` | 16 passed |
| `node --check whatsapp-motor/server.js` | OK |
| `python -c "import app; print('OK')"` | OK |
| `bash scripts/ux_check.sh` | alert/confirm = **0** (era 23), demais alvos = 0 |
| PyInstaller `--clean` | OK |
| `server.js` sync source ↔ engine ↔ bundle | OK (3 ocorrências de `ZAP_BUNDLED_CHROMIUM`) |
| `electron-builder` | OK (310 MB) |
| Smoke app.exe standalone | HTTP 200 + QR gerado em <10s |

## Conteúdo do bundle

```
electron/dist/win-unpacked/
├── ZapManager Pro.exe                    (217 MB, Electron)
├── resources/
│   ├── engine/
│   │   ├── app.exe                       (53 MB, Python+FastAPI)
│   │   └── whatsapp-motor/
│   │       ├── server.js                 (com fix + watchdog 90s)
│   │       └── node_modules/             (puppeteer, whatsapp-web.js)
│   ├── node/node.exe                     (67 MB, Node 20.18 portátil)
│   └── chromium/chrome.exe               (~250 MB, Chrome 148)
```

## Instruções para o operador

1. Copiar `ZapManager Pro Setup 4.2.5.exe` (310 MB) para máquina destino.
2. (Opcional) Rodar `scripts/verify_install.ps1` antes de instalar.
3. Executar instalador. SmartScreen → Mais informações → Executar mesmo assim.
4. Após instalar, abrir do menu Iniciar.
5. Trial 7 dias ativado no primeiro boot. Para licença permanente, copiar Hardware ID da aba Licença e gerar chave com `python keygen_web.py` (abre em localhost:9876).
6. **Aquecimento ativo por 14 dias** — operador receberá modal de aceite ao ultrapassar limites diários. Pode desativar via API `/api/safety/warmup-toggle` se for número já antigo.

## Garantias

- Funciona em máquina sem Chrome nem Edge (Chromium embutido).
- Anti-banimento em duas camadas (warm-up + safety).
- Operador é forçado a aceitar conscientemente o risco antes de ultrapassar limites.
- Aceite fica auditável em `safety_consents`.

## Reversão

`git checkout 38a72d2` (v4.2.4) ou redistribuir `ZapManager Pro Setup 4.2.4.exe` se necessário.
