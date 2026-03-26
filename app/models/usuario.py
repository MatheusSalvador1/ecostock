"""
Model de Usuário — integrado com Flask-Login
"""
from flask_login import UserMixin
from app import login_manager
from app.utils.db import query


class Usuario(UserMixin):
    def __init__(self, data: dict):
        self.id               = data['id']
        self.login            = data['login']
        self.nivel_acesso     = data['nivel_acesso']
        self.ativo            = bool(data['ativo'])
        self.email            = data.get('email')
        self.can_view_audit   = bool(data.get('can_view_audit', 0))
        self.can_edit_stock   = bool(data.get('can_edit_stock', 0))
        self.can_delete_items = bool(data.get('can_delete_items', 0))
        self.can_add_product  = bool(data.get('can_add_product', 0))

    def is_admin(self):
        return self.nivel_acesso == 'Administrador'

    def is_liberacao(self):
        return self.nivel_acesso == 'Liberacao'

    def pode_editar(self):
        return self.can_edit_stock or self.is_admin()

    def pode_excluir(self):
        return self.can_delete_items or self.is_admin()

    def pode_auditar(self):
        return self.can_view_audit or self.is_admin()

    def pode_cadastrar(self):
        return self.can_add_product or self.is_admin()

    def get_id(self):
        return str(self.id)

    @staticmethod
    def buscar_por_id(user_id):
        row = query("SELECT * FROM usuarios WHERE id = %s", (user_id,), fetchone=True)
        return Usuario(row) if row else None

    @staticmethod
    def buscar_por_login(login):
        row = query("SELECT * FROM usuarios WHERE login = %s", (login,), fetchone=True)
        return Usuario(row) if row else None


@login_manager.user_loader
def load_user(user_id):
    return Usuario.buscar_por_id(user_id)
