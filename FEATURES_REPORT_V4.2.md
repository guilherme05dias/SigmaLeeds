# FEATURES_REPORT_V4.2.md

## Resumo

Implementadas as três features pendentes do Sprint 2 em commits locais, sem `git push`, sem `--no-verify` e sem `amend`. Não foi aberto navegador e `python app.py` não foi executado.

## Features

| Feature | Status | Arquivos alterados | Testes adicionados | Smoke pendente |
|---|---|---|---|---|
| Planilha modelo | ✅ | `app.py`, `criar_planilha_modelo.py`, `database/services/template_xlsx.py`, `templates/index.html`, `static/script.js` | Não | Sim |
| M7 Onboarding | ✅ | `app.py`, `templates/index.html`, `static/script.js`, `static/style.css` | Não | Sim |
| M8 Janela de horário | ✅ | `api/models.py`, `app.py`, `database/services/send_window.py`, `tests/test_send_window.py`, `templates/index.html`, `static/script.js`, `static/style.css` | `tests/test_send_window.py` | Sim |

## Commits

| Commit | Título | Escopo |
|---|---|---|
| `aef8e56` | `feat: botao de download da planilha modelo` | Rota protegida `/api/template/contacts.xlsx` + botão de download |
| `ab086d7` | `feat: wizard de onboarding (M7)` | Wizard 4 passos persistido em `system_config.onboarding_completed` |
| `50d42ee` | `feat: janela de horario de envio (M8)` | Config `send_window`, pausa automática do runner e testes |

## Decisões

- A rota da planilha modelo gera XLSX em memória via `openpyxl`, sem servir o arquivo versionado da raiz.
- O wizard reaproveita `/api/connector` para QR/status do WhatsApp; não foram criados endpoints paralelos de conexão.
- A configuração de M8 usa a chave `system_config.send_window`, conforme o plano principal.
- O helper de M8 ficou em `database/services/send_window.py` para manter a estrutura existente do projeto.
- Dias seguem `datetime.weekday()`: `0=segunda` até `6=domingo`; default é segunda a sexta `[0,1,2,3,4]`.
- A janela que cruza meia-noite é suportada; madrugada pertence ao dia em que a janela começou.
- O Plan agent sugeriu rejeitar overnight na versão mínima, mas o plano do usuário exigia teste de cruzamento de meia-noite; prevaleceu o requisito explícito.

## Validação

```text
python -c "import app; print('OK')"
OK

python -m pytest tests/ license/ -v
13 passed in 1.72s
```

## Smoke Manual Pendente

- Subir o app localmente e clicar em `Modelo` para confirmar download e abertura do `.xlsx` no Excel.
- Resetar `system_config.onboarding_completed` e conferir o wizard de 4 passos, incluindo QR e conclusão.
- Configurar janela ativa fora do horário atual e confirmar que a campanha fica com status `Aguardando janela de horário`.
- Configurar janela ativa dentro do horário atual e confirmar envio normal.

## Diff Resumido

### Planilha Modelo

```diff
+ @app.get("/api/template/contacts.xlsx")
+ build_template_workbook().save(BytesIO())
+ downloadTemplateWorkbook()
+ <button ... onclick="downloadTemplateWorkbook()">Modelo</button>
```

### M7 Onboarding

```diff
+ GET /api/onboarding/status
+ POST /api/onboarding/complete
+ <div id="onboardingWizard" data-step="1">
+ initOnboarding()
+ system_config.onboarding_completed = "1"
```

### M8 Janela De Horário

```diff
+ normalize_send_window_config()
+ is_within_window(now, window)
+ seconds_until_window_opens(now, window)
+ GET/POST /api/config/send-window
+ if not _wait_for_send_window(): break
+ tests/test_send_window.py
```

## Reversão

- Planilha modelo: `git revert aef8e56`
- M7 onboarding: `git revert ab086d7`
- M8 janela de horário: `git revert 50d42ee`

## Observações

- `PLAN_GPT_FEATURES.md` foi mantido como documento de planejamento e deve ser versionado junto deste relatório para deixar o working tree limpo.
