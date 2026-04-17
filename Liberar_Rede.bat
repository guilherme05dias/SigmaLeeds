@echo off
title Liberar SigmaHub na Rede Local
echo ========================================================
echo SOLICITANDO PERMISSOES DE ADMINISTRADOR...
echo ========================================================

:: Verifica privilégios de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como Administrador.
    echo Por favor, clique com o botão direito neste arquivo e selecione "Executar como Administrador".
    pause
    exit /b 1
)

echo.
echo Adicionando regra de Firewall para portas 5050 a 5099 (TCP)...
netsh advfirewall firewall add rule name="SigmaHub" dir=in action=allow protocol=TCP localport=5050-5099
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao adicionar regra no Firewall!
) else (
    echo [SUCESSO] Regra de Firewall adicionada!
)

echo.
echo Para acessar o SigmaHub de outras maquinas, verifique o IP Local exibido quando iniciar o sistema.
echo Pressione qualquer tecla para sair...
pause >nul
