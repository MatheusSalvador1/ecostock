"""Blueprint: Notificações."""
from flask import Blueprint, jsonify, current_app
from flask_login import current_user, login_required

from app.services.auditoria import registrar

notify_bp = Blueprint('notify', __name__)


@notify_bp.route('/api/v1/notificar/testar', methods=['POST'])
@notify_bp.route('/notificar/testar', methods=['POST'])
@login_required
def testar_notificacao():
    if not current_user.is_admin():
        return jsonify({'erro': 'Apenas administradores'}), 403

    from app.services.notificacoes import verificar_e_enviar_alertas

    verificar_e_enviar_alertas(current_app._get_current_object())
    registrar('NOTIFICACAO_MANUAL', 'Admin disparou verificação manual de alertas')
    return jsonify({'sucesso': True, 'msg': 'Verificação executada. Veja os logs.'})
