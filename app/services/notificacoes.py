"""
Serviço de Notificações por Email (Gmail SMTP)
Envia alertas automáticos de validade em 3 níveis.
"""
from flask_mail import Message
from flask import current_app, render_template_string
from app import mail
from app.utils.db import query, execute


# ── Templates de Email ─────────────────────────────────────────────────────────

EMAIL_ALERTA_HTML = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }
    .card { background: white; border-radius: 12px; padding: 30px; max-width: 600px; margin: 0 auto; }
    .header { background: {{ cor }}; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    .header h1 { margin: 0; font-size: 1.4rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th { background: #f8f9fa; padding: 10px; text-align: left; font-size: 0.85rem; color: #555; }
    td { padding: 10px; border-bottom: 1px solid #eee; font-size: 0.9rem; }
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; background: {{ cor }}20; color: {{ cor }}; }
    .footer { text-align: center; margin-top: 20px; font-size: 0.8rem; color: #999; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>{{ icone }} EcoStock — Alerta de Validade</h1>
      <p style="margin:5px 0 0">{{ subtitulo }}</p>
    </div>
    <p>Olá! Os seguintes lotes requerem atenção imediata:</p>
    <table>
      <thead>
        <tr><th>Produto</th><th>Lote</th><th>Qtd</th><th>Validade</th><th>Status</th></tr>
      </thead>
      <tbody>
        {% for item in itens %}
        <tr>
          <td><strong>{{ item.nome }}</strong></td>
          <td><code>{{ item.codigo_lote }}</code></td>
          <td>{{ item.quantidade_atual }}</td>
          <td>{{ item.data_validade.strftime('%d/%m/%Y') }}</td>
          <td><span class="badge">{{ item.status }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <div class="footer">
      EcoStock · Sistema Inteligente de Gestão de Validade<br>
      Este é um e-mail automático, não responda.
    </div>
  </div>
</body>
</html>
"""

NIVEIS = {
    'VENCIDO':   {'dias': 0,  'cor': '#d32f2f', 'icone': '🚨', 'subtitulo': 'Produtos VENCIDOS no estoque!'},
    'CRITICO_7': {'dias': 7,  'cor': '#e64a19', 'icone': '⚠️', 'subtitulo': 'Produtos vencem em até 7 dias'},
    'AVISO_15':  {'dias': 15, 'cor': '#f57c00', 'icone': '🔔', 'subtitulo': 'Produtos vencem em até 15 dias'},
    'AVISO_30':  {'dias': 30, 'cor': '#388e3c', 'icone': '📋', 'subtitulo': 'Aviso preventivo — 30 dias'},
}


def verificar_e_enviar_alertas(app):
    """Chamado pelo scheduler. Verifica lotes e envia emails se necessário."""
    with app.app_context():
        admin_email = current_app.config.get('ADMIN_EMAIL') or current_app.config.get('MAIL_USERNAME')
        if not admin_email:
            return

        for tipo, cfg in NIVEIS.items():
            if cfg['dias'] == 0:
                sql = """
                    SELECT l.*, p.nome FROM lotes l
                    JOIN produtos p ON l.id_produto = p.id
                    WHERE l.data_validade < CURDATE() AND l.quantidade_atual > 0
                """
            else:
                sql = """
                    SELECT l.*, p.nome FROM lotes l
                    JOIN produtos p ON l.id_produto = p.id
                    WHERE l.data_validade BETWEEN CURDATE()
                          AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
                    AND l.quantidade_atual > 0
                """

            params = () if cfg['dias'] == 0 else (cfg['dias'],)
            lotes = query(sql, params)

            # Filtra apenas lotes que ainda não receberam este tipo de notificação
            lotes_novos = []
            for lote in lotes:
                ja_enviado = query(
                    "SELECT id FROM notificacoes_enviadas WHERE id_lote=%s AND tipo=%s",
                    (lote['id'], tipo), fetchone=True
                )
                if not ja_enviado:
                    lotes_novos.append(lote)

            if not lotes_novos:
                continue

            # Adiciona campo status para o template
            for l in lotes_novos:
                l['status'] = tipo.replace('_', ' ')

            # Renderiza e envia email
            corpo_html = render_template_string(
                EMAIL_ALERTA_HTML,
                itens=lotes_novos,
                cor=cfg['cor'],
                icone=cfg['icone'],
                subtitulo=cfg['subtitulo']
            )

            msg = Message(
                subject=f"{cfg['icone']} EcoStock — {cfg['subtitulo']}",
                recipients=[admin_email],
                html=corpo_html
            )

            try:
                mail.send(msg)
                # Marca como enviado para não repetir
                for lote in lotes_novos:
                    execute(
                        "INSERT IGNORE INTO notificacoes_enviadas (id_lote, tipo) VALUES (%s, %s)",
                        (lote['id'], tipo)
                    )
            except Exception as e:
                current_app.logger.error(f"[EMAIL] Erro ao enviar alerta {tipo}: {e}")


def enviar_email_boas_vindas(email_destino: str, login: str):
    """Enviado ao admin quando um novo usuário se cadastra."""
    if not email_destino:
        return
    try:
        msg = Message(
            subject="🌱 EcoStock — Novo usuário aguardando liberação",
            recipients=[email_destino],
            html=f"""
            <div style="font-family:sans-serif;padding:20px;background:#f4f4f4">
              <div style="background:white;padding:25px;border-radius:10px;max-width:500px;margin:0 auto">
                <h2 style="color:#2e7d32">Novo cadastro no EcoStock</h2>
                <p>O usuário <strong>{login}</strong> acabou de se registrar e está aguardando liberação.</p>
                <p>Acesse o painel de <strong>Gestão de Usuários</strong> para ativar as permissões.</p>
                <hr style="border:none;border-top:1px solid #eee">
                <small style="color:#999">EcoStock · Notificação automática</small>
              </div>
            </div>"""
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"[EMAIL] Boas-vindas não enviado: {e}")
