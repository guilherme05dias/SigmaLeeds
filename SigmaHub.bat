@echo off
title SigmaHub - Automação
cd /d "%~dp0"
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH.
    pause
    exit /b 1
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python encontrado, mas nao executou corretamente.
    pause
    exit /b 1
)
taskkill /f /im node.exe >nul 2>&1
python app.py > startup_debug.log 2>&1
