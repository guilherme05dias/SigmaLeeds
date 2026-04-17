@echo off
title SigmaHub - Automação
cd /d "C:\Users\user\Desktop\SigmaLeeds"
set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python311\;%LOCALAPPDATA%\Programs\Python\Python311\Scripts\
taskkill /f /im node.exe >nul 2>&1
python app.py > startup_debug.log 2>&1
