"""SkipQ application factory, adapted from the StaycationX lab structure."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.config import settings_from_environment
from app.controllers.auth import auth_bp
from app.controllers.diner import diner_bp
from app.controllers.order import diner_orders_bp, vendor_orders_bp
from app.controllers.vendor import vendor_bp
from app.errors import register_error_handlers
from app.extensions import init_extensions
from app.query_timing import install as install_query_timing


def create_app(config: dict | None = None) -> Flask:
    """Build a local API; use one active MongoEngine DB config per process."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    static_folder = Path(__file__).resolve().parent.parent / "static"
    app = Flask(
        __name__,
        static_folder=str(static_folder) if static_folder.is_dir() else None,
        static_url_path="/static",
    )
    app.config.from_mapping(settings_from_environment())
    if config:
        app.config.update(config)

    if not app.config.get("TOKEN_SECRET") or app.config["TOKEN_SECRET"] == (
        "replace-with-a-local-random-secret"
    ):
        raise RuntimeError("Set TOKEN_SECRET in your local .env before starting SkipQ.")

    app.config["SECRET_KEY"] = app.config["TOKEN_SECRET"]
    init_extensions(app)
    install_query_timing(app)
    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(diner_bp)
    app.register_blueprint(diner_orders_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(vendor_orders_bp)
    return app
