@echo off
cd /d "%~dp0"
echo ========================================================
echo        GERADOR DE INSTALADOR - ZAPMANAGER PRO v4.0
echo ========================================================
echo.
echo NOTA: Certifique-se de estar rodando este script como Administrador!
echo.

:: Passo 1: Limpeza e Build do Python
echo [1/2] Limpando cache e Empacotando o motor interno (Python e Node)...
if exist "electron\dist" rmdir /s /q "electron\dist"
if exist "electron\resources\engine" rmdir /s /q "electron\resources\engine"

.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pyinstaller --clean -y --onefile --noconsole --name app --distpath electron/resources/engine --hidden-import cryptography --hidden-import wmi --add-data "templates;templates" --add-data "static;static" --add-data "database;database" --add-data "license;license" --add-data "api;api" --add-data "whatsapp-motor;whatsapp-motor" app.py

:: Passo 2: Build do Instalador do Electron
echo.
echo [2/2] Gerando o instalador final...
cd electron
call npm install
call npm run build:installer

echo.
echo ========================================================
echo CONCLUÍDO! O instalador ".exe" está na pasta:
echo SigmaLeeds\electron\dist\
echo ========================================================
pause
