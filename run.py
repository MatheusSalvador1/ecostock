import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('APP_HOST', '127.0.0.1')
    port = int(os.getenv('APP_PORT', '8000'))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
    app.run(debug=debug, host=host, port=port)
