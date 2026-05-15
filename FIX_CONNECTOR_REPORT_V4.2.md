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

## Campos adicionais na planilha/importador

Planilha modelo:
| Antes | Depois |
|---|---|
| Nome, Numero, Status, Empresa, Observacao, DataEnvio | Nome, Numero, Empresa, Adicional1, Adicional2, Adicional3 |

Chips da UI:
| Antes | Depois |
|---|---|
| nome, empresa, numero, adicional1, adicional2, adicional3 | nome, numero, empresa, adicional1, adicional2, adicional3 |

Validacao:
- `python -m pytest tests/ license/ -v` -> `15 passed`
- `python -c "import app; print('OK')"` -> `OK`
- Headers gerados por `build_template_workbook()` -> `['Nome', 'Numero', 'Empresa', 'Adicional1', 'Adicional2', 'Adicional3']`

## Import de contatos: duplicatas e erros visiveis

| Caso | Antes | Depois |
|---|---|---|
| Phone duplicado | Ignorado pelo `INSERT OR IGNORE` sem contagem | `duplicates_skipped` calculado e exibido no card DUPLICADOS |
| Phone invalido/vazio | Ficava em `errors`, sem detalhe acionavel na UI | API retorna `error_count`/`errors[:50]`; UI mostra invalidos e toast |
| Blacklist | Contava separado, sem entrar no alerta pos-import | Toast inclui `skipped_blacklist` quando houver descarte |

Validacao:
- `python -m pytest tests/ license/ -v` -> `16 passed in 3.05s`.
- `python -c "import app; print('OK')"` -> `OK`.
- Toast novo: `Atencao: N duplicada(s), M com erro, K em blacklist ignoradas. Veja o console para detalhes.`

## Import com phones repetidos por empresa

| Caso | Antes | Depois |
|---|---|---|
| Mesmo phone na campanha | `idx_contacts_unique` bloqueava e o import descartava com `INSERT OR IGNORE` | Migration v9 remove o indice unico; todas as linhas validas entram |
| Contagem de duplicados | `duplicates_skipped` indicava descarte | `duplicates_detected` e informativo; mensagens duplicadas serao enviadas |
| UI | Card amarelo/toast de descarte | Card azul/info, toast de importacao e linhas `.row-duplicate` na tabela |

Validacao:
- `python -m pytest tests/ license/ -v` -> `16 passed in 2.70s`.
- `python -c "import app; print('OK')"` -> `OK`.

**ATENCAO:** enviar varias mensagens em sequencia para o mesmo numero aumenta risco de bloqueio pelo WhatsApp; o operador deve avaliar a lista antes de iniciar.

## UX Campanhas: remover `{numero}` e planilha

Linhas alteradas:
- `templates/index.html:123 -> 130`: placeholder removeu `{numero}` e virou `Ola {nome}, a {empresa} tem uma novidade...`.
- `templates/index.html:126 -> removida`: chip `numero` foi retirado dos chips fixos.
- `templates/index.html:76 -> 77-83`: summary ganhou titulo da planilha e botao `Remover planilha`.
- `static/script.js:305 -> 340`: `defaultVars` nao inclui mais `numero`.
- `static/script.js:501 -> 533-536`: `substitutions` nao substitui mais `numero`.
- `static/script.js:246-247 -> 247-251/280-300`: import oculta upload, mostra filename e `removeSpreadsheet()` reseta a UI.
- `static/style.css:208-238`: estilos `.summary-header`, `.summary-title` e `.btn-link-danger` usando tokens existentes.

Validacao:
- `python -m pytest tests/ license/ -v` -> `16 passed in 2.51s`.

## UX: emojis substituidos por Lucide

| Arquivo:linha | Antes | Depois |
|---|---|---|
| `templates/index.html:132-136` | `nome/empresa/adicional` com emojis | `user`, `building-2`, `plus` |
| `templates/index.html:139` | emoji de variacao | `shuffle` + `Variacao` |
| `templates/index.html:524` | simbolo de fechar historico | `x` com `aria-label=Fechar` |
| `templates/index.html:590` | emoji de alerta spintax | `alert-triangle` |
| `static/script.js:399` | emoji de anexo PDF | `paperclip` |
| `static/script.js:409/418` | simbolo de remover PDF/contato | `x` |
| `static/script.js:1430-1436` | simbolo de remover opcao | `x` + `lucide.createIcons()` |

Validacao:
- `rg -n "<emoji-list>" templates/index.html static/script.js static/style.css` -> sem resultados.
- `python -m pytest tests/ license/ -v` -> `16 passed in 2.23s`.

## Ajuste visual dos icones Lucide

- Antes: SVGs dos chips e botoes pequenos podiam renderizar maiores que o texto.
- Depois: `.var-chip` tem `gap: 6px`; SVG interno fica fixo em `14x14`.
- `.btn-danger` e `.btn-link-danger` restringem Lucide para `14x14`.
- `.btn-close-modal` restringe Lucide para `14x14`.
- `.icon-9` força o `x` do botao inline de remover PDF para `9x9`, alinhado ao pai de `14px`.
- Visual esperado: icone e texto do chip com proporcao uniforme e respiro consistente.

## Remocao de contato recalcula cards

- Antes: `removeContact` removia a linha do DOM, mas cards e flag `REPETIDO` ficavam stale.
- Depois: `updateImportCards(contacts)` recalcula Total, Prontos, Invalidos, Blacklist e Duplicados pelo array local.
- `removeContact` muta `window.importedContacts`, re-renderiza a tabela e chama `updateImportCards`.
- Re-render da tabela recalcula `.row-duplicate`, removendo `REPETIDO` quando o phone deixa de repetir.
- `removeContactAttachment` tambem chama `updateImportCards` por consistencia do fluxo.
- Validacao: `python -c "import app; print('OK')"`; `node --check static/script.js`; `python -m pytest tests/ license/ -v` -> `16 passed in 2.20s`.

## Node attachments root via env

- Diagnostico: `ATTACHMENTS_ROOT` usava `path.resolve('./data/attachments')` com CWD `whatsapp-motor/`, apontando para pasta errada.
- Fix Node: `server.js` le `ZAP_ATTACHMENTS_ROOT`; fallback usa `__dirname/../data/attachments`.
- Fix Python: `_spawn_node_with_job` passa `ZAP_ATTACHMENTS_ROOT=str(UPLOAD_ROOT)` no `subprocess.Popen`.
- Guard preservado: validacao `startsWith(ATTACHMENTS_ROOT + path.sep)` continua intacta.
- Boot programatico: `node_ping: 200 {"ok":true}`.
- Validacao: `node --check whatsapp-motor/server.js`; `python -c "import app; print('OK')"`; `pytest` -> `16 passed in 2.42s`.

## Anexos global + por linha
| Entrada | Comportamento novo |
|---|---|
| nenhum / so global / so por linha | texto; texto+global; texto+por linha |
| ambos | 2 msgs: texto+por linha, depois global sem legenda; falha global secundaria fica WARN |
| Commit | `fix: anexo global e anexo por linha enviam os dois` |

## Upload de anexo global
- Diagnostico: `templates/index.html` chamava `uploadAttachment(this)`, mas a funcao nao existia em `static/script.js`.
- Fix: `uploadAttachment` valida 16 MB, envia `FormData` para `/api/upload-attachment`, atualiza `#attFileName` e mostra toast success.
- Bonus: `clearAttachment` chama `/api/clear-attachment` e reseta input/label para uso futuro.
- Commit: `fix: implementa uploadAttachment para anexo global`.

## UX do anexo global
- Antes: anexo carregado aparecia como texto pequeno solto, sem feedback visual forte nem acao de remover.
- Depois: `attachment-chip` mostra paperclip, nome com ellipsis e botao X ao lado do `Anexar Midia`.
- `uploadAttachment` revela o chip e reidrata Lucide; cancelamento/erro/tamanho invalido ocultam o chip.
- `clearAttachment` usa o botao X para chamar `/api/clear-attachment`, resetar input/label e esconder o chip.
- Commit: `fix: chip visual com botao de remover para anexo global`.

## UX audit estrutural V4.2
- Baseline `ux_check`: Google Fonts=1; Hex HTML=4; Emoji=3; bg-surface=1; alert/confirm=1; botao sem aria=5; `sera(o)`=1; inline>=5=1.
- Depois `ux_check`: Google Fonts=0; Hex HTML=0; Emoji=0; bg-surface=0; alert/confirm=1; botao sem aria=0; `sera(o)`=0; inline>=5=1.
- Conclusao: todos os 7 contadores-alvo zerados; contadores nao alvo permanecem fora desta fase.
- Validacao: `node --check static/script.js`; `python -c "import app; print('OK')"`; `pytest` -> `16 passed in 2.02s`.

## Refactor inline styles pesados
- Antes `ux_check`: inline>=5=1; Google Fonts=0; Hex HTML=0; Emoji=0; bg-surface=0; botao sem aria=0; `sera(o)`=0.
- Depois `ux_check`: inline>=5=0; demais contadores-alvo seguem 0; alert/confirm permanece 1.
- Filtros Historico, Monitor, edicao inline e remanescentes pesados migraram para classes CSS.
- `scripts/ux_check.sh`: contador inline corrigido para contar matches reais, nao a linha `0` do `grep -c`.
- Validacao: `node --check static/script.js`; `python -c "import app; print('OK')"`; `pytest` -> `16 passed in 4.97s`.
