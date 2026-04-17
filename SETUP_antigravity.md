# Guia de instalação — Configuração global do Antigravity
## ZapManager Pro v4.0

---

## Arquivos gerados e onde colocar cada um

| Arquivo | Destino | Carregado quando |
|:---|:---|:---|
| `GEMINI_global.md` | `C:\Users\Guilherme Dias\.gemini\GEMINI.md` | Em **todos** os projetos |
| `GEMINI.md` | `C:\Users\Guilherme Dias\Desktop\SigmaLeeds\GEMINI.md` | Só no projeto ZapManager |
| `AGENTS.md` | `C:\Users\Guilherme Dias\Desktop\SigmaLeeds\AGENTS.md` | Só no projeto ZapManager |
| `.antigravityignore` | `C:\Users\Guilherme Dias\Desktop\SigmaLeeds\.antigravityignore` | Controla indexação |
| `.antigravity\rules\rules.md` | `C:\Users\Guilherme Dias\Desktop\SigmaLeeds\.antigravity\rules\rules.md` | Regras operacionais |

---

## Passo a passo de instalação

### 1. Configuração global (preferências pessoais — todos os projetos)

```
Copiar GEMINI_global.md para:
C:\Users\Guilherme Dias\.gemini\GEMINI.md

Se a pasta não existir, criar:
mkdir C:\Users\Guilherme Dias\.gemini
```

### 2. Configuração do projeto ZapManager

```
Copiar para C:\Users\Guilherme Dias\Desktop\SigmaLeeds\:

├── GEMINI.md
├── AGENTS.md
├── .antigravityignore
└── .antigravity\
    └── rules\
        └── rules.md
```

### 3. Instalar skills (rodar na pasta do projeto)

```bash
# Agentes especialistas (auto-detecção)
npx ag-kit init

# Skills oficiais de backend e segurança
npx @voltagent/awesome-agent-skills --antigravity --category backend,security,testing

# Design system
npx getdesign@latest add airtable
```

### 4. Fechar e reabrir o Antigravity

Após copiar os arquivos, feche completamente o Antigravity e abra novamente.
O agente vai ler o GEMINI.md e AGENTS.md automaticamente na próxima sessão.

---

## Por que essa estrutura economiza tokens

| Arquivo | Tokens aprox. | Frequência de carga |
|:---|:---:|:---|
| `GEMINI_global.md` | ~200 | Todo prompt de todo projeto |
| `GEMINI.md` (projeto) | ~180 | Todo prompt do ZapManager |
| `AGENTS.md` | ~800 | Lido uma vez por sessão |
| Skills (ag-kit) | ~50–100 por skill | Só quando semanticamente relevante |
| `.antigravityignore` | 0 | Só afeta o indexador, não o contexto |

**Total por prompt:** ~380 tokens fixos — dentro da zona "lean" recomendada.

> Comparação: sem essa configuração, você repetiria contexto em todo prompt manualmente,
> custando 500–2.000 tokens extras por solicitação.

---

## Dicas de uso no dia a dia

**Abra uma sessão nova por módulo** — não use a mesma janela de chat para o módulo de licença e para o SQLite. Contexto longo degrada a qualidade do agente.

**Seja específico no prompt** — em vez de "conserte o bug", diga "conserte o bug em `license/validator.py` linha 47, na função `validate_key`". Isso economiza 60–80% dos tokens que o agente gastaria localizando o problema.

**Use Gemini Flash para tarefas simples** — renomear variável, formatar código, gerar boilerplate. Reserve o modelo Pro/Ultra para arquitetura e debug complexo.

**Feche o Antigravity quando não estiver usando** — o indexador em background consome tokens mesmo sem você estar digitando.
