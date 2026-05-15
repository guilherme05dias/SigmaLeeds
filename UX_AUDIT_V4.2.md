# Auditoria UX/UI ZapManager Pro v4.2

Data: 2026-05-15
Auditor: Explore agent (auditoria sistemática read-only)
Escopo: templates/index.html, static/script.js, static/style.css contra DESIGN.md e AGENTS.md

## Resumo

O frontend apresenta arquitetura sólida alinhada com o design system Airtable-inspired, com tokens CSS bem estruturados e componentes responsivos. Pontos fortes: handlers JS bem mapeados (todas as ~45 funções existem), tabelas com estados visuais claros, modalidades de feedback (toast). Fraco: 3 violações críticas de design (hex hardcoded, emoji textual, Google Fonts), tokens CSS indefinido referenciado (`--color-bg-surface`), alert/confirm misturados com toast, 10+ estilos inline pesados que deveriam ser classes. Severidade: **Média-Alta (8/10)** — impacto estético/UX significativo, sem quebra funcional imediata.

---

## Top 10 Críticos

1. **Token CSS indefinido (`--color-bg-surface`) em script.js:511** — Referencia token que não existe em `:root`. Fallback undefined causa comportamento inesperado em inputs editáveis. **Fix:** Substituir por `var(--color-bg-input)` ou `var(--color-bg-primary)`.

2. **Emoji textual `↓` em botão de exportação (index.html:244)** — Viola regra de nenhum emoji em UI. Deve usar ícone lucide. **Fix:** `<i data-lucide="download" size="16"></i>` no lugar de `↓`.

3. **Google Fonts importado (index.html:10)** — `fonts.googleapis.com/css2?family=JetBrains+Mono` viola regra de font stack vanilla. **Fix:** Remover `<link>` ou usar fonte do sistema.

4. **Cores hardcoded fora de :root** — 3 instâncias: `background:#1C1C1E` (monitor-logs, index.html:347), `background:#d46b08` (btn-retry-failed, index.html:574), `color:#0b6e1f` (conex sucesso, index.html:501). **Fix:** Criar tokens `--color-monitor-bg`, `--color-warning-dark`, usar vars.

5. **alert()/confirm() para ações críticas** — 16 chamadas em script.js (ex.: lines 98, 152, 220, 343, 592, 662) deveriam usar `showToast()` ou modal confirmação. Cria inconsistência UX. **Fix:** Substituir por `showToast('...', 'warning')` + modal de confirmação reutilizável.

6. **Border-radius inconsistente** — 12 valores diferentes encontrados (4px, 6px, 8px, 12px, 20px, 50%, 999px). Regra: 6px componentes, 8px cards — alguns violam (botão 38px em linha 865, progress-bar 4px). **Fix:** Padronizar: 6px inputs/botões, 8px cards, 20px chips, 50% circles.

7. **Altura de botões fora do padrão** — `.btn-primary:44px` (ok), `.btn-danger:40px` (ok), mas modais têm height:38px (linhas 865, 871) — abaixo do mínimo 32px+ aceitável. **Fix:** Ajustar modais para 40px min.

8. **Estilos inline pesados (5-7 props)** — Múltiplos inputs em history filters (index.html:275, 279, 283, 287, 298) com `width:100%; height:36px; padding; border-radius; border; background; color;`. **Fix:** Criar classe `.history-input { ... }`.

9. **`--color-bg-surface` referência órfã** — Usado em script.js mas não definido em :root. Indica sincronização quebrada entre CSS e JS. **Fix:** Definir em :root ou refatorar JS.

10. **Labels singular/plural ambíguas** — "Prontos" vs singular em outras linhas, "Inválidos" vs output JS. Confuso em tabelas. **Fix:** Padronizar: "Válidos" ou "Prontos" + quantidade em parênteses.

---

## Por categoria

### Tokens/Cores
- `index.html:347` — `background:#1C1C1E` inline — cria var `--color-monitor-bg-dark`
- `index.html:501` — `color:#0b6e1f` inline — usar `var(--color-success-text)`
- `index.html:574` — `background:#d46b08; border-color:#d46b08` — criar `--color-warning-dark:#d46b08`
- `script.js:511` — `background: var(--color-bg-surface)` — **token indefinido**, substituir por `var(--color-bg-input)`

### Emojis (Violação de Regra)
- `index.html:244` — `↓ Exportar Relatório` — substituir por `<i data-lucide="download"></i>`
- Nenhum outro emoji literal encontrado.

### Border-radius
- Padrão cumpre bem (6px inputs/botões, 8px cards), mas outliers:
  - `.progress-bar-bg:4px` — muito pequeno, aumentar para 6px
  - Chips `.var-chip:20px` — aceitável (roundness proposital)
  - Modais `.onboarding-panel:8px` — correto
  - `.modal-content:12px` — um pouco alto, manter (é intenção)

### Botões
- `.btn-primary: height:44px` — acima do padrão (regra: 36px), mas aceitável para CTAs
- `.btn-danger: height:40px` — ok
- Modais em `.spintax-modal .btn:38px` — abaixo de 32px min (marginal)
- `index.html:70` — `min-height:40px` no btn-danger "Modelo" — ok

### Acessibilidade
- OK: botão fechar modal tem `aria-label="Fechar"` (linha 533)
- OK: attachment chip tem `aria-label="Remover anexo global"` (linha 154)
- OK: inputs têm labels no HTML (send-window, history filters)
- Atenção: chips de variáveis (nome, empresa, etc.) não têm aria-label — são buttons sem texto visível além do ícone + label. Considerar `aria-label="Inserir variável {nome}"`.
- Atenção: icon-only botões (PDF remover `icon-9` class) sem labels — adicionar aria-label

### Handlers órfãos/inexistentes
- **Todos os 45+ handlers referenciados no HTML existem em script.js**
- Amostra confirmada: `showPage()`, `openConnector()`, `uploadAttachment()`, `toggleDelay()`, `startCampaign()`, `loadHistory()`, `loadLicense()`
- **Sem funções órfãs detectadas**

### Estilos inline pesados
- `index.html:62-74` — grid 2-coluna com múltiplas props em divs → classe `.upload-header-row`
- `index.html:275, 279, 283, 287, 298` — inputs em history filters, cada um com 6-7 propriedades → **CRÍTICO**, criar `.history-filter-input`
- `index.html:347` — monitor-logs div com 7 propriedades → classe `.monitor-box-styled`
- `index.html:453-470` — label PDF upload com múltiplas props → `.pdf-upload-label`
- `script.js:508-513` — inline.cssText de 7 propriedades em makeEditable() → mover para classe CSS `.inline-edit-input`

### Estados de loading
- OK: upload carregando: spinner com mensagem (linha 292)
- OK: license: "Carregando..." placeholder (linha 361)
- OK: connector/onboarding: loader icons (linhas 440, 487)
- Atenção: export — botão muda texto para "Gerando..." mas pode parecer desativado (não há spinner visual)
- Atenção: startCampaign() — nenhum spinner enquanto `/api/campaign/start` está em voo
- Atenção: histórico — nenhum skeleton/loader enquanto `loadHistory()` carrega

### Strings (Português/Inglês)
- Exceto "Cancelar" e "OK" em alertas, **tudo em português**
- "Modelo" vs "Planilha modelo" — ambíguo. Fix: sempre "Planilha modelo"
- `script.js:390` — `"sera(o) enviada(s)"` (acento faltando em será) — corrigir para `"serão enviadas"`

### Inconsistências entre páginas
- Campanhas: padding esquerdo 48px, header h1 sem borda
- Histórico: mesmos paddings, tabela com thead sticky — OK
- Monitor: padding 48px, logs em monospace — coerente
- Licença: cards sem bordas visíveis (apenas shadow) — diverge de outros cards que têm 0.5px border
- Conclusão: licença card é mais suave (sem border) — decisão estética, documentar com comentário CSS

### Outros
- Font stack: `system-ui, Segoe UI, Roboto` sem Google Fonts em CSS, mas HTML importa JetBrains Mono do googleapis ← remover
- Sidebar: 220px fixo + margin-left 220px em main-content — OK
- Z-index: 1 (table header), 1000 (modais), 2000 (spintax), 3000 (onboarding) — bem escalonado
- Modal spintax em `.modal-overlay` com z:2000, `.modal` em z:1000 — spintax sobrepõe corretamente
- Sem Bootstrap/Tailwind detectado

---

## Quick wins (≤30 min cada)

1. **Remover Google Fonts (JetBrains Mono)** — monospace já disponível em system fonts. Linha 10 do index.html deletar, referência em style.css trocar por fallback.

2. **Criar classe `.history-filter-input`** — consolidar 5 inputs com estilos inline em uma classe CSS.

3. **Substituir emoji `↓` por lucide icon** — index.html:244 trocar por `<i data-lucide="download" size="16"></i>`.

4. **Definir `--color-bg-surface` em :root** — adicionar a :root (cópia de `--color-bg-input`), ou refatorar script.js:511.

5. **Converter 3 cores hardcoded em tokens** — criar `--color-monitor-bg-dark:#1C1C1E`, `--color-warning-dark:#d46b08`, aplicar em index.html.

6. **Padronizar alert/confirm para showToast** — 16 instâncias, substituir por `showToast()` + modal reutilizável.

7. **Adicionar aria-label a chips + icon buttons** — percorrer 15+ botões sem texto visível, adicionar labels.

8. **Criar `.monitor-box-styled` e `.pdf-upload-label`** — consolidar 2 elementos com inline styles pesados.

9. **Corrigir typo "sera(o)" → "serão"** — script.js:390 correção trivial.

10. **Documentar divergência visual licença card** — adicionar comentário CSS explicando por que `.license-card` não tem border.

---

## O que NÃO mexer

- **Border-radius 20px em chips** — intenção design: pill-shaped, correto conforme Airtable pattern
- **Height 44px em btn-primary** — oversized é proposital para CTAs (melhor hit target)
- **Lucide icons via `<i data-lucide>`** — sistema funcionando bem
- **Z-index escalonamento** — 1000/2000/3000 é convenção clara e funciona sem conflitos
- **Sidebar 220px + margin-left 220px** — layout double-offset correto
- **SSE logs com max 200 linhas** — performance decision justificada

---

Severidade geral: Média-Alta (8/10). Prazo estimado para correção: 3–4 horas cumprindo quick wins + refactors estruturais.
