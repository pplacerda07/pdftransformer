@echo off
chcp 65001 >nul
title Instalar - PDF para Markdown
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ============================================
echo    PDF para Markdown - instalacao
echo ============================================
echo.

if exist ".venv\Scripts\python.exe" goto :libs

set "PYCMD="
for %%C in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python311\python.exe"
) do (
  if not defined PYCMD if exist %%C set PYCMD="%%~C"
)

if not defined PYCMD (
  py -3 -c "import sys" >nul 2>&1 && set "PYCMD=py -3"
)
if not defined PYCMD (
  python -c "import sys" >nul 2>&1 && set "PYCMD=python"
)

if not defined PYCMD (
  echo [ERRO] Python nao encontrado nesta maquina.
  echo.
  echo Instale com o comando abaixo no Terminal e rode este arquivo de novo:
  echo    winget install -e --id Python.Python.3.12
  echo.
  echo Ou baixe em https://www.python.org/downloads/
  echo marcando a opcao "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo Usando o Python: !PYCMD!
echo Criando o ambiente do programa...
!PYCMD! -m venv .venv
if errorlevel 1 (
  echo [ERRO] Nao foi possivel criar o ambiente.
  pause
  exit /b 1
)

:libs
echo Instalando as bibliotecas necessarias...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERRO] Falha ao instalar as bibliotecas. Verifique sua conexao.
  pause
  exit /b 1
)

echo.
echo ============================================
echo    Pronto! Abra o programa com:  abrir.bat
echo ============================================
echo.
pause
