@echo off
chcp 65001 >nul
setlocal enableextensions
cd /d "%~dp0"

set "LOGFILE=%~dp0install_log.txt"
> "%LOGFILE%" echo EcoStock - instalacao
>>"%LOGFILE%" echo Data: %date% %time%

echo ================================
echo  EcoStock - Instalacao
echo ================================
echo.

set "PYTHON_CMD="
py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
  py --version >nul 2>&1 && set "PYTHON_CMD=py"
)
if not defined PYTHON_CMD (
  python --version >nul 2>&1 && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
  echo Python nao encontrado.
  echo Instale Python 3.10+ e marque Add Python to PATH.
  pause
  exit /b 1
)

echo Usando: %PYTHON_CMD%
>>"%LOGFILE%" echo Python selecionado: %PYTHON_CMD%

if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo Arquivo .env criado com configuracao padrao para XAMPP.
)

set "RUNPY=%PYTHON_CMD%"
set "PIPPY=%PYTHON_CMD%"

if not exist ".venv\Scripts\python.exe" (
  echo Tentando criar ambiente virtual...
  call %PYTHON_CMD% -m venv .venv >>"%LOGFILE%" 2>&1
)

if exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual criado com sucesso.
  set "RUNPY=.venv\Scripts\python.exe"
  set "PIPPY=.venv\Scripts\python.exe"
) else (
  echo.
  echo Aviso: nao foi possivel criar ambiente virtual.
  echo Vou continuar usando o Python instalado no Windows.
  echo Veja "%LOGFILE%" depois se quiser analisar.
  echo.
)

echo Atualizando pip...
call %PIPPY% -m pip install --upgrade pip >>"%LOGFILE%" 2>&1 || (
  echo Falha ao atualizar o pip. Veja "%LOGFILE%".
  pause
  exit /b 1
)

echo Instalando dependencias...
call %PIPPY% -m pip install -r requirements.txt >>"%LOGFILE%" 2>&1 || (
  echo Falha ao instalar dependencias. Veja "%LOGFILE%".
  pause
  exit /b 1
)

echo.
echo Inicializando banco de dados...
call %RUNPY% scripts\init_db.py >>"%LOGFILE%" 2>&1 || (
  echo.
  echo Nao foi possivel inicializar o banco automaticamente.
  echo Confira o arquivo .env e se o MariaDB do XAMPP esta iniciado.
  echo Veja "%LOGFILE%" para detalhes.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
echo.
echo Proximo passo:
echo   1. Certifique-se de que o MariaDB do XAMPP esteja ligado.
echo   2. Rode o arquivo 02_rodar.bat
echo.
echo Login inicial padrao:
echo   usuario: admin
echo   senha:   Admin@123
echo.
pause
