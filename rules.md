# Regras operacionais — ZapManager Pro

## Economia de tokens e contexto

- Leia apenas os arquivos necessários para a tarefa atual — não leia o projeto inteiro de uma vez
- Ao iniciar uma tarefa, pergunte quais arquivos são relevantes antes de abrir tudo
- Não repita código já existente no contexto — referencie pelo nome do arquivo e linha
- Respostas de confirmação devem ser curtas: liste o que vai fazer, aguarde aprovação, execute

## Ferramentas proibidas neste projeto

- **Browser:** não abrir navegador para nenhuma finalidade (verificação de UI, busca, docs)
- **Screenshot / gravação de vídeo:** proibido em qualquer circunstância
- **Chamadas de rede externas:** o produto é offline — nenhum `requests.get()` para URLs externas no código do app
- **Instalação automática de pacotes:** sempre listar e perguntar antes de rodar `pip install` ou `npm install`

## Comportamento em cada tarefa

1. **Antes de começar:** confirme em 2–3 linhas o que vai fazer e quais arquivos vai tocar
2. **Durante:** modifique um arquivo por vez, mostre o diff antes de salvar se a mudança for grande
3. **Ao terminar:** liste o que foi feito, o que foi criado/modificado e qual é o próximo passo do plano

## Quando parar e perguntar

- Se a tarefa exigir modificar um arquivo fora da estrutura definida no `AGENTS.md`
- Se uma dependência nova for necessária
- Se houver ambiguidade sobre qual fase ou módulo está sendo desenvolvido
- Se o escopo da tarefa parecer maior do que o esperado

## Prioridade de leitura de contexto

1. `AGENTS.md` — leia sempre primeiro
2. `DESIGN.md` — leia antes de qualquer UI
3. Apenas os arquivos diretamente relacionados à tarefa atual
