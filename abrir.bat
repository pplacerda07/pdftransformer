@echo off
chcp 65001 >nul
title PDF para Markdown
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo O programa ainda nao foi instalado.
    echo Rode primeiro o arquivo  instalar.bat
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "app.py"
