# 🚀 Guia de Instalação e Uso Automotivo SigmaHub em Outro Computador

Bem-vindo(a) ao projeto **SigmaHub / SigmaLeeds**! Siga as instruções abaixo rigorosamente para configurar o sistema de automação e dashboard em uma nova máquina do zero.

---

## 🛠️ 1. Pré-Requisitos: Instalação de Programas Necessários

Antes de tudo, o novo computador precisa ter as seguintes ferramentas instaladas:

1. **Python (Linguagem do Servidor e Interface e Robô)**
   - Baixe a versão `3.10` ou superior (recomendado: 3.12) em [python.org](https://www.python.org/downloads/).
   - **MUITO IMPORTANTE:** Durante a instalação, marque a caixa **"Add Python to PATH"** ou **"Adicionar Python ao PATH"** logo na primeira tela. Sem isso o sistema não irá funcionar.

2. **Node.js (Motor de Conexão do WhatsApp)**
   - Baixe a versão `LTS` (estável) de [nodejs.org](https://nodejs.org/).
   - Instale com as configurações padrão. Ele será usado para a API responsável por parear o WhatsApp e enviar as mensagens de forma invisível.

3. **Google Chrome**
   - Tenha o Google Chrome mais atualizado instalado. O sistema usará os drivers padrão para manipular a web.

---

## 📥 2. Configurando o Projeto

Copie toda a pasta principal do projeto para o novo computador (por exemplo, na Área de Trabalho ou Documentos).

Após colar os arquivos no novo computador, faça o seguinte:

1. **Abra o Prompt de Comando (CMD) ou PowerShell** como administrador, e navegue até a pasta do projeto. 
   - Exemplo: `cd C:\Users\SeuUsuario\Desktop\SigmaLeeds_Export`
   
2. **Instalar Dependências do Python**
   No terminal, digite e execute:
   ```bash
   pip install -r requirements.txt
   ```
   *(Isso irá instalar todos os pacotes necessários como Flask, Selenium, requests, etc).*

3. **Instalar Dependências do Node.js (Motor)**
   No seu terminal (dentro da pasta do projeto), abra a subpasta `whatsapp-motor` e rode a instalação do Node:
   ```bash
   cd whatsapp-motor
   npm install
   ```
   *(Isso vai baixar todas as bibliotecas usadas pela API do WhatsApp: express, qr-code, whatsapp-web.js, etc).*

---

## 🚀 3. Como Iniciar o Sistema (Dia a Dia)

Depois que a configuração for concluída, você não precisará mais abrir o terminal para as dependências. 

1. Volte para a pasta principal do projeto.
2. Dê **dois cliques** no arquivo `SigmaHub.bat` (ou `Iniciar_Sistema.vbs` caso precise que o terminal se mantenha oculto). Se não existir, crie ou execute diretamente:
   ```bash
   python app.py
   ```
3. O servidor Flask irá rodar, e o servidor Node.js iniciará em *background* automaticamente (assumindo que as portas não estejam ocupadas).
4. Seu navegador principal vai abrir o link local `http://127.0.0.1:5050` (ou a porta que o sistema alocou) exibindo o Painel (Dashboard) SigmaHub.
5. Se uma janela preta do Node (`server.js`) ficar aberta, apenas as minimize-a. Ela é o cérebro que mantém a conexão em tempo real com o WhatsApp Web.

---

## 🔁 4. Resetando a Conexão (Caso o WhatsApp trave)

Se o celular for desconectado ou as mensagens pararem de sair:
- Clique no programa para **Parar Sistema**, ou rode `Parar_Sistema.bat`.
- Dê dois cliques em `Resetar_WhatsApp.bat` se precisar limpar os dados do cliente e deslogar de sessões fantasmas. 
- Inicie novamente o sistema. Você precisará ler um novo QRCode (que aparecerá na tela de Status no momento de conectar).

---

## ⚙️ Dúvidas sobre Scripts e Organização da Pasta

- `app.py`: Controlador geral (Dashboard web e regras do sistema Python).
- `whatsapp_automation.py`: Serviço de gerenciamento de contatos da planilha e lógica de processamento e envio do WhatsApp.
- `whatsapp-motor/server.js`: API local responsável por emular o WhatsApp pelo Chromium sem gerar interface bloqueante, disparando as mensagens efetivamente via protocolo WhatsAppWeb.
- `requirements.txt`: Lista de peças cruciais pro Python.
- `whatsapp-motor/package.json`: Lista de peças para o Node.js.
- `templates/` e `static/`: Arquivos HTML/CSS do visual do dashboard.

Sucesso na nova máquina!
