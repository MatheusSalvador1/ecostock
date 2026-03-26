from __future__ import annotations

import bcrypt
from flask import current_app

from app.utils.db import execute, query


ADMIN_COLUMNS = (
    'can_view_audit',
    'can_edit_stock',
    'can_delete_items',
    'can_add_product',
)


def ensure_admin_user() -> None:
    login = current_app.config['ADMIN_INITIAL_LOGIN']
    senha = current_app.config['ADMIN_INITIAL_PASSWORD']
    email = current_app.config['ADMIN_INITIAL_EMAIL']
    force_reset = current_app.config['ADMIN_FORCE_RESET_ON_START']

    existing = query('SELECT * FROM usuarios WHERE login = %s', (login,), fetchone=True)
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    if not existing:
        execute(
            """
            INSERT INTO usuarios (
                login, email, senha_hash, nivel_acesso, ativo,
                can_view_audit, can_edit_stock, can_delete_items, can_add_product
            ) VALUES (%s, %s, %s, 'Administrador', 1, 1, 1, 1, 1)
            """,
            (login, email, senha_hash),
        )
        current_app.logger.info('Usuário administrador inicial criado: %s', login)
        return

    needs_update = (
        existing['nivel_acesso'] != 'Administrador'
        or not bool(existing['ativo'])
        or any(not bool(existing.get(col, 0)) for col in ADMIN_COLUMNS)
        or force_reset
    )
    if not needs_update:
        return

    execute(
        """
        UPDATE usuarios
           SET email = COALESCE(%s, email),
               nivel_acesso = 'Administrador',
               ativo = 1,
               can_view_audit = 1,
               can_edit_stock = 1,
               can_delete_items = 1,
               can_add_product = 1,
               senha_hash = CASE WHEN %s THEN %s ELSE senha_hash END
         WHERE id = %s
        """,
        (email, 1 if force_reset else 0, senha_hash, existing['id']),
    )
    current_app.logger.info('Usuário administrador inicial validado: %s', login)
