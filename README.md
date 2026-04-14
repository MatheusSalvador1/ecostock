Alunos:

Diego de Gusmão Gaseo / matricula:01659279  
Erick Ayrton Lins Santos / matricula:01606295  
Fernando Silva De oliveira / matricula:01612125    
Luiz Felipe Bernardo Cavalcante/matricula:01605724  
Cassio Vinicius da Silva Mota/01584279   
João Matheus Salvador de Carvalho/ matrícula: 01603692 





# EcoStock Revisado

Versão revisada do projeto EcoStock, preparada para rodar localmente no Windows com XAMPP/MariaDB e dois arquivos `.bat`:

- `01_instalar.bat` → cria venv, instala dependências e inicializa o banco.
- `02_rodar.bat` → sobe o sistema.

## Melhorias aplicadas

- correção do host e porta padrão para evitar erro de soquete no Windows
- criação automática do usuário admin caso ele não exista
- rota `/health` para testar a aplicação
- teardown da conexão com o banco
- scheduler iniciado apenas uma vez mesmo com debug
- `.env.example` ajustado para cenário local com XAMPP
- script Python para inicializar o banco sem depender do `mysql.exe`
- rota manual de notificação corrigida para `/api/v1/notificar/testar`

## Requisitos

- Python 3.10+
- XAMPP com MariaDB iniciado

## Como usar

1. Inicie o MariaDB no XAMPP.
2. Dê dois cliques em `01_instalar.bat`.
3. Depois rode `02_rodar.bat`.
4. Acesse `http://127.0.0.1:8000`.

## Login inicial

- usuário: `admin`
- senha: `Admin@123`

O admin é validado automaticamente ao iniciar a aplicação. Se quiser forçar a redefinição da senha do admin ao subir o sistema, altere no `.env`:

```env
ADMIN_FORCE_RESET_ON_START=True
ADMIN_INITIAL_PASSWORD=NovaSenha@123
```

## Banco de dados

Configuração padrão do `.env.example`:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=ecostock_db
```

## Observações

- Se quiser usar e-mail, preencha as variáveis SMTP no `.env`.
- Se a porta 8000 estiver ocupada, troque `APP_PORT` no `.env`.


## Correção v3
- Corrigido bug de timeout de sessão no Windows/Flask ao comparar `float` com `timedelta`.

EcoStock - Sprint 2 (Completo)
1. Backend Funcional
O backend foi desenvolvido em Flask (Python), utilizando arquitetura modular. O sistema
implementa autenticação, controle de estoque por lote, saída FIFO, auditoria, perdas e lucro.
2. Endpoints da API
Método Rota Descrição
GET /api/v1/estoque Lista estoque
POST /api/v1/novo_produto Cadastrar produto
POST /api/v1/novo_lote Cadastrar lote
POST /api/v1/produto/<id>/saida_fifo Saída FIFO
POST /api/v1/lote/<id>/descartar Descarte vencido
GET /api/v1/movimentacoes Histórico
GET /api/v1/gestor-resumo Dados financeiros
3. Exemplo de Requisição
POST /api/v1/produto/1/saida_fifo { "quantidade": 5, "motivo": "Venda" }
4. Banco de Dados
O sistema utiliza MariaDB com tabelas: usuarios, produtos, lotes, movimentacoes_estoque,
auditoria e notificacoes.
5. Regras de Negócio
- Saída FIFO automática - Bloqueio de produtos vencidos - Descarte obrigatório de vencidos -
Cálculo de lucro e perdas - Auditoria de ações
6. Execução do Sistema
Para rodar o sistema: 1. Iniciar MariaDB no XAMPP 2. Rodar 01_instalar.bat 3. Rodar 02_rodar.bat
4. Acessar http://127.0.0.1:8000 Login: admin / Admin@123
7. Evolução
O sistema evoluiu de um modelo conceitual para um sistema funcional com backend real, banco persistente e regras completas.
