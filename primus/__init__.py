"""Primus application factory."""

from __future__ import annotations

import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from .config import CONFIGS, validate_production
from .extensions import csrf, db, login_manager, migrate
from .models import User


def create_app(config_name: str | None = None, config_overrides: dict | None = None) -> Flask:
    """Create and configure a Flask application instance."""

    config_name = config_name or os.environ.get("PRIMUS_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIGS.get(config_name, CONFIGS["development"]))
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.instance_path, exist_ok=True)

    _configure_logging(app)
    _init_extensions(app)
    _register_login(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_cli(app)
    _register_shell_context(app)

    if config_name == "production":
        validate_production(app)
    app.logger.info("Primus started in %s mode", config_name)
    return app


def _configure_logging(app: Flask) -> None:
    if app.config.get("DEBUG") and not app.config.get("TESTING"):
        logging.basicConfig(level=logging.INFO)


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)


def _register_login(app: Flask) -> None:
    @login_manager.user_loader
    def load_user(user_id: str):  # pragma: no cover - trivial
        if not user_id or not str(user_id).isdigit():
            return None
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if _wants_json():
            return jsonify({"error": "authentication required"}), 401
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for("auth.login", next=request.full_path))


def _register_blueprints(app: Flask) -> None:
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp

    # Token-authenticated JSON API: CSRF does not apply to bearer tokens.
    csrf.exempt(api_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")


def _register_error_handlers(app: Flask) -> None:
    def _render_error(code: int, message: str, description: str):
        if _wants_json():
            return jsonify({"error": message}), code
        return render_template(
            "error.html", code=code, message=message, description=description
        ), code

    @app.errorhandler(400)
    def bad_request(error):
        return _render_error(400, "bad request", "The request could not be understood.")

    @app.errorhandler(404)
    def not_found(error):
        return _render_error(404, "not found", "That page or resource does not exist.")

    @app.errorhandler(405)
    def method_not_allowed(error):
        return _render_error(405, "method not allowed", "That method is not supported here.")

    @app.errorhandler(500)
    def internal_error(error):  # pragma: no cover - exercised manually
        db.session.rollback()
        app.logger.exception("Unhandled error")
        return _render_error(500, "internal server error", "Something went wrong.")


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def set_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; connect-src 'self'",
        )
        return response


def _register_cli(app: Flask) -> None:
    from .cli import register_cli

    register_cli(app)


def _register_shell_context(app: Flask) -> None:
    @app.shell_context_processor
    def shell_context():  # pragma: no cover - developer convenience
        from . import models

        return {
            "db": db,
            "User": models.User,
            "Monitor": models.Monitor,
            "Check": models.Check,
            "Incident": models.Incident,
        }


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    return request.accept_mimetypes.best == "application/json"
