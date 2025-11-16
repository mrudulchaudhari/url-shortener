from flask import Flask
from .config import Config
from .db import init_db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)

    from .api import bp as api_bp
    app.register_blueprint(api_bp)

    return app