@echo off
chcp 65001 >nul
cls

:: Redireciona tudo para log tambem
set LOGFILE=ecostock_log.txt
echo EcoStock Setup Log > %LOGFILE%
echo Data: %date% %time% >> %LOGFILE%
echo. >> %LOGFILE%

echo.
echo  ================================
echo   EcoStock - Setup Windows
echo  ================================
echo.

:: ==============================================================
:: PASSO 1 - Python
:: ==============================================================
echo [1/5] Verificando Python...
echo [1/5] Verificando Python... >> %LOGFILE%

python --version >> %LOGFILE% 2>&1
if errorlevel 1 (
    py --version >> %LOGFILE% 2>&1
    if errorlevel 1 (
        echo.
        echo  ERRO: Python nao encontrado no sistema!
        echo  ERRO: Python nao encontrado >> %LOGFILE%
        echo.
        echo  SOLUCAO:
        echo  1. Acesse https://python.org/downloads
        echo  2. Baixe a versao mais recente
        echo  3. Durante instalacao marque: "Add Python to PATH"
        echo  4. Reinicie o computador e tente novamente
        echo.
        echo  Log salvo em: %LOGFILE%
        pause
        exit /b 1
    )
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% --version
echo  OK - Python encontrado
echo.

:: ==============================================================
:: PASSO 2 - Pip
:: ==============================================================
echo [2/5] Verificando pip...
echo [2/5] Verificando pip... >> %LOGFILE%

%PYTHON% -m pip --version >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo  ERRO: pip nao encontrado!
    echo  ERRO: pip nao encontrado >> %LOGFILE%
    echo  Tentando instalar pip...
    %PYTHON% -m ensurepip --upgrade >> %LOGFILE% 2>&1
)
echo  OK - pip encontrado
echo.

:: ==============================================================
:: PASSO 3 - Ambiente Virtual
:: ==============================================================
echo [3/5] Criando ambiente virtual...
echo [3/5] Ambiente virtual... >> %LOGFILE%

if not exist "venv\" (
    %PYTHON% -m venv venv >> %LOGFILE% 2>&1
    if errorlevel 1 (
        echo.
        echo  ERRO ao criar ambiente virtual!
        echo  ERRO ao criar venv >> %LOGFILE%
        echo  Veja o arquivo: %LOGFILE%
        pause
        exit /b 1
    )
    echo  OK - Ambiente virtual criado
) else (
    echo  OK - Ambiente virtual ja existe
)

call venv\Scripts\activate.bat >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo  AVISO: nao conseguiu ativar venv, usando Python do sistema
    echo  AVISO: venv nao ativado >> %LOGFILE%
    set PYTHON=%PYTHON%
) else (
    set PYTHON=python
    echo  OK - Ambiente virtual ativado
)
echo.

:: ==============================================================
:: PASSO 4 - Dependencias
:: ==============================================================
echo [4/5] Instalando dependencias (pode demorar)...
echo [4/5] Instalando dependencias... >> %LOGFILE%

python -m pip install --upgrade pip >> %LOGFILE% 2>&1
python -m pip install -r requirements.txt >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo.
    echo  ERRO ao instalar dependencias!
    echo  ERRO pip install >> %LOGFILE%
    echo.
    echo  Possiveis causas:
    echo  - Sem conexao com internet
    echo  - requirements.txt nao encontrado
    echo  - Versao do Python incompativel
    echo.
    echo  Veja detalhes em: %LOGFILE%
    pause
    exit /b 1
)
echo  OK - Dependencias instaladas
echo.

:: ==============================================================
:: PASSO 5 - .env
:: ==============================================================
echo [5/5] Verificando .env...
echo [5/5] Verificando .env... >> %LOGFILE%

if not exist ".env" (
    if not exist ".env.example" (
        echo  ERRO: arquivo .env.example nao encontrado!
        echo  ERRO: .env.example ausente >> %LOGFILE%
        echo  Certifique-se de estar na pasta correta do projeto.
        pause
        exit /b 1
    )
    copy .env.example .env >nul
    echo  OK - .env criado
    echo.
    echo  ATENCAO: Configure o .env com seus dados do MariaDB!
    echo  Abrindo no Bloco de Notas...
    notepad .env
    echo.
    pause
) else (
    echo  OK - .env ja existe
)
echo.

:: ==============================================================
:: Schema lembrete
:: ==============================================================
echo  Lembrete: execute o schema.sql no MariaDB se ainda nao fez:
echo  mysql -u root -p ^< schema.sql
echo.
echo  (Se ja fez, pode ignorar)
echo.
pause

:: ==============================================================
:: INICIAR
:: ==============================================================
echo.
echo  ================================
echo   Iniciando EcoStock...
echo   Acesse: http://localhost:5000
echo   Login:  admin / Admin@123
echo  ================================
echo.
echo  Iniciando servidor... >> %LOGFILE%

python run.py >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo.
    echo  ERRO ao iniciar o servidor Flask!
    echo  Veja o arquivo %LOGFILE% para detalhes.
    echo.
    type %LOGFILE%
    pause
)