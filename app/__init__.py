"""SkipQ application factory, adapted from the StaycationX lab structure."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.config import settings_from_environment
from app.errors import register_error_handlers
from app.extensions import init_extensions


def create_app(config: dict | None = None) -> Flask:
    """Build a local API; use one active MongoEngine DB config per process."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    app = Flask(__name__)
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
    return app
