# Global Rules — Guilherme Dias

## Comportamento padrão
- Responda sempre em português brasileiro
- Confirme o escopo em 2 linhas antes de executar qualquer tarefa
- Liste os arquivos que serão tocados antes de modificá-los
- Ao terminar, liste o que foi feito e qual é o próximo passo

## Economia de tokens
- Nunca abra o navegador — nenhuma tarefa exige isso
- Nunca tire screenshot ou grave vídeo
- Não leia arquivos que não sejam necessários para a tarefa atual
- Não repita código já visível no contexto — referencie por arquivo e linha

## Código
- Python 3.8+, type hints, docstrings em português
- Nunca use `print()` para debug — use o logger do projeto
- Nunca capture `Exception` genérica sem logar o erro
- Trate todos os erros — nenhum módulo pode derrubar o app por exceção não tratada
- Pergunte antes de instalar qualquer dependência nova

## Quando parar e perguntar
- Escopo maior que o esperado
- Arquivo fora da estrutura definida no AGENTS.md
- Dependência nova necessária
- Ambiguidade sobre qual fase ou módulo está sendo desenvolvido
