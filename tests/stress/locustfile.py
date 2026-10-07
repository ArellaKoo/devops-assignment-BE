"""Q6(b) local load measurement: the diner menu endpoint.

Endpoint choice (argued in docs/report/q6-load-verdict.md): the UI polls
``GET /api/diner/stalls/<id>/menu`` every 3 s while the diner views a stall
menu — the most frequent diner request by far; order placement and checkout
are once-per-order events and are deliberately not loaded here.

Two user classes:

- ``MenuLoadUser`` — signs in **once per user** in ``on_start`` (those
  requests surface as their own stats line, never mixed into the measured
  task), then polls the seeded open stall's menu at the UI's ~3 s cadence,
  checking the payload (200, the stall's name, an ``items`` list).
- ``LoginProbe`` — a dedicated authentication observation (repeated
  sign-ins), run separately with ``--class LoginProbe`` so auth is reported
  apart from the measured menu load.

The stall id is resolved from the live seed at process start (never
hardcoded). The load targets the API the README documents at
``127.0.0.1:5001``; override with ``SKIPQ_LOAD_HOST``.
"""

import os

import requests
from locust import HttpUser, between, task

API = os.environ.get("SKIPQ_LOAD_HOST", "http://127.0.0.1:5001")
EMAIL = os.environ.get("SKIPQ_LOAD_EMAIL", "diner.one@skipq.test")
PASSWORD = os.environ.get("SKIPQ_LOAD_PASSWORD", "SkipQDemo2026!")
STALL_NAME = os.environ.get("SKIPQ_LOAD_STALL", "Charcoal Grill")


def _resolve_menu_path() -> str:
    login = requests.post(
        f"{API}/api/user/gettoken", json={"email": EMAIL, "password": PASSWORD}, timeout=10
    )
    if login.status_code != 200:
        raise SystemExit(f"Locust setup: sign-in refused with {login.status_code}: {login.text[:200]}")
    token = login.json()["token"]
    stalls = requests.get(
        f"{API}/api/diner/stalls", headers={"Authorization": f"Bearer {token}"}, timeout=10
    )
    if stalls.status_code != 200:
        raise SystemExit(f"Locust setup: stall list refused with {stalls.status_code}")
    stall = next((entry for entry in stalls.json()["items"] if entry["name"] == STALL_NAME), None)
    if stall is None:
        raise SystemExit(
            f"Locust setup: open stall {STALL_NAME!r} not found — is the seeded database serving this API?"
        )
    return f"/api/diner/stalls/{stall['id']}/menu"


MENU_PATH = _resolve_menu_path()
MENU_LABEL = f"GET {MENU_PATH}"


def _sign_in(client, name: str) -> str | None:
    """Sign in through the API; record the refusal and return None instead of a token."""
    with client.post(
        "/api/user/gettoken",
        json={"email": EMAIL, "password": PASSWORD},
        name=name,
        catch_response=True,
    ) as resp:
        if resp.status_code != 200:
            resp.failure(f"sign-in refused: {resp.status_code}")
            return None
        body = resp.json()
        if not body.get("token") or body.get("persona", {}).get("role") != "diner":
            resp.failure("sign-in response missing the token or the diner persona")
            return None
        resp.success()
        return body["token"]


class MenuLoadUser(HttpUser):
    """One simulated diner: one sign-in, then the 3 s menu poll."""

    host = API
    wait_time = between(2.9, 3.1)  # the UI's 3-second menu poll cadence

    def on_start(self):
        self.token = _sign_in(self.client, "setup: POST /api/user/gettoken (one sign-in per user)")

    @task
    def poll_menu(self):
        with self.client.get(
            MENU_PATH,
            headers={"Authorization": f"Bearer {self.token}"},
            name=MENU_LABEL,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"expected 200, got {resp.status_code}")
                return
            try:
                data = resp.json()
            except ValueError:
                resp.failure("response was not JSON")
                return
            if data.get("stall", {}).get("name") != STALL_NAME or not isinstance(data.get("items"), list):
                resp.failure("menu payload missing the stall name or the items list")
                return
            resp.success()


class LoginProbe(HttpUser):
    """Authentication-only observation (reported separately from the menu load)."""

    host = API
    wait_time = between(5, 10)

    @task
    def sign_in(self):
        _sign_in(self.client, "POST /api/user/gettoken (auth probe)")
