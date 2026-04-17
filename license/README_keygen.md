# ZapManager Pro v4.0 - Gerenciador de Licenças (Opção C)

Este módulo controla as regras de testes e ativação offline do ZapManager Pro com segurança criptográfica (Ed25519).

## 1. Primeiros Passos (Para o Vendedor)

Para poder emitir e assinar licenças de forma reconhecida pelo validador do aplicativo, precisamos gerar o **par de chaves criptográficas**.

1. Na raiz do projeto, rode o script gerador de chaves no seu ambiente seguro:
   ```bash
   python license/keygen.py --generate-keys
   ```
2. O sistema informará que salvou a `private_key.pem`. **MANTENHA ESTE ARQUIVO SEGURO. NUNCA O ENVIE PARA O CLIENTE.**
3. O console também irá imprimir uma "CHAVE PÚBLICA".
4. Abra o arquivo `license/validator.py` e substitua o valor da constante `PUBLIC_KEY_PEM` pelo payload inteiro da chave pública gerada.

---

## 2. Como gerar licenças para clientes

Sempre que efetuar uma venda, utilize a linha de comando para gerar a chave para o cliente. 
Certifique-se de que o seu `private_key.pem` está na mesma pasta onde você vai rodar o comando.

**Para Plano PRO (1 ano):**
```bash
python license/keygen.py --plan pro --days 365 --machines 1
```

**Para Plano Agency (Vitálicio/10 anos):**
```bash
python license/keygen.py --plan agency --days 3650 --machines 10
```

O comando retornará a chave (ex: `ZMPRO-xxxxx.yyyyy`).
**Envie este texto para o cliente colar no aplicativo.** O sistema offline e isolado dele usará a chave pública embutida e baterá com aquela assinada pela chave privada que apenas você possui, liberando os recursos apropriados!

---

## 3. Estrutura

- `hardware.py`: Identificação de hardware (uuid/cpu)
- `keygen.py`: Gerador de assinaturas digitais
- `validator.py`: Validador de assinaturas (com public key)
- `trial.py`: Verificações seguras em 3 locais contra bypass
- `manager.py`: Orquestrador importado pelo `app.py`
- `test_license.py`: Verificador de integridade programática

Para garantir o funcionamento antes de liberar sua build, você pode rodar (testes são executados em ambiente isolado via mock de diretórios):
```bash
python license/test_license.py
```
Nenhum erro deve ser detectado.

**Notas:**
Necessário que a máquina rode com os pacotes do `requirements.txt`, dos quais se destacam `cryptography` e `wmi`.
