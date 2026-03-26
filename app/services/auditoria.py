"""
Serviço de Auditoria — REGRA 3
Logs imutáveis: apenas INSERT, nunca UPDATE/DELETE.
Registra IP, user-agent e diff de campos.
"""
import json
from datetime import datetime
from flask import request
from flask_login import current_user
from app.utils.db import execute


def registrar(tipo_acao: str, descricao: str, resultado: str = 'Sucesso',
              dados_antes: dict = None, dados_depois: dict = None,
              login_override: str = None):
    """
    Registra uma ação no log de auditoria.

    Parâmetros:
        tipo_acao     : ex. 'CADASTRO_LOTE', 'EXCLUSAO_LOTE', 'LOGIN', 'BAIXA_ESTOQUE'
        descricao     : texto legível da ação
        resultado     : 'Sucesso' | 'Falha' | 'Bloqueado'
        dados_antes   : dict com estado anterior (para diffs)
        dados_depois  : dict com estado novo
        login_override: usar quando não há current_user (ex: scheduler)
    """
    try:
        # IP real mesmo atrás de proxy/nginx
        ip = (
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.headers.get('X-Real-IP')
            or request.remote_addr
            or '0.0.0.0'
        )
        user_agent = request.headers.get('User-Agent', '')[:255]
    except RuntimeError:
        # Fora de contexto de request (scheduler)
        ip = '127.0.0.1'
        user_agent = 'sistema/scheduler'

    try:
        uid   = current_user.id    if (not login_override and current_user.is_authenticated) else None
        login = current_user.login if (not login_override and current_user.is_authenticated) else (login_override or 'sistema')
    except Exception:
        uid, login = None, login_override or 'sistema'

    execute(
        """INSERT INTO auditoria
           (id_usuario, login_usuario, tipo_acao, descricao,
            ip_origem, user_agent, resultado, dados_antes, dados_depois)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            uid, login, tipo_acao, descricao,
            ip, user_agent, resultado,
            json.dumps(dados_antes,  ensure_ascii=False) if dados_antes  else None,
            json.dumps(dados_depois, ensure_ascii=False) if dados_depois else None,
        )
    )
