"""Browser system-suite fixtures (Q6(a)).

This suite drives the real application end to end: a separately running
Flask API on ``127.0.0.1:5001`` serving the guarded ``skipq_system_test``
database, and the React app on ``127.0.0.1:5173``. Both personas sign in
through the UI in isolated browser contexts; the in-process Flask test
client is never used, and no token is injected into the browser.

- the database name is checked **before** any connection is registered;
  the development (``skipq_dev*``) and functional (``skipq_test*``)
  database names are rejected outright;
- the session fixture verifies both servers are up and that the database
  holds the seed state before any persona step runs;
- teardown deletes only this run's records — orders whose queue number is
  a 32-hex run id (seed orders are ``Q-seed-``), plus the test diner's
  cart lines — so two consecutive runs against the same seeded database
  need no manual reset between them;
- the MongoEngine default alias is disconnected on teardown, so no later
  app in this process can inherit this suite's database.
"""

import json
import os
import re
import urllib.error
import urllib.request

import pytest
from mongoengine import connect, disconnect

from app.models.cart import Cart
from app.models.order import Order
from app.models.user import User

SYSTEM_DB = "skipq_system_test"
API_BASE = "http://127.0.0.1:5001"
WEB_BASE = "http://127.0.0.1:5173"
RUN_QUEUE_RE = r"^Q-[0-9a-f]{32}$"
SEED_QUEUE_RE = r"^Q-seed-"
SEED_ORDER_COUNT = 9


def _system_database() -> str:
    """The one database the browser suite may use, guarded by name."""
    candidate = os.environ.get("SKIPQ_SYSTEM_DB", SYSTEM_DB)
    if (
        candidate in ("skipq_dev", "skipq")
        or candidate.startswith("skipq_dev")
        or candidate in ("skipq_test",)
        or candidate.startswith("skipq_test")
    ):
        pytest.fail(
            f"Refusing to run the browser suite against the development or functional "
            f"database name {candidate!r}. Point SKIPQ_SYSTEM_DB at the guarded "
            f"skipq_system_test database."
        )
    if not re.fullmatch(r"skipq_system_test(_[a-z0-9]+)?", candidate):
        pytest.fail(
            f"Browser fixtures require a skipq_system_test* database name; got {candidate!r}."
        )
    return candidate


def _server_problems() -> list:
    """Actionable problems with the two required servers, empty when both are up."""
    problems = []
    try:
        with urllib.request.urlopen(API_BASE + "/api/nonexistent", timeout=5) as resp:
            problems.append(f"the API at {API_BASE} answered {resp.status} on an unknown path")
    except urllib.error.HTTPError as err:
        try:
            body = json.load(err)
            ok = err.code == 404 and body.get("error", {}).get("code") == "not_found"
        except (ValueError, AttributeError):
            ok = False
        if not ok:
            problems.append(f"the API at {API_BASE} is not serving the SkipQ JSON error envelope")
    except Exception as exc:  # noqa: BLE001 - reported as an actionable message
        problems.append(f"the API at {API_BASE} is unreachable ({exc})")
    try:
        with urllib.request.urlopen(WEB_BASE + "/", timeout=5) as resp:
            body = resp.read().decode("utf-8", "replace")
            if "<div id=\"root\">" not in body:
                problems.append(f"the app at {WEB_BASE} is not serving the React build")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"the app at {WEB_BASE} is unreachable ({exc})")
    return problems


_STARTUP_HELP = (
    "Start them: MongoDB on 127.0.0.1:27017, then seed the guarded database "
    "(`MONGODB_DB=skipq_system_test python -m db_seed.seed`), run the API against "
    "that database in its own process "
    "(`MONGODB_DB=skipq_system_test python -m flask --app app:create_app run "
    "--host 127.0.0.1 --port 5001`), and the frontend on http://127.0.0.1:5173 "
    "(see the backend README, Test suites)."
)


@pytest.fixture(scope="session")
def system_database():
    """The guarded database the running API serves; verified, then cleaned.

    Connects the MongoEngine default alias to the guarded database, checks
    the two servers and the seed state, yields the database name, then
    deletes exactly this run's records and releases the alias.
    """
    db_name = _system_database()
    host = os.environ.get("MONGODB_HOST", "mongodb://127.0.0.1:27017")

    problems = _server_problems()
    if problems:
        pytest.fail("Browser suite prerequisites failed: " + "; ".join(problems) + ". " + _STARTUP_HELP)

    connect(db=db_name, host=host)
    try:
        assert User.objects(email="diner.one@skipq.test").count() == 1, (
            "seed user diner.one is missing — seed the database first"
        )
        assert User.objects(email="vendor.one@skipq.test").count() == 1, (
            "seed user vendor.one is missing — seed the database first"
        )
        assert Order.objects(queue_number__regex=SEED_QUEUE_RE).count() == SEED_ORDER_COUNT, (
            "seed orders are missing — seed the database first"
        )
        yield db_name
    finally:
        # Run-owned records only: seed queue numbers never match the 32-hex
        # run-id pattern. The cart is recreated lazily on the next run's first
        # cart request, so removing it here is safe.
        Order.objects(queue_number__regex=RUN_QUEUE_RE).delete()
        diner = User.objects(email="diner.one@skipq.test").first()
        if diner is not None:
            Cart.objects(diner=diner).delete()
        disconnect(alias="default")
