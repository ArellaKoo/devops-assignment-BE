"""Separate extension setup, adapted from StaycationX's extensions module."""

from flask_cors import CORS
from mongoengine import connect

cors = CORS()


def init_extensions(app) -> None:
    # The default alias belongs to one database configuration per process.
    # Test fixtures release it explicitly after their app has finished.
    app.extensions["mongoengine_connection"] = connect(
        db=app.config["MONGODB_DB"],
        host=app.config["MONGODB_HOST"],
        connect=False,
        uuidRepresentation="standard",
    )
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}},
    )
