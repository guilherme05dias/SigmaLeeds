@echo off
title Instalador Motor Zap Invisível - SigmaLeeds
color 0a

echo ----------------------------------------------------
echo         INSTALADOR MOTOR NODE.JS - SIGMA HUB
echo ----------------------------------------------------
echo.
echo Verificando se o Node.js esta instalado...
node -v >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\nodejs\node.exe" (
        set "PATH=%PATH%;C:\Program Files\nodejs"
        echo [INFO] Node.js encontrado em C:\Program Files\nodejs. Caminho temporário adicionado.
    ) else (
        color 0c
        echo [ERRO] O Node.js nao foi encontrado no Windows nem no caminho padrao.
        echo Por favor, instale o Node.js baixando de https://nodejs.org/
        echo Apos instalar, REINICIE o computador ou feche e abra o terminal novamente.
        pause
        exit /b
    )
)

echo [OK] Node.js detectado!
echo Instalando dependencias do motor...
cd /d "c:\Users\user\Desktop\SigmaLeeds\whatsapp-motor"
npm install

echo.
echo ----------------------------------------------------
echo [SUCESSO] MOTOR INSTALADO E PRONTO.
echo O Python sera modificado para aciona-lo automaticamente!
echo ----------------------------------------------------
pause
