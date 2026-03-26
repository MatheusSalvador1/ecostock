from datetime import timedelta
import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail

load_dotenv()

login_manager = LoginManager()
mail = Mail()


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-insegura')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', 30)))
    app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    app.config['DB_PORT'] = int(os.getenv('DB_PORT', 3306))
    app.config['DB_USER'] = os.getenv('DB_USER', 'root')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', '')
    app.config['DB_NAME'] = os.getenv('DB_NAME', 'ecostock_db')
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL')
    app.config['ADMIN_INITIAL_LOGIN'] = os.getenv('ADMIN_INITIAL_LOGIN', 'admin')
    app.config['ADMIN_INITIAL_PASSWORD'] = os.getenv('ADMIN_INITIAL_PASSWORD', 'Admin@123')
    app.config['ADMIN_INITIAL_EMAIL'] = os.getenv('ADMIN_INITIAL_EMAIL', 'admin@local')
    app.config['ADMIN_FORCE_RESET_ON_START'] = os.getenv('ADMIN_FORCE_RESET_ON_START', 'False').lower() in {'1', 'true', 'yes', 'on'}

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    mail.init_app(app)

    from app.api.auth import auth_bp
    from app.api.inventory import inventory_bp
    from app.api.users import users_bp
    from app.api.audit import audit_bp
    from app.api.dashboard import dashboard_bp
    from app.api.notify import notify_bp
    from app.services.scheduler import iniciar_scheduler
    from app.services.bootstrap import ensure_admin_user
    from app.utils.db import close_db

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(notify_bp)

    app.teardown_appcontext(close_db)

    with app.app_context():
        ensure_admin_user()
        iniciar_scheduler(app)

    return app
