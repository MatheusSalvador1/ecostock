"""Conexão centralizada com MariaDB/MySQL usando PyMySQL."""
from __future__ import annotations

import pymysql
import pymysql.cursors
from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=current_app.config['DB_HOST'],
            port=current_app.config['DB_PORT'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD'],
            database=current_app.config['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
            autocommit=False,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
    else:
        g.db.ping(reconnect=True)
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, params=None, fetchone=False):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone() if fetchone else cur.fetchall()


def execute(sql, params=None):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid


def executemany(sql, params_list):
    conn = get_db()
    with conn.cursor() as cur:
        cur.executemany(sql, params_list)
        conn.commit()


def ping_db():
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute('SELECT DATABASE() AS db')
            row = cur.fetchone()
        return True, row.get('db') if row else current_app.config['DB_NAME']
    except Exception as exc:
        return False, str(exc)
