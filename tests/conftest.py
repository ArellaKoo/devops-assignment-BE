"""Shared fixtures for the SkipQ assessed test suites.

The offline unit suite (``tests/unit``) never opens a network socket — its
own conftest enforces that. The functional suite (``tests/functional``)
runs the real application against the guarded ``skipq_test`` database:

- the database name is checked **before** any connection is registered and
  the development database name is rejected outright;
- each functional test registers the documents it creates in
  ``fixture_records`` and teardown deletes exactly those documents, in
  dependency order, so two consecutive suite runs against the same
  database leave no state behind;
- the MongoEngine default alias is disconnected after every app, so a
  later, differently configured app in the same process can never inherit
  this suite's database.
"""

import os
import re

import pytest
from mongoengine import disconnect

from app import create_app
from app.models.cart import Cart
from app.models.order import Order

FUNCTIONAL_DB = "skipq_test"


def _functional_database() -> str:
    """The one database the functional suite may use, guarded by name."""
    candidate = os.environ.get("SKIPQ_FUNCTIONAL_DB", FUNCTIONAL_DB)
    if candidate in ("skipq_dev", "skipq") or candidate.startswith("skipq_dev"):
        pytest.fail(
            f"Refusing to run the functional suite against the development database name {candidate!r}. "
            "Point SKIPQ_FUNCTIONAL_DB at the guarded test database."
        )
    if not re.fullmatch(r"skipq_test(_[a-z0-9]+)?", candidate):
        pytest.fail(
            f"Functional fixtures require a skipq_test* database name; got {candidate!r}."
        )
    return candidate


@pytest.fixture
def functional_app():
    """The real application against the guarded functional database.

    Function-scoped and lazy: nothing in this fixture touches the database
    until the first query, and the alias is released on teardown without
    deleting any collection or data.
    """
    application = create_app(
        {
            "TESTING": True,
            "TOKEN_SECRET": "functional-test-secret-not-a-user-credential",
            "MONGODB_HOST": os.environ.get("MONGODB_HOST", "mongodb://127.0.0.1:27017"),
            "MONGODB_DB": _functional_database(),
        }
    )
    try:
        yield application
    finally:
        disconnect(alias="default")


@pytest.fixture
def fixture_records(functional_app):
    """Owns the documents a functional test creates; deletes exactly those.

    Tests append their saved documents to the matching list; teardown runs
    after the app fixture is still connected and removes orders, carts,
    menu items, users, then vendors — so re-running the suite against the
    same database is safe and leaves no residue.
    """
    registered = {
        "orders": [],
        "carts": [],
        "items": [],
        "users": [],
        "vendors": [],
    }
    yield registered
    # Routes create carts (and every paid order) as side effects the tests
    # may not register, so sweep them by reference while the owners still
    # exist, then remove the registered documents themselves.
    for user in list(registered["users"]):
        Cart.objects(diner=user).delete()
        Order.objects(diner=user).delete()
    for stall in list(registered["vendors"]):
        Order.objects(vendor=stall).delete()
    for kind in ("orders", "carts", "items", "users", "vendors"):
        for document in registered[kind]:
            document.delete()
        registered[kind].clear()
