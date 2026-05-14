# Relatório Completo — Sprint Final ZapManager Pro v4.0

## O que foi feito

Foram corrigidos **8 problemas** encontrados na auditoria final: 4 críticos e 4 de confiabilidade/dados.

---

## CRÍTICOS — C1 a C4

### C1 — Electron não conseguia iniciar o app

**Problema:** O Electron tentava detectar se o servidor Python estava rodando fazendo uma requisição para `/api/status`. Essa rota agora exige autenticação, então o servidor respondia `401 Unauthorized`. O Electron interpretava isso como "servidor ainda não iniciou" e ficava tentando por 60 segundos até mostrar um erro fatal: *"Servidor não respondeu em 60s"*.

**O que foi alterado:** `electron/main.js` linha 41
- Antes: `http.get('.../api/status')` e aceitava só status `200`
- Depois: `http.get('.../')` (rota pública) e aceita qualquer resposta `2xx`

**Como funciona agora:** O Electron detecta o servidor corretamente na inicialização, a splash screen some, e a janela principal abre normalmente.

---

### C2 — Motor WhatsApp acessível pela rede local

**Problema:** O servidor Node.js que controla o WhatsApp (`whatsapp-motor/server.js`) estava ouvindo em todas as interfaces de rede (`0.0.0.0`). Qualquer pessoa na mesma rede Wi-Fi (café, hotel, escritório) conseguia acessar a porta 3001 e:
- Ver o QR Code e roubar a sessão do WhatsApp
- Enviar mensagens do WhatsApp do usuário para qualquer número
- Desconectar a sessão do WhatsApp

**O que foi alterado:** `whatsapp-motor/server.js` linha 172
- Antes: `app.listen(3001, ...)`
- Depois: `app.listen(3001, '127.0.0.1', ...)`

**Como funciona agora:** O motor WhatsApp só aceita conexões vindas da própria máquina. Rede local bloqueada completamente.

---

### C3 — Motor WhatsApp podia ler qualquer arquivo do computador

**Problema:** A rota `/send` do Node aceitava um parâmetro `filePath` sem validação. Um atacante com acesso à porta 3001 (ver C2) podia mandar qualquer caminho de arquivo — `C:\Users\...\private_key.pem`, arquivos de senha, dados pessoais — e o servidor enviava esse arquivo via WhatsApp para um número controlado pelo atacante.

**O que foi alterado:** `whatsapp-motor/server.js` linhas 12 e 135–141
- Adicionado: `const ATTACHMENTS_ROOT = path.resolve('./data/attachments')`
- Antes de qualquer leitura de arquivo: verifica se o caminho resolvido está dentro dessa pasta
- Se estiver fora: responde `403 Access denied` sem tocar no arquivo

**Como funciona agora:** Só arquivos dentro de `data/attachments/` (pasta onde o próprio sistema salva os PDFs carregados) podem ser enviados como anexo. Qualquer tentativa de enviar outro caminho é bloqueada.

---

### C4 — Chave privada de licença estava no repositório

**Problema:** O arquivo `private_key.pem` (chave Ed25519 usada para assinar licenças) estava salvo no código-fonte em dois lugares: raiz do projeto e `license/`. Qualquer pessoa com acesso ao repositório podia usar essa chave para gerar licenças falsas e burlar completamente o sistema de cobrança.

**O que foi feito:**
- Arquivos `private_key.pem` e `license/private_key.pem` **deletados do disco**
- Confirmado que `license/validator.py` contém **só a chave pública** (para verificar assinaturas), sem nenhum dado privado
- `.gitignore` já tinha `*.pem` — confirmado presente

**⚠️ Ação manual ainda necessária (não pode ser automatizada):**

| Passo | O que fazer |
|-------|-------------|
| 1 | Gerar um novo par de chaves Ed25519 em uma máquina segura |
| 2 | Substituir a constante `PUBLIC_KEY_PEM` em `license/validator.py` pela nova chave pública |
| 3 | Guardar a nova chave privada **fora do repositório** (cofre de senhas, gerenciador de segredos) |
| 4 | Considerar o par antigo **comprometido** — quem tem o repositório pode forjar licenças |
| 5 | Reemitir licenças aos clientes assinadas com a nova chave |
| 6 | Limpar o histórico do git: `git filter-repo --path private_key.pem --invert-paths` |

---

## MÉDIOS — M1 a M4

### M1 — Worker de campanha travava com configuração de delay inválida

**Problema:** O servidor tentava "proteger" os limites de delay (intervalo entre envios) com lógica incorreta:

```python
# ANTES — com bug
"min": max(15, req.min_interval),   # só garante mínimo de 15s
"max": min(45, req.max_interval),   # só garante máximo de 45s
```

Se o usuário mandasse `min=50, max=30`, o resultado era `min=50, max=30`. Quando a thread de envio chamava `random.randint(50, 30)`, o Python lança `ValueError`. O worker morria silenciosamente com status `"Erro interno"`, deixando contatos presos em `EM_PROCESSAMENTO`.

**O que foi alterado:** `app.py` linhas 687–688 e 825–826 (as duas rotas de início de campanha)

```python
# DEPOIS — correto
lo = max(15, min(45, req.min_interval or 15))   # garante: 15 ≤ min ≤ 45
hi = max(lo, min(45, req.max_interval or 30))   # garante: min ≤ max ≤ 45
```

**Como funciona agora:** Independente do que o frontend mande, o delay mínimo sempre será entre 15s e 45s, e o máximo nunca será menor que o mínimo. `random.randint` nunca vai falhar.

---

### M2 — Contagem de envios diários errava perto da meia-noite

**Problema:** O banco de dados gravava o horário de envio em UTC (`CURRENT_TIMESTAMP`), mas a verificação do limite diário comparava com o horário local (`DATE('now','localtime')`). No Brasil (UTC-3), às 22h BRT o horário UTC já é 01h do dia seguinte — os envios feitos das 21h à meia-noite eram contados no dia errado, permitindo burlar o limite diário ou bloquear envios legítimos.

**O que foi alterado:** `database/services/campaign_service.py` linha 173
- Antes: `sent_at = CURRENT_TIMESTAMP` (UTC)
- Depois: `sent_at = datetime('now','localtime')` (horário local)

A leitura (`get_today_sent_count`) já usava `DATE('now','localtime')` — agora ambos os lados usam o mesmo fuso.

**Como funciona agora:** A contagem de envios do dia bate exatamente com o dia local do usuário. Limite de 300/dia (Starter) ou 1000/dia (Pro) funciona corretamente em qualquer horário.

---

### M3 — Contatos travados em "EM_PROCESSAMENTO" após crash do worker

**Problema:** Quando a thread de envio era iniciada, ela marcava cada contato como `EM_PROCESSAMENTO` antes de tentar enviar. Se o worker morria no meio (erro interno, queda de energia, etc.), esses contatos ficavam com esse status indefinidamente. O sistema só resetava contatos travados na inicialização do app. Se o usuário iniciasse uma nova campanha sem reiniciar o app, os contatos travados simplesmente desapareciam — não eram enviados, mas não apareciam como erro.

**O que foi alterado:** `app.py` linha 367
- Antes: `reset_processing_contacts` só rodava se fosse um "resume" explícito
- Depois: roda **sempre**, no início de qualquer execução, antes de buscar os contatos pendentes
- A variável `resume` (que ficou sem uso) foi removida

**Como funciona agora:** Toda vez que uma campanha começa — seja início normal, retomada ou retry — qualquer contato que estava em `EM_PROCESSAMENTO` é automaticamente devolvido para `PENDENTE`. Nenhum contato some silenciosamente após um crash.

---

### M4 — Vazamento de conexão SQLite ao importar planilha com erro

**Problema:** A função `import_contacts_from_xlsx` abria uma conexão com o banco (`conn = get_connection()`) e só a fechava no final do fluxo normal. Se qualquer erro ocorresse no meio da importação (arquivo corrompido, linha malformada, erro de banco), a conexão era abandonada aberta. Com WAL mode ativo, conexões abertas com escrita pendente bloqueiam outras operações do banco — em uma sessão longa isso podia causar o erro "database is locked".

**O que foi alterado:** `database/services/campaign_service.py` linhas 117–147
- O bloco que usa `conn` foi envolto em `try/finally`
- `conn.close()` agora sempre executa, independente de sucesso ou erro

**Como funciona agora:** A conexão é sempre fechada ao final da importação, com ou sem erro. Sem risco de bloqueio acumulativo do banco em sessões longas.

---

## Resumo do estado atual

| Área | Antes | Agora |
|------|-------|-------|
| Electron inicializa | ❌ Trava em 60s | ✅ Inicia normalmente |
| Motor WhatsApp | ❌ Aberto na rede local | ✅ Só localhost |
| Envio de arquivos | ❌ Qualquer arquivo do sistema | ✅ Só `data/attachments/` |
| Chave privada | ❌ No repositório | ✅ Deletada do disco |
| Delay de campanha | ❌ Pode crashar o worker | ✅ Sempre 15s–45s, min ≤ max |
| Limite diário | ❌ Errava perto da meia-noite | ✅ Baseado em horário local |
| Contatos travados | ❌ Sumiam até reiniciar o app | ✅ Recuperados automaticamente |
| Conexões SQLite | ❌ Vazamento em erros de import | ✅ Sempre fechadas |

---

## Arquivos modificados

| Arquivo | Blocos |
|---------|--------|
| `electron/main.js` | C1 |
| `whatsapp-motor/server.js` | C2, C3 |
| `private_key.pem` | C4 — deletado |
| `license/private_key.pem` | C4 — deletado |
| `app.py` | M1, M3 |
| `database/services/campaign_service.py` | M2, M4 |

---

## Pendência obrigatória — C4 Rotação de Chaves

> O app funciona normalmente com as chaves atuais, mas qualquer pessoa que teve acesso ao repositório antes de hoje pode forjar licenças. A rotação deve ser feita antes do lançamento para clientes reais.

```bash
# Limpar histórico do git após gerar novo par de chaves
git filter-repo --path private_key.pem --invert-paths
git filter-repo --path license/private_key.pem --invert-paths
git push --force --all
```
