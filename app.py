import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify, redirect, abort, send_file
from sqlalchemy.exc import IntegrityError

from db import init_db, get_session
from models import Url, URLStats
from cache import cache_get_code, cache_set_code, increment_click_redis
from utils import encode_base62, normalize_url, qr_png_base64

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:pass@db:5432/urls")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
HOST = os.getenv("HOST", "localhost:8000")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))


def create_app():
    """Create and configure the Flask app instance.
    Returns:
        Flask: configure app
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["REDIS_URL"] = REDIS_URL
    app.config["CACHE_TTL"] = CACHE_TTL
    app.config["HOST"] = HOST

    with app.app_context():
        init_db()

    register_routes(app)
    return app