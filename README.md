# ZapManager Pro v3.0

> Ferramenta de automação controlada para WhatsApp Web — desenvolvida em Python com interface gráfica Tkinter e motor Selenium.

---

## 1. Visão Geral

O **ZapManager Pro** permite enviar mensagens personalizadas para listas de contatos via WhatsApp Web, de forma organizada e auditável. Cada envio é rastreado diretamente em uma planilha Excel (`.xlsx`), com status atualizado linha por linha em tempo real.

O sistema foi projetado para **uso controlado e em baixa escala**, com foco em:
- Personalização de mensagens com `{nome}` e `{empresa}`
- Envio de **anexos** junto com a mensagem (Imagens, Vídeos, PDFs, Planilhas, etc.)
- Rastreamento preciso de status por contato
- Recuperação automática após interrupções
- Backup da planilha antes de cada campanha
- Registro de logs em arquivo para auditoria

> ⚠️ **Aviso legal:** Esta ferramenta automatiza uma sessão pessoal do WhatsApp Web. O uso deve ser responsável, ético e em conformidade com os [Termos de Serviço do WhatsApp](https://www.whatsapp.com/legal/). O uso em massa pode resultar em bloqueio de conta. **Não há qualquer garantia de que a conta não será suspensa.**

---

## 2. Arquitetura

O sistema é dividido em três camadas:

| Camada | Classe | Responsabilidade |
|:---|:---|:---|
| **Interface (UI)** | `ZapAutomationApp` | Tkinter — formulário, logs, controles |
| **Motor de Automação** | `AutomationEngine` | Selenium — Chrome, WhatsApp Web, envio |
| **Gerenciador de Dados** | `ExcelService` / `ConfigService` | openpyxl — planilha, backup, persistência |

### Fluxo de execução

```
Selecionar planilha
     │
     ▼
Mapear colunas (automático)
     │
     ▼
Recuperar EM_PROCESSAMENTO → PENDENTE
     │
     ▼
Criar backup da planilha
     │
     ▼
Abrir Chrome (perfil persistente)
     │
     ├─► QR Code? → Aguardar scan (até 120s)
     │
     ▼
Para cada linha PENDENTE:
   ├─ Validar número
   ├─ Marcar EM_PROCESSAMENTO
   ├─ Personalizar mensagem
   ├─ Enviar via WhatsApp Web
   ├─ Atualizar status (ENVIADO / INVALIDO / ERRO)
   └─ Aguardar intervalo aleatório
     │
     ▼
Exibir resumo final
```

---

## 3. Estrutura de Arquivos

```
SigmaLeeds/
├── whatsapp_automation.py   ← Código-fonte principal
├── requirements.txt         ← Dependências Python
├── zap_config.json          ← Gerado automaticamente (persistência)
├── contatos_modelo.xlsx     ← Planilha modelo de exemplo
├── backups/                 ← Cópias automáticas antes de cada campanha
└── logs/                    ← Logs detalhados de cada execução
```

> **Nota:** A pasta `ZapManagerProfile` é criada pelo Chrome em `%LOCALAPPDATA%\Google\Chrome\User Data\ZapManagerProfile` e armazena a sessão do WhatsApp.

---

## 4. Requisitos

| Item | Versão mínima |
|:---|:---|
| Sistema Operacional | Windows 10 ou superior |
| Python | 3.8+ |
| Google Chrome | Versão atual estável |
| selenium | 4.15.0+ |
| openpyxl | 3.1.2+ |
| webdriver-manager | 4.0.1+ |

---

## 5. Instalação

### 5.1 Pré-requisitos
- Python instalado e no PATH (`python --version` deve funcionar no terminal)
- Google Chrome instalado

### 5.2 Instalar dependências

```bash
# No terminal, dentro da pasta do projeto:
pip install -r requirements.txt
```

Ou manualmente:
```bash
pip install selenium openpyxl webdriver-manager
```

### 5.3 Executar

```bash
python whatsapp_automation.py
```

---

## 6. Configuração

### Perfil persistente do Chrome

O sistema usa um perfil isolado chamado `ZapManagerProfile`. Isso garante que o login seja **salvo entre sessões** — você escaneará o QR Code apenas na primeira execução (ou quando a sessão expirar).

O perfil é criado automaticamente em:
```
%LOCALAPPDATA%\Google\Chrome\User Data\ZapManagerProfile
```

### Arquivo `zap_config.json`

Criado automaticamente na primeira execução. Armazena:

```json
{
    "msg": "Olá {nome}! Tudo bem?",
    "limit": 100,
    "min": 15,
    "max": 30,
    "keep_open": false,
    "last_file": "C:\\caminho\\para\\contatos.xlsx",
    "last_attachment": "C:\\caminho\\para\\imagem.png"
}
```

---

## 7. Formato da Planilha

O arquivo deve ser `.xlsx`. O sistema mapeia as colunas **automaticamente por nome** (não importa a ordem ou capitalização).

| Coluna | Obrigatória | Aliases reconhecidos | Descrição |
|:---|:---:|:---|:---|
| **Nome** | ✅ Sim | nome, cliente, contato | Nome do contato para `{nome}` |
| **Numero** | ✅ Sim | whatsapp, numero, telefone, celular | Telefone com DDD (sem formatação) |
| **Status** | ✅ Sim | status, situacao | Deve conter `PENDENTE` para ser enviado |
| **Empresa** | ❌ Não | empresa, razao social, fantasia | Para `{empresa}` |
| **Observacao** | ❌ Não | observacao, obs | Preenchido pelo sistema com erros |
| **DataEnvio** | ❌ Não | dataenvio, data de envio, enviado em | Preenchido com data/hora do sucesso |

### Formatos de número aceitos

| Formato | Exemplo | Resultado |
|:---|:---|:---|
| DDD + 9 dígitos | `11999998888` | `5511999998888` |
| DDD + 8 dígitos | `1133334444` | `55113333444` |
| Com código do país | `5511999998888` | Usado diretamente |

> ⚠️ Não use formatação com parênteses, hífen ou espaços. O sistema limpa automaticamente, mas é uma boa prática manter os números limpos.

---

## 8. Status dos Contatos

| Status | Significado |
|:---|:---|
| `PENDENTE` | Aguardando envio |
| `EM_PROCESSAMENTO` | Em tentativa de envio (resetado automaticamente na próxima abertura) |
| `ENVIADO` | Mensagem disparada com sucesso |
| `INVALIDO` | Número não possui WhatsApp ou foi rejeitado |
| `ERRO` | Falha técnica durante a tentativa |

---

## 9. Como Usar

1. **Abrir:** Execute `python whatsapp_automation.py`
2. **Selecionar planilha:** Clique em "📂 Selecionar Excel" e escolha o arquivo `.xlsx`
3. **Escrever a mensagem:** Use `{nome}` e `{empresa}` onde quiser personalizar
4. **Adicionar Anexo (Opcional):** Marque a caixa, clique em "📎 Selecionar Arquivo" e escolha a imagem, documento ou vídeo
5. **Configurar limites:**
   - **Limite de envios:** quantos contatos processar nesta sessão
   - **Intervalo:** tempo mínimo e máximo (em segundos) entre cada envio
6. **Iniciar:** Clique em "▶ INICIAR CAMPANHA"
7. **Acompanhar:** Clique em "🔍 Exibir Logs" para ver o que acontece em tempo real
8. **Parar se necessário:** Clique em "■ PARAR" — o progresso atual é salvo

### Opção "Manter Chrome aberto"

Marque esta opção se quiser inspecionar o navegador após a campanha. Se desmarcada, o Chrome fecha automaticamente ao terminar.

---

## 10. Troubleshooting

| Problema | Causa provável | Solução |
|:---|:---|:---|
| Chrome não abre | Outra instância usando o perfil | Feche todos os processos `chrome.exe` no Gerenciador de Tarefas |
| QR Code solicitado toda vez | Sessão expirada ou logout pelo celular | Escaneie novamente; a sessão será salva |
| Planilha não carrega | Arquivo aberto no Excel ou colunas com nome errado | Feche o arquivo no Excel e verifique o cabeçalho |
| Mensagem não enviada (ERRO) | Botão de envio não encontrado (layout mudou) | Verifique se o WhatsApp Web está funcionando normalmente no Chrome |
| `PermissionError` ao salvar | Planilha aberta em outro programa | Feche o Excel e reinicie a campanha |
| `webdriver-manager` lento | Download do ChromeDriver na primeira vez | Aguarde; na segunda execução será rápido |
| Contatos presos em `EM_PROCESSAMENTO` | Execução interrompida abruptamente | Ao reabrir a planilha no sistema, eles são resetados automaticamente |

---

## 11. Segurança Operacional e Boas Práticas

- **Escala:** Use para listas pequenas e controladas (até algumas dezenas por sessão)
- **Intervalo:** Mantenha no mínimo 15 segundos entre envios para reduzir risco de instabilidade
- **Não interfira:** Não clique na janela do Chrome durante a automação — isso pode tirar o foco do Selenium
- **Planilha fechada:** Nunca deixe o arquivo `.xlsx` aberto no Excel durante a execução
- **Teste primeiro:** Faça um teste com 2 ou 3 contatos antes de iniciar a lista completa
- **Supervisão:** Sempre monitore os primeiros envios de uma nova campanha
- **Backup manual:** Embora o sistema faça backup automático, guarde uma cópia adicional antes de campanhas grandes

---

## 12. Limitações Conhecidas

1. **Dependência de layout:** A automação depende de seletores HTML do WhatsApp Web. Atualizações da plataforma podem quebrar o envio sem aviso prévio.
2. **Detecção de inválido:** A identificação de "número inválido" é baseada em texto da página. Não há integração com API oficial.
3. **Validação de número:** A lógica de validação é prática (comprimento + DDD), não uma verificação real de existência no WhatsApp.
4. **Sem anti-ban:** Não há nenhuma garantia de proteção contra limitações ou bloqueios do WhatsApp.
5. **Dependência de Chrome:** O sistema não funciona com outros navegadores.
6. **Planilha em uso:** Se o arquivo `.xlsx` estiver aberto no Excel durante a execução, os saves falharão.
7. **Sem relatórios:** Não há exportação de relatórios automáticos; o status está na própria planilha.

---

## 13. Logs

A cada execução, um arquivo de log é criado automaticamente em:
```
logs/zap_YYYYMMDD_HHMMSS.log
```

O log inclui: todas as ações, tentativas, erros e o resumo final da campanha.

---

## ⚡ Resumo Rápido de Uso

```bash
# 1. Instalar dependências (apenas uma vez)
pip install -r requirements.txt

# 2. Executar
python whatsapp_automation.py
```

1. Selecione a planilha `.xlsx` com os contatos na coluna `Status` = `PENDENTE`
2. Escreva sua mensagem usando `{nome}` e `{empresa}` para personalizar
3. Na primeira vez, escaneie o QR Code que aparecerá no Chrome
4. Clique em **INICIAR CAMPANHA** e monitore pelos logs
5. O progresso é salvo na planilha linha a linha — pode parar e retomar com segurança

---

*ZapManager Pro v3.0 — Automação controlada, responsável e auditável.*
