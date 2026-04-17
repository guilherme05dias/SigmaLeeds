@echo off
title Parando SigmaHub
echo Encerrando processos do Node.js (Motor do WhatsApp)...
taskkill /f /im node.exe >nul 2>&1

echo Encerrando processos do Python (Servidor Flask)...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

echo Tudo encerrado com sucesso.
ping 127.0.0.1 -n 3 > nul
