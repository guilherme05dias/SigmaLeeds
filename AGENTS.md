# AGENTS.md — ZapManager Pro v4.0
> Lido pelo Antigravity em toda sessão. Nunca ignore este arquivo.

---

## 1. Identidade do projeto

Você está desenvolvendo o **ZapManager Pro v4.0**, um software desktop Windows para automação de disparos via WhatsApp Web.

**Stack:**
- Motor: Python + Selenium (arquivo `app.py` existente — não reescrever do zero)
- Interface: HTML/CSS/JS servido localmente (migração para Electron em andamento)
- Comunicação interna: FastAPI em localhost (substituindo Flask)
- Banco de dados: SQLite local (substituindo `.xlsx` como storage)
- Empacotamento final: PyInstaller + Electron Builder

**O que já existe e deve ser preservado:**
- `app.py` — motor Flask + lógica de automação (evoluir, não reescrever)
- `index.html` — interface atual (evoluir com o design system)
- Integração Node.js na porta `3001`
- Motor Selenium funcional

---

## 2. Design System — OBRIGATÓRIO

**Antes de criar ou modificar qualquer arquivo de interface, leia o `DESIGN.md` na raiz do projeto.**

Regras inegociáveis de UI:
- Use exclusivamente os tokens CSS definidos em `DESIGN.md` — nunca valores hex hardcoded
- Font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI"` — sem Google Fonts ou fontes externas
- Cores de status de campanha: verde=ENVIADO, amarelo=PENDENTE, azul=EM_PROCESSAMENTO, vermelho=ERRO, cinza=INVÁLIDO
- Border-radius padrão: `6px` (componentes) / `8px` (cards) — nunca valores arbitrários
- Altura de botões: `36px` (padrão) — nunca menor que `32px`
- Sidebar: `220px` de largura fixa
- Se um componente não estiver no `DESIGN.md`, use o padrão visual mais próximo já definido

**Não invente estilos. Não use frameworks CSS externos (Bootstrap, Tailwind etc.).**

---

## 3. Plano de ação — Fases e ordem

Siga rigorosamente esta ordem. Não pule fases. Não antecipe entregas de fases futuras.

### ✅ Fase 1 — MVP Comercial (em andamento)
Ordem de execução dentro da fase:

1. **[C] Módulo de Licença** — `license/` (independente, não toca em nada existente)
2. **[A] Migração para SQLite** — substituir `.xlsx` como storage principal
3. **[D] Migração Flask → FastAPI** — manter rotas existentes, trocar o framework
4. **[B] Empacotamento Electron** — empacotar tudo que já estiver funcionando

### 🔵 Fase 2 — Produto Completo (não iniciar até Fase 1 concluída)
- Múltiplas contas WhatsApp
- Biblioteca de templates
- Histórico de campanhas
- Wizard de onboarding
- Janela de horário de envio

### 🟢 Fase 3 — Expansão (não iniciar até Fase 2 concluída)
- Planos diferenciados na licença
- Agendamento de campanhas
- Múltiplos anexos por contato
- Auto-atualização do app

**Se você não souber em qual fase ou tarefa está, pergunte antes de agir.**

---

## 4. Regras de comportamento do agente

### O que NUNCA fazer
- Nunca abrir o navegador para verificar resultado de UI
- Nunca gravar vídeo ou tirar screenshot da tela
- Nunca reescrever arquivos funcionais existentes do zero — sempre evoluir
- Nunca instalar dependências sem listar e perguntar antes
- Nunca criar arquivos fora da estrutura de pastas definida abaixo
- Nunca modificar mais de um módulo por vez sem aprovação explícita
- Nunca usar `print()` para debug em produção — usar o sistema de log estruturado
- Nunca fazer chamadas de rede externas no código do app (produto é 100% offline)
- Nunca usar `os.system()` — usar `subprocess` com tratamento de erro

### O que SEMPRE fazer
- Ler `DESIGN.md` antes de qualquer trabalho de UI
- Confirmar o escopo da tarefa antes de começar a escrever código
- Listar os arquivos que serão modificados antes de modificá-los
- Tratar todas as exceções — nenhum módulo pode derrubar o app por erro não tratado
- Criar ou atualizar testes ao criar um novo módulo
- Comentar funções públicas com docstring em português
- Após concluir uma tarefa, listar exatamente o que foi feito e o que falta

---

## 5. Estrutura de pastas do projeto

```
SigmaLeeds/
├── AGENTS.md               ← este arquivo
├── DESIGN.md               ← design system (ler antes de qualquer UI)
├── app.py                  ← motor principal (Flask → FastAPI)
├── index.html              ← interface principal
├── requirements.txt
│
├── license/                ← módulo de licenciamento (Fase 1-C)
│   ├── keygen.py
│   ├── hardware.py
│   ├── validator.py
│   ├── trial.py
│   ├── manager.py
│   └── test_license.py
│
├── database/               ← módulo SQLite (Fase 1-A)
│   ├── schema.py
│   ├── migrations/
│   └── services/
│
├── api/                    ← rotas FastAPI (Fase 1-D)
│   ├── main.py
│   ├── routes/
│   └── models/
│
├── electron/               ← empacotamento desktop (Fase 1-B)
│   ├── main.js
│   └── package.json
│
├── static/                 ← assets da interface
│   ├── css/
│   ├── js/
│   └── icons/
│
├── tests/                  ← todos os testes
│
└── data/                   ← dados locais (gitignored)
    └── app.db
```

**Não criar pastas fora desta estrutura sem aprovação.**

---

## 6. Padrões de código

```python
# Python — padrões obrigatórios
- Python 3.8+ compatível
- Type hints em todas as funções públicas
- Docstrings em português
- Nunca capturar Exception genérica sem logar o erro
- Funções com mais de 40 linhas devem ser refatoradas
- Nomes de variáveis em snake_case, classes em PascalCase
```

```javascript
// JavaScript/HTML — padrões obrigatórios
- ES2020+ (sem transpilação necessária — Electron usa V8 moderno)
- Sem frameworks externos (sem React, Vue, jQuery)
- CSS via variáveis do DESIGN.md
- IDs e classes em kebab-case
```

---

## 7. Limites de segurança do produto

O motor de disparo deve respeitar sempre estes limites (embutidos no código, não configuráveis pelo usuário):

- Intervalo mínimo entre mensagens: **15 segundos**
- Intervalo máximo aleatório: **45 segundos**
- Pausa obrigatória a cada 100 mensagens: **30 minutos**
- Janela de horário padrão: **08h00 – 20h00**
- Limite diário por plano: Starter=300, Pro=1.000, Agency=sem limite

---

## 8. Referências rápidas

| Arquivo | Para que serve |
|:---|:---|
| `DESIGN.md` | Tokens de cor, tipografia, componentes de UI |
| `license/manager.py` | Único import de licença para o resto do app |
| `database/schema.py` | Schema completo do SQLite |
| `api/main.py` | Entrada da API FastAPI |
| `AGENTS.md` | Este arquivo — regras globais do agente |
