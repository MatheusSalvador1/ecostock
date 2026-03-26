#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  EcoStock — Setup & Run Automático
#  Execute:  chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════

set -e  # Para ao primeiro erro

# ── Cores ──────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'
BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()    { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error()   { echo -e "${RED}[ERRO]${NC}  $1"; exit 1; }
section() { echo -e "\n${BOLD}━━━  $1  ━━━${NC}"; }

clear
echo -e "${GREEN}"
echo "  ███████╗ ██████╗ ██████╗ ███████╗████████╗ ██████╗  ██████╗██╗  ██╗"
echo "  ██╔════╝██╔════╝██╔═══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔════╝██║ ██╔╝"
echo "  █████╗  ██║     ██║   ██║███████╗   ██║   ██║   ██║██║     █████╔╝ "
echo "  ██╔══╝  ██║     ██║   ██║╚════██║   ██║   ██║   ██║██║     ██╔═██╗ "
echo "  ███████╗╚██████╗╚██████╔╝███████║   ██║   ╚██████╔╝╚██████╗██║  ██╗"
echo "  ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝   ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "  ${BOLD}Sistema de Gestão de Validade — Setup Automático${NC}"
echo ""

# ═══════════════════════════════════════════════════════════════
# ETAPA 1 — Verificar Python
# ═══════════════════════════════════════════════════════════════
section "ETAPA 1 — Python"

if ! command -v python3 &>/dev/null; then
    error "Python 3 não encontrado. Instale em https://python.org"
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VERSION encontrado"

if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    ok "Versão compatível"
else
    warn "Recomendado Python 3.10+. Sua versão: $PYTHON_VERSION"
fi

# ═══════════════════════════════════════════════════════════════
# ETAPA 2 — Ambiente Virtual
# ═══════════════════════════════════════════════════════════════
section "ETAPA 2 — Ambiente Virtual"

if [ ! -d "venv" ]; then
    info "Criando ambiente virtual..."
    python3 -m venv venv
    ok "Ambiente virtual criado em ./venv"
else
    ok "Ambiente virtual já existe"
fi

# Ativar venv
source venv/bin/activate
info "Ambiente virtual ativado"

# ═══════════════════════════════════════════════════════════════
# ETAPA 3 — Dependências
# ═══════════════════════════════════════════════════════════════
section "ETAPA 3 — Instalando Dependências"

pip install --upgrade pip -q
info "Instalando pacotes do requirements.txt..."
pip install -r requirements.txt -q
ok "Todas as dependências instaladas"

# ═══════════════════════════════════════════════════════════════
# ETAPA 4 — Arquivo .env
# ═══════════════════════════════════════════════════════════════
section "ETAPA 4 — Configuração (.env)"

if [ ! -f ".env" ]; then
    cp .env.example .env
    warn "Arquivo .env criado a partir do .env.example"
    echo ""
    echo -e "  ${YELLOW}⚠️  Configure o .env antes de continuar:${NC}"
    echo ""
    echo -e "  ${BOLD}MariaDB:${NC}"
    echo "    DB_HOST=localhost"
    echo "    DB_USER=seu_usuario"
    echo "    DB_PASSWORD=sua_senha"
    echo "    DB_NAME=ecostock_db"
    echo ""
    echo -e "  ${BOLD}Gmail (opcional — para alertas):${NC}"
    echo "    MAIL_USERNAME=seu@gmail.com"
    echo "    MAIL_PASSWORD=sua_senha_de_app  (não a senha normal!)"
    echo "    ADMIN_EMAIL=admin@email.com"
    echo ""
    read -p "  Pressione ENTER após editar o .env (ou CTRL+C para cancelar)..."
else
    ok ".env já configurado"
fi

# ═══════════════════════════════════════════════════════════════
# ETAPA 5 — MariaDB
# ═══════════════════════════════════════════════════════════════
section "ETAPA 5 — Banco de Dados MariaDB"

# Lê variáveis do .env
DB_HOST=$(grep '^DB_HOST' .env | cut -d'=' -f2 | tr -d ' ')
DB_PORT=$(grep '^DB_PORT' .env | cut -d'=' -f2 | tr -d ' ')
DB_USER=$(grep '^DB_USER' .env | cut -d'=' -f2 | tr -d ' ')
DB_PASSWORD=$(grep '^DB_PASSWORD' .env | cut -d'=' -f2 | tr -d ' ')
DB_NAME=$(grep '^DB_NAME' .env | cut -d'=' -f2 | tr -d ' ')

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-3306}
DB_NAME=${DB_NAME:-ecostock_db}

if command -v mysql &>/dev/null; then
    info "Tentando criar banco de dados e tabelas..."
    if mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" < schema.sql 2>/dev/null; then
        ok "Banco '${DB_NAME}' criado/atualizado com sucesso!"
    else
        warn "Não foi possível executar o schema automaticamente."
        echo ""
        echo -e "  Execute manualmente:"
        echo -e "  ${CYAN}mysql -u $DB_USER -p < schema.sql${NC}"
        echo ""
        read -p "  Pressione ENTER após executar o schema..."
    fi
else
    warn "mysql não encontrado no PATH."
    echo ""
    echo -e "  Execute o schema manualmente:"
    echo -e "  ${CYAN}mysql -u $DB_USER -p < schema.sql${NC}"
    echo ""

    # Testa conexão via Python mesmo assim
    info "Testando conexão via Python/PyMySQL..."
    python3 -c "
import pymysql, os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST','localhost'),
        port=int(os.getenv('DB_PORT',3306)),
        user=os.getenv('DB_USER','root'),
        password=os.getenv('DB_PASSWORD',''),
        database=os.getenv('DB_NAME','ecostock_db')
    )
    conn.close()
    print('Conexão bem-sucedida!')
except Exception as e:
    print(f'Falha na conexão: {e}')
    exit(1)
" && ok "Banco acessível" || warn "Verifique as credenciais no .env e se o schema foi aplicado"
fi

# ═══════════════════════════════════════════════════════════════
# ETAPA 6 — Verificação final
# ═══════════════════════════════════════════════════════════════
section "ETAPA 6 — Verificação Final"

python3 -c "
import importlib
pkgs = ['flask','flask_login','flask_mail','pymysql','bcrypt','dotenv','apscheduler']
ok = True
for p in pkgs:
    try:
        importlib.import_module(p)
        print(f'  ✅ {p}')
    except ImportError:
        print(f'  ❌ {p} — FALTANDO')
        ok = False
exit(0 if ok else 1)
" || error "Dependências com problema. Rode: pip install -r requirements.txt"

# ═══════════════════════════════════════════════════════════════
# INÍCIO
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BOLD}✅  Tudo pronto! Iniciando o EcoStock...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  🌐  Acesse:  ${BOLD}http://localhost:5000${NC}"
echo -e "  👤  Login:   ${BOLD}admin${NC}"
echo -e "  🔑  Senha:   ${BOLD}Admin@123${NC}  ← ${RED}troque imediatamente!${NC}"
echo ""
echo -e "  Para parar: ${CYAN}CTRL+C${NC}"
echo ""

python3 run.py
