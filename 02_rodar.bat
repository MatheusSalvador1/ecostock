@echo off
chcp 65001 >nul
setlocal enableextensions
cd /d "%~dp0"

set "RUNPY="
if exist ".venv\Scripts\python.exe" set "RUNPY=.venv\Scripts\python.exe"
if not defined RUNPY (
  py -3 --version >nul 2>&1 && set "RUNPY=py -3"
)
if not defined RUNPY (
  py --version >nul 2>&1 && set "RUNPY=py"
)
if not defined RUNPY (
  python --version >nul 2>&1 && set "RUNPY=python"
)
if not defined RUNPY (
  echo Python nao encontrado.
  echo Rode primeiro o 01_instalar.bat ou instale o Python 3.10+.
  pause
  exit /b 1
)

echo ================================
echo  EcoStock - Inicializacao
echo ================================
echo.
echo Acesse: http://127.0.0.1:8000
echo Login:  admin
echo Senha:  Admin@123
echo.
call %RUNPY% run.py
pause
