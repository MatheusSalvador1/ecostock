# ⚡ Guia Rápido — Como Rodar o EcoStock

## Linux / Mac

```bash
# 1. Entre na pasta do projeto
cd ecostock

# 2. Dê permissão e execute
chmod +x setup.sh
./setup.sh
```

## Windows

```
1. Abra a pasta ecostock no Explorador de Arquivos
2. Dê duplo clique em: setup.bat
```

---

## O que o script faz automaticamente:
1. ✅ Verifica Python 3.10+
2. ✅ Cria ambiente virtual (`venv/`)
3. ✅ Instala todas as dependências
4. ✅ Cria o `.env` a partir do `.env.example`
5. ✅ Tenta criar o banco MariaDB
6. ✅ Verifica se tudo está OK
7. ✅ Sobe o servidor Flask

---

## Pré-requisitos (instale antes)

### Python 3.10+
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update && sudo apt install python3 python3-pip python3-venv -y
  ```
- **Mac:**
  ```bash
  brew install python3
  ```
- **Windows:** https://python.org/downloads — marque ☑️ "Add to PATH"

### MariaDB
- **Linux:**
  ```bash
  sudo apt install mariadb-server -y
  sudo systemctl start mariadb
  sudo mysql_secure_installation
  ```
- **Mac:**
  ```bash
  brew install mariadb
  brew services start mariadb
  ```
- **Windows:** https://mariadb.org/download — instale o MariaDB Server

---

## Configurar o .env (obrigatório)

Edite o arquivo `.env` gerado pelo script:

```env
# Banco (obrigatório)
DB_HOST=localhost
DB_USER=root          # ou seu usuário MariaDB
DB_PASSWORD=          # senha do MariaDB
DB_NAME=ecostock_db

# Gmail (opcional — para alertas automáticos)
MAIL_USERNAME=seu@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Senha de App Google
ADMIN_EMAIL=admin@email.com
```

### Como criar Senha de App do Gmail:
1. Acesse https://myaccount.google.com
2. Segurança → Verificação em 2 etapas (ative se necessário)
3. Segurança → Senhas de App → Outro → "EcoStock"
4. Copie a senha gerada para `MAIL_PASSWORD`

---

## Aplicar o Schema no MariaDB

Se o script não aplicou automaticamente:

```bash
mysql -u root -p < schema.sql
```

Ou abra o HeidiSQL/DBeaver/Workbench e execute o `schema.sql`.

---

## Acessar o Sistema

Após o script subir o servidor:

| | |
|---|---|
| 🌐 URL | http://localhost:5000 |
| 👤 Login | `admin` |
| 🔑 Senha | `Admin@123` |

> ⚠️ **Troque a senha do admin imediatamente após o primeiro acesso!**

---

## Rodar sem o script (manual)

```bash
# Criar e ativar venv
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# ou: venv\Scripts\activate.bat  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar banco
mysql -u root -p < schema.sql

# Configurar .env
cp .env.example .env
# edite o .env

# Subir o servidor
python run.py
```

---

## Problemas Comuns

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError: flask` | `pip install -r requirements.txt` |
| `Access denied for user` | Verifique `DB_USER` e `DB_PASSWORD` no `.env` |
| `Unknown database 'ecostock_db'` | Execute o `schema.sql` no MariaDB |
| `Address already in use` | Já tem algo rodando na porta 5000. Mude em `run.py`: `port=5001` |
| Emails não chegam | Verifique se usou **Senha de App** (não a senha normal) |
