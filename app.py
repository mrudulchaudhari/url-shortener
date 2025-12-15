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


def register_routes(app):
    """Register HTTP route handlers on the Flask app.

    Args:
        app (Flask): Flask app instance to register routes on.
    """

    @app.route("/shorten", methods=["POST"])
    def shorten():
        """
        Endpoint: shorten a provided URL.
        Request JSON: {"url":"<original>", "custom":"<optional>", "expires_at":"<ISO8601 optional>"}
        Returns JSON with code, short_url, qr_base64 on success.
        """
        data = request.get_json(force=True, silent=True) or {}
        if "url" not in data:
            return jsonify({"error": "url required"}), 400

        try:
            norm = normalize_url(data["url"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        custom = data.get("custom")
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except Exception:
                return jsonify({"error": "invalid expires_at format"}), 400

        session = get_session()

        try:
            if custom:
                if not custom.isalnum() or len(custom) > 32:
                    return jsonify({"error": "custom alias invalid"}), 400

                u = Url(code=custom, original_url=norm, expires_at=expires_at)
                session.add(u)
                session.commit()
                code = custom

            else:
                u = Url(code="tmp", original_url=norm, expires_at=expires_at)
                session.add(u)
                session.flush()
                code = encode_base62(u.id)
                u.code = code
                session.commit()

            payload = {
                "url_id": u.id,
                "original_url": u.original_url,
                "is_active": u.is_active,
                "expires_at": u.expires_at.isoformat() if u.expires_at else None
            }

            cache_set_code(code, payload, ttl=app.config["CACHE_TTL"])

            short_url = f"https://{app.config["HOST"]}/{code}"
            qr_b64 = qr_png_base64(code)

            return jsonify({"code":code, "short_url":short_url, "qr_base64":qr_b64}), 201

        except IntegrityError:
            session.rollback()
            return jsonify({"error": "alias_exists"}), 409

        finally:
            session.close()


        @app.route("/<code>", methods=["GET"])
        def go(code):
            """Endpoint: resolve a short code and redirect to original URL.

            Fast path: try redis cache. If cached and active, increment redis click buffer and redirect.
            Cold path: fetch DB, set cahce, increment click buffer, then redirect.
            """

        cached = cache_get_code(code)
        if cached:
            if cached.get("expires_at"):
                exp = datetime.fromisoformat(cached["expires_at"])
                if exp <= datetime.now(timezone.utc):
                    return ("Expired", 410)

            increment_click_redis(cached["url_id"])
            return redirect(cached["original_url"], code = 302)

        # if cache miss
        session = get_session()
        u = session.query(Url).filter_by(code=code, is_active=True).first()
        if not u:
            session.close()
            abort(404)
        if u.expires_at and u.expires_at <= datetime.now(timezone.utc):
            session.close()
            return ("Expired", 410)

        payload = {
            "url_id": u.id,
            "original_url": u.original_url,
            "is_active": u.is_active,
            "expires_at": u.expires_at.isoformat() if u.expires_at else None
        }
        cache_set_code(code, payload, ttl=app.config["CACHE_TTL"])
        increment_click_redis(u.id)
        session.close()
        return redirect(u.original_url, code = 302)


