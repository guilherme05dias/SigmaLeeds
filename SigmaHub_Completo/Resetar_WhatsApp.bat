@echo off
title Resetar Sessao WhatsApp - SigmaHub
echo ========================================================
echo          RESETAR SESSAO DO WHATSAPP (SigmaHub)
echo ========================================================
echo.
echo Este script vai:
echo  1. Matar TODOS os processos Node.js e Chrome
echo  2. Limpar a sessao antiga do WhatsApp
echo  3. Reiniciar o sistema limpo para gerar novo QR Code
echo.
echo Pressione qualquer tecla para continuar...
pause >nul

echo.
echo [1/3] Matando processos...
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im chrome.exe >nul 2>&1
taskkill /f /im chromium.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
:: Espera processos morrerem
ping 127.0.0.1 -n 4 >nul

echo [2/3] Removendo sessao antiga...
cd /d "C:\Users\user\Desktop\SigmaLeeds\whatsapp-motor"
if exist ".wwebjs_auth" (
    rmdir /s /q ".wwebjs_auth" 2>nul
    if exist ".wwebjs_auth" (
        echo Tentando novamente com delay...
        ping 127.0.0.1 -n 3 >nul
        rmdir /s /q ".wwebjs_auth" 2>nul
    )
    if not exist ".wwebjs_auth" (
        echo [OK] Sessao removida com sucesso!
    ) else (
        echo [AVISO] Alguns arquivos podem ter ficado. Reinicie o PC se persistir.
    )
) else (
    echo [OK] Nenhuma sessao antiga encontrada.
)

echo [3/3] Iniciando SigmaHub...
echo.
cd /d "C:\Users\user\Desktop\SigmaLeeds"
set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311\;%LOCALAPPDATA%\Programs\Python\Python311\Scripts\
echo Iniciando servidor... O navegador vai abrir automaticamente.
echo Aguarde o QR Code aparecer na tela!
echo.
python app.py > startup_debug.log 2>&1
