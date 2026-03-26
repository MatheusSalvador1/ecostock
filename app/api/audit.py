"""
Blueprint: Auditoria
REGRA 3: Logs imutaveis com filtros avancados
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.utils.db import query
from app.services.auditoria import registrar

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/auditoria')
@login_required
def auditoria():
    if not current_user.pode_auditar():
        registrar('ACESSO_NEGADO', 'Tentativa de acesso a auditoria sem permissao', 'Bloqueado')
        return render_template('dashboard/bloqueado.html')
    return render_template('audit/auditoria.html')


@audit_bp.route('/api/v1/auditoria/logs', methods=['GET'])
@login_required
def listar_logs():
    if not current_user.pode_auditar():
        return jsonify({'erro': 'Sem permissao'}), 403

    tipo      = request.args.get('tipo', '')
    resultado = request.args.get('resultado', '')
    login_f   = request.args.get('login', '')
    data_ini  = request.args.get('data_ini', '')
    data_fim  = request.args.get('data_fim', '')
    limite    = min(int(request.args.get('limite', 200)), 1000)

    sql    = "SELECT * FROM auditoria WHERE 1=1"
    params = []

    if tipo:
        sql += " AND tipo_acao LIKE %s"; params.append(f'%{tipo}%')
    if resultado:
        sql += " AND resultado = %s"; params.append(resultado)
    if login_f:
        sql += " AND login_usuario LIKE %s"; params.append(f'%{login_f}%')
    if data_ini:
        sql += " AND DATE(data_hora) >= %s"; params.append(data_ini)
    if data_fim:
        sql += " AND DATE(data_hora) <= %s"; params.append(data_fim)

    sql += " ORDER BY data_hora DESC LIMIT %s"
    params.append(limite)

    logs = query(sql, params)
    result = []
    for l in logs:
        d = dict(l)
        d['data_hora'] = str(d['data_hora'])
        result.append(d)
    return jsonify(result)