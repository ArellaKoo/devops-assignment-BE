"""Offline factory fixtures; never initialize or clean the development DB."""

import re
import socket

import pytest
from mongoengine import disconnect

from app import create_app


@pytest.fixture
def app(request, monkeypatch):
    database = getattr(request, "param", "skipq_unit_default")
    if not re.fullmatch(r"skipq_unit_[a-z0-9_]+", database):
        raise ValueError("Foundation fixtures require a skipq_unit_* database name.")

    def refuse_network(*args, **kwargs):
        raise AssertionError("An offline unit test attempted a network connection.")

    monkeypatch.setattr(socket.socket, "connect", refuse_network)
    application = create_app(
        {
            "TESTING": True,
            "TOKEN_SECRET": "unit-test-secret-not-a-user-credential",
            "MONGODB_HOST": "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100",
            "MONGODB_DB": database,
        }
    )
    try:
        yield application
    finally:
        # Release this fixture's alias, without deleting collections or data.
        # Never disconnect another running app to force configuration changes.
        disconnect(alias="default")
