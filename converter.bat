@echo off
chcp 65001 >nul
title PDF para Markdown - linha de comando
cd /d "%~dp0"
if "%~1"=="" (
    echo Arraste um PDF ou uma pasta para cima deste arquivo.
    pause
    exit /b 0
)
".venv\Scripts\python.exe" -m pdf2md %*
pause
