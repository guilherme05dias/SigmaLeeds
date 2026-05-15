# BUILD_REPORT_V4.2.2

Data: 2026-05-15
Instalador: `electron/dist/ZapManager Pro Setup 4.2.2.exe` (178 MB)

## Motivo do rebuild

Usuário instalou v4.2.1 em outra máquina e todos os disparos com anexo
falharam com `Erro no anexo: Access denied` no log do motor Node.

## Causa raiz

`electron/resources/engine/whatsapp-motor/server.js` estava
**desatualizado** (timestamp 2026-05-14 16:06, anterior ao commit
`1d264f6` do fix de `ATTACHMENTS_ROOT`).

[app.py:104-109](app.py#L104-L109) define `_resource_path` que prefere
arquivo externo ao `app.exe` em vez do `sys._MEIPASS` interno. Como o
diretório externo já existia com `server.js` antigo, o bundle empacotado
rodava a versão sem o fix de `ZAP_ATTACHMENTS_ROOT`.

PyInstaller embute corretamente o `server.js` atualizado em `_MEIPASS`,
mas o código nunca cai no fallback porque o externo existe primeiro.

`build.md:47` já tem o passo `Copy-Item whatsapp-motor ... -Recurse
-Force` que sincronizaria. O passo foi pulado no build da v4.2.1.

## Fix aplicado para v4.2.2

1. `cp whatsapp-motor/server.js electron/resources/engine/whatsapp-motor/server.js`
2. PyInstaller rebuild com `--clean`
3. electron-builder rebuild

## Validação

- `grep "ATTACHMENTS_ROOT" electron/dist/win-unpacked/resources/engine/whatsapp-motor/server.js`
  retorna `process.env.ZAP_ATTACHMENTS_ROOT` (fix confirmado no bundle)
- Tamanho final: 178 MB

## Para o operador

1. Copiar `electron/dist/ZapManager Pro Setup 4.2.2.exe` para a máquina destino.
2. Desinstalar versão 4.2.1 antes de instalar 4.2.2 (ou aceitar overwrite).
3. Após instalar, abrir o app e testar disparo com anexo.

## Próximos builds

**Sempre** rodar o `Copy-Item whatsapp-motor ... -Force` ANTES do
PyInstaller, conforme [build.md:47](build.md#L47). Pular esse passo
causa o bug recorrente que motivou esta release.
