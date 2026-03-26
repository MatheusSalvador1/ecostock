"""
Blueprint: Gestão de Usuários
REGRA 2: Permissões granulares por nível
REGRA 5: Bloqueio e controle de acesso
"""
import bcrypt
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.utils.db import query, execute
from app.services.auditoria import registrar

users_bp = Blueprint('users', __name__)


def _admin_required(fn):
    """Decorator: apenas Administradores."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_admin():
            registrar('ACESSO_NEGADO', f'Acesso admin negado para {current_user.login}', 'Bloqueado')
            return jsonify({'erro': 'Apenas administradores'}), 403
        return fn(*args, **kwargs)
    return login_required(wrapper)


# ── PÁGINA ────────────────────────────────────────────────────────────────────
@users_bp.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin():
        return render_template('dashboard/bloqueado.html')
    lista = query("SELECT * FROM usuarios ORDER BY nivel_acesso, login")
    return render_template('users/usuarios.html', usuarios=lista)


# ── API: LISTAR ───────────────────────────────────────────────────────────────
@users_bp.route('/api/v1/usuarios/lista', methods=['GET'])
@_admin_required
def listar_usuarios():
    lista = query("""
        SELECT id, login, nivel_acesso, ativo, email,
               can_view_audit, can_edit_stock, can_delete_items, can_add_product,
               criado_em, ultimo_login
        FROM usuarios ORDER BY nivel_acesso, login
    """)
    result = []
    for u in lista:
        d = dict(u)
        d['criado_em']    = str(d['criado_em']) if d['criado_em'] else None
        d['ultimo_login'] = str(d['ultimo_login']) if d['ultimo_login'] else None
        result.append(d)
    return jsonify(result)


# ── API: ATUALIZAR PERMISSÕES ─────────────────────────────────────────────────
@users_bp.route('/api/v1/usuario/<int:uid>/atualizar', methods=['POST'])
@_admin_required
def atualizar_usuario(uid):
    if uid == current_user.id:
        return jsonify({'erro': 'Você não pode alterar suas próprias permissões'}), 400

    dados = request.get_json()
    antes = query("SELECT * FROM usuarios WHERE id=%s", (uid,), fetchone=True)
    if not antes:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    execute("""
        UPDATE usuarios SET
            nivel_acesso     = %s,
            ativo            = %s,
            can_view_audit   = %s,
            can_edit_stock   = %s,
            can_delete_items = %s,
            can_add_product  = %s
        WHERE id = %s
    """, (
        dados.get('nivel',  antes['nivel_acesso']),
        dados.get('ativo',  antes['ativo']),
        dados.get('audit',  antes['can_view_audit']),
        dados.get('edit',   antes['can_edit_stock']),
        dados.get('delete', antes['can_delete_items']),
        dados.get('add',    antes['can_add_product']),
        uid
    ))

    depois = {k: dados.get(k) for k in ['nivel','ativo','audit','edit','delete','add']}
    registrar('PERMISSAO_ALTERADA',
              f'Permissões do usuário {antes["login"]} (id={uid}) atualizadas',
              dados_antes={k: antes[k] for k in ['nivel_acesso','ativo','can_view_audit',
                                                   'can_edit_stock','can_delete_items','can_add_product']},
              dados_depois=depois)
    return jsonify({'sucesso': True})


# ── API: EXCLUIR USUÁRIO ──────────────────────────────────────────────────────
@users_bp.route('/api/v1/usuario/<int:uid>', methods=['DELETE'])
@_admin_required
def excluir_usuario(uid):
    if uid == current_user.id:
        return jsonify({'erro': 'Você não pode excluir a si mesmo'}), 400

    user = query("SELECT login FROM usuarios WHERE id=%s", (uid,), fetchone=True)
    if not user:
        return jsonify({'erro': 'Usuário não encontrado'}), 404

    execute("DELETE FROM usuarios WHERE id=%s", (uid,))
    registrar('EXCLUSAO_USUARIO', f'Usuário {user["login"]} (id={uid}) removido',
              dados_antes={'login': user['login'], 'id': uid})
    return jsonify({'sucesso': True})


# ── API: REDEFINIR SENHA (admin) ──────────────────────────────────────────────
@users_bp.route('/api/v1/usuario/<int:uid>/senha', methods=['POST'])
@_admin_required
def redefinir_senha(uid):
    dados = request.get_json()
    nova  = dados.get('nova_senha', '').encode('utf-8')
    if len(nova) < 6:
        return jsonify({'erro': 'Senha deve ter ao menos 6 caracteres'}), 400

    h = bcrypt.hashpw(nova, bcrypt.gensalt()).decode('utf-8')
    execute("UPDATE usuarios SET senha_hash=%s WHERE id=%s", (h, uid))

    user = query("SELECT login FROM usuarios WHERE id=%s", (uid,), fetchone=True)
    registrar('SENHA_REDEFINIDA', f'Senha do usuário {user["login"]} redefinida pelo admin')
    return jsonify({'sucesso': True})