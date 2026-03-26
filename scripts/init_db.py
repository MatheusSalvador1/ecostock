from __future__ import annotations

import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env')

HOST = os.getenv('DB_HOST', 'localhost')
PORT = int(os.getenv('DB_PORT', '3306'))
USER = os.getenv('DB_USER', 'root')
PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'ecostock_db')
SCHEMA_PATH = BASE_DIR / 'schema.sql'


def split_sql(sql_text: str) -> list[str]:
    statements = []
    current = []
    in_single = False
    in_double = False
    for char in sql_text:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        if char == ';' and not in_single and not in_double:
            statement = ''.join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
    tail = ''.join(current).strip()
    if tail:
        statements.append(tail)
    return statements


def clean_sql(sql_text: str) -> str:
    lines = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith('--'):
            continue
        lines.append(line)
    return '\n'.join(lines)


def has_column(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
          FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """,
        (DB_NAME, table, column),
    )
    return cur.fetchone()[0] > 0


def ensure_evolution(cur) -> None:
    alterations = {
        ('produtos', 'preco_referencia'): "ALTER TABLE produtos ADD COLUMN preco_referencia DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER estoque_min",
        ('lotes', 'custo_unitario'): "ALTER TABLE lotes ADD COLUMN custo_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER quantidade_inicial",
        ('lotes', 'preco_venda_unitario'): "ALTER TABLE lotes ADD COLUMN preco_venda_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER custo_unitario",
        ('lotes', 'fornecedor'): "ALTER TABLE lotes ADD COLUMN fornecedor VARCHAR(120) DEFAULT NULL AFTER preco_venda_unitario",
        ('movimentacoes_estoque', 'motivo'): "ALTER TABLE movimentacoes_estoque ADD COLUMN motivo VARCHAR(80) DEFAULT NULL AFTER quantidade_posterior",
        ('movimentacoes_estoque', 'valor_unitario'): "ALTER TABLE movimentacoes_estoque ADD COLUMN valor_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00 AFTER motivo",
        ('movimentacoes_estoque', 'valor_total'): "ALTER TABLE movimentacoes_estoque ADD COLUMN valor_total DECIMAL(14,2) NOT NULL DEFAULT 0.00 AFTER valor_unitario",
    }
    for (table, column), sql in alterations.items():
        if not has_column(cur, table, column):
            cur.execute(sql)

    cur.execute(
        """
        ALTER TABLE movimentacoes_estoque
        MODIFY COLUMN tipo_movimento
        ENUM('ENTRADA','SAIDA','AJUSTE_POSITIVO','AJUSTE_NEGATIVO','DESCARTE_VENCIDO','AVARIA','EXCLUSAO') NOT NULL
        """
    )



def main() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f'Schema não encontrado: {SCHEMA_PATH}')

    conn = pymysql.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        charset='utf8mb4',
        autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            sql = clean_sql(SCHEMA_PATH.read_text(encoding='utf-8'))
            for statement in split_sql(sql):
                cur.execute(statement)
            ensure_evolution(cur)
        conn.commit()
        print(f'Banco inicializado com sucesso em {HOST}:{PORT}/{DB_NAME}')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
