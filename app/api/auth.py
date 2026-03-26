"""
Blueprint: Autenticação
Rotas: /login  /logout  /registrar
REGRA 5: Bloqueio de usuários sem permissão + sessão por inatividade
"""
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.utils.db import query, execute
from app.services.auditoria import registrar
from app.models.usuario import Usuario

auth_bp = Blueprint('auth', __name__)


# ── REGRA 5: timeout de sessão por inatividade ─────────────────────────────────
@auth_bp.before_app_request
def checar_timeout_sessao():
    from flask import current_app
    import time
    if current_user.is_authenticated:
        timeout_cfg = current_app.config.get('PERMANENT_SESSION_LIFETIME', 1800)
        timeout = timeout_cfg.total_seconds() if hasattr(timeout_cfg, 'total_seconds') else float(timeout_cfg)
        ultimo = float(session.get('_last_activity', 0) or 0)
        agora = time.time()
        if ultimo and (agora - ultimo) > timeout:
            logout_user()
            session.clear()
            registrar('SESSAO_EXPIRADA', 'Sessão expirada por inatividade', 'Bloqueado')
            flash('Sua sessão expirou por inatividade. Faça login novamente.', 'warning')
            return redirect(url_for('auth.login'))
        session['_last_activity'] = agora
        session.permanent = True


# ── LOGIN ──────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        senha     = request.form.get('senha', '').encode('utf-8')

        user_data = query("SELECT * FROM usuarios WHERE login = %s", (login_val,), fetchone=True)

        if not user_data:
            registrar('LOGIN', f'Tentativa com login inexistente: {login_val}',
                      resultado='Falha', login_override='anonimo')
            flash('Usuário ou senha incorretos.', 'error')
            return render_template('auth/login.html')

        if not bcrypt.checkpw(senha, user_data['senha_hash'].encode('utf-8')):
            registrar('LOGIN', f'Senha incorreta para: {login_val}',
                      resultado='Falha', login_override=login_val)
            flash('Usuário ou senha incorretos.', 'error')
            return render_template('auth/login.html')

        if not user_data['ativo']:
            registrar('LOGIN', f'Acesso bloqueado — conta inativa: {login_val}',
                      resultado='Bloqueado', login_override=login_val)
            flash('Sua conta está desativada. Contate o administrador.', 'error')
            return render_template('auth/login.html')

        usuario = Usuario(user_data)
        login_user(usuario, remember=False)
        execute("UPDATE usuarios SET ultimo_login = NOW() WHERE id = %s", (usuario.id,))

        import time
        session['_last_activity'] = time.time()
        session.permanent = True

        registrar('LOGIN', f'Login realizado com sucesso: {login_val}')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')


# ── LOGOUT ─────────────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
@login_required
def logout():
    registrar('LOGOUT', f'Usuário {current_user.login} encerrou sessão')
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


# ── REGISTRAR ─────────────────────────────────────────────────────────────────
@auth_bp.route('/registrar', methods=['GET', 'POST'])
def registrar_usuario():
    if request.method == 'POST':
        login_val = request.form.get('login', '').strip()
        senha     = request.form.get('senha', '').encode('utf-8')
        email     = request.form.get('email', '').strip() or None

        if len(login_val) < 3:
            flash('Login deve ter ao menos 3 caracteres.', 'error')
            return render_template('auth/registrar.html')

        existe = query("SELECT id FROM usuarios WHERE login = %s", (login_val,), fetchone=True)
        if existe:
            flash('Este login já está em uso.', 'error')
            return render_template('auth/registrar.html')

        hash_senha = bcrypt.hashpw(senha, bcrypt.gensalt()).decode('utf-8')

        # REGRA 5: novos usuários sempre entram como Operador (nível Liberacao até admin ativar)
        execute(
            """INSERT INTO usuarios (login, senha_hash, nivel_acesso, ativo, email)
               VALUES (%s, %s, 'Liberacao', 1, %s)""",
            (login_val, hash_senha, email)
        )

        registrar('CADASTRO_USUARIO', f'Novo usuário registrado: {login_val}',
                  login_override=login_val)

        # Notifica admin por email
        from flask import current_app
        from app.services.notificacoes import enviar_email_boas_vindas
        admin_email = current_app.config.get('ADMIN_EMAIL')
        enviar_email_boas_vindas(admin_email, login_val)

        flash('Conta criada! Aguarde a liberação do administrador.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registrar.html')
