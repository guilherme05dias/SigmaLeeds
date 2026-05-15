# BUILD_REPORT_V4.2.1

Data: 2026-05-15
Instalador: `electron/dist/ZapManager Pro Setup 4.2.1.exe` (178 MB)

## Mudanças desde v4.2.0

```
0b47e70 fix: protege logging uvicorn em app windowed
1a434a0 chore: bump versao para 4.2.1
a6d2b09 fix: polimento dark mode - badges, transição, marcador de duplicata
bca1c45 feat: modo dark com toggle persistente
02fb017 fix: histórico mostra contadores reais e ux_check corrige alert/confirm
4741439 refactor: move inline styles pesados para classes CSS
186494d docs: relatorio de auditoria UX e script de validacao
e169b70 chore: limpeza estrutural UX/UI v4.2 + desativa Janela de horario
6782e1e fix: chip visual com botao de remover para anexo global
1ea70d5 fix: implementa uploadAttachment para anexo global
4858f51 fix: anexo global e anexo por linha enviam os dois
1d264f6 fix: Node motor resolve attachments root via env var
```

## Destaques funcionais

- **Anexo global** funciona (foi quebrado em v4.2.0 por path resolve relativo).
- **Anexo per-line + global** envia os dois.
- **Janela de horário** desativada na UI (backend intacto).
- **Modo dark** completo com toggle persistente e badges adaptativos.
- **Histórico** mostra contadores reais (campaigns.total_contacts era 0).
- **Crash em PyInstaller noconsole** corrigido (`stdout=None` → sink em devnull).

## Versões / ambiente de build

- Python: 3.12.10 (PyInstaller `--clean`)
- Node: v20.18.0 (portátil em `electron/resources/node/node.exe`)
- Electron: 42.0.1
- electron-builder: 26.8.1

## Validação executada

- `python -m pytest tests/ license/ -v` → 16 passed (antes do build)
- Smoke `electron/resources/engine/app.exe` standalone → HTTP 200 em 127.0.0.1:5050
- `bash scripts/ux_check.sh` → contadores-alvo zerados
- Bundle final em `electron/dist/win-unpacked/`:
  - `ZapManager Pro.exe` 217 MB
  - `resources/engine/app.exe` 54 MB (timestamp pós-fix do `stdout`)
  - `resources/engine/whatsapp-motor/server.js` + node_modules
  - `resources/node/node.exe` 67 MB

## Instruções para o operador

1. Copiar `electron/dist/ZapManager Pro Setup 4.2.1.exe` (178 MB) para a máquina destino (USB / rede / OneDrive).
2. Executar. Windows SmartScreen vai mostrar "Windows protected your PC" (instalador não assinado): clicar em **More info → Run anyway**.
3. NSIS pergunta diretório de instalação (não-silent).
4. Após instalar, abrir pelo menu Iniciar **ZapManager Pro**.
5. Trial de 7 dias é ativado no primeiro boot. Para licença permanente, copiar o Hardware ID da aba Licença e gerar chave com `keygen.py` usando a `private_key.pem` do operador.

## Avisos não-bloqueantes

- `author is missed in the package.json` do electron — trivial, adicionar `"author"` quando quiser.
- `DEP0190` do Node — vem do `electron-builder`, não do nosso código.

## Reversão

- Voltar para v4.2.0: `git checkout bcf448c` e rebuildar.
- Ou: distribuir `electron/dist/ZapManager Pro Setup 4.2.0.exe` (178 MB, datado 2026-05-15 10:34).
