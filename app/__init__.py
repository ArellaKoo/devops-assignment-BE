"""SkipQ application factory, adapted from the StaycationX lab structure."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.config import settings_from_environment
from app.controllers.auth import auth_bp
from app.errors import register_error_handlers
from app.extensions import init_extensions


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
    register_error_handlers(app)
    app.register_blueprint(auth_bp)
    return app
