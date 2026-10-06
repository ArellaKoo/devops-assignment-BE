# SkipQ backend

Backend repository: [devops-assignment-BE](https://github.com/ArellaKoo/devops-assignment-BE). Frontend: [devops-assignment-FE](https://github.com/ArellaKoo/devops-assignment-FE).

This is the Flask/MongoEngine backend for the ICT381 SkipQ TMA, adapted from StaycationX. It implements the SkipQ domain documents (users, stalls, menu items, carts, paid orders with embedded simulated payment), the repeatable demo seed, and — as the build continues — persona API routes and the assessed test suites. Read the [complete plan](ASSIGNMENT_PLAN.md), [workspace setup guide](docs/assessment/setup-guide.md), [verified startup checks](docs/assessment/foundation-verification.md) and [actual lab reuse](docs/report/provenance.md).

For Qwen Code, [QWEN.md](QWEN.md) supplies persistent project instructions; [the readiness record](docs/assessment/qwen-readiness.md) lists installed skills, verified helper tools and how to start the implementation handoff.

## Prerequisites and install

- Python 3.12 (setup verified with 3.12.15).
- Local MongoDB Community 8.0, bound to `127.0.0.1:27017`.
- Separate frontend on `http://127.0.0.1:5173`.

Inside this repository:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

Set a local random TOKEN_SECRET in the ignored `.env`. This command replaces only the example value without printing the generated secret:

```bash
python - <<'PY'
from pathlib import Path
import secrets
path = Path('.env')
text = path.read_text()
path.write_text(text.replace('replace-with-a-local-random-secret', secrets.token_urlsafe(32)))
PY
```

Database host/name come from `.env`. MongoEngine's default alias has one active database configuration per process. Run development and assessed DB tests in separate processes. Fixtures must use test-only names and call `mongoengine.disconnect(alias="default")` on teardown before another app changes the database; the factory never silently disconnects a running app. The offline foundation fixture demonstrates that lifecycle without deleting data. Never use the development database for test cleanup. `.env`, virtual environments and database data are ignored.

## Run

Start your local MongoDB server, then:

```bash
source .venv/bin/activate
python -m flask --app app:create_app run --host 127.0.0.1 --port 5001
```

The app factory runs and unsupported API paths return JSON 404. No user-facing health/demo endpoint is added. Verify the current startup with:

```bash
curl -i http://127.0.0.1:5001/api/nonexistent
```

Expected: HTTP 404 with `error.code` equal to `not_found`. This is a foundation smoke check, not the required Q4 test suite.

## Seed data and demo accounts

After installing and starting your local MongoDB, seed the configured database (default `skipq_dev`) with the repeatable demo data:

```bash
source .venv/bin/activate
python -m db_seed.seed
```

The script upserts deterministic demo records by their natural keys and
refreshes the time-relative fixtures; re-running it never deletes unrelated
data. The coverage argument (which records put the application in the state
each acceptance criterion describes, and what a marker must do for states
seeding alone cannot produce) is in [docs/report/seed-coverage.md](docs/report/seed-coverage.md).

All seeded accounts share the local demo password `SkipQDemo2026!`
(demonstration accounts only, never personal credentials):

| Role | Email | Stall |
|---|---|---|
| Diner | `diner.one@skipq.test` | — (owns current and past orders) |
| Diner | `diner.two@skipq.test` | — (foreign orders to expose ownership leaks) |
| Diner | `diner.empty@skipq.test` | — (no orders; empty state) |
| Vendor | `vendor.one@skipq.test` | Charcoal Grill (open) |
| Vendor | `vendor.one.backup@skipq.test` | Charcoal Grill (shared-stall account) |
| Vendor | `vendor.two@skipq.test` | Noodle Bar (closed) |

To point the seed (or the app) at a different database, set `MONGODB_DB`
in the ignored `.env`. The seed targets the configured database only.

## Foundation checks

```bash
python -m pip check
python -m pytest -q
```

The four startup regression cases preserve HTTP `Allow`/`Retry-After` headers in JSON errors and release the MongoEngine alias between sequential test apps; the validation, cart and sign-in/lockout/token/role suites add the domain allow/refuse rules. All of them run without database access. The required real-database lifecycle and browser/load suites remain in the build plan.

## Sign in and use a token

With the API running and the database seeded, `POST /api/user/gettoken` exchanges a seeded account's email and password for a signed Bearer token that is valid for 3,600 seconds:

```bash
curl -s -X POST http://127.0.0.1:5001/api/user/gettoken \
  -H 'Content-Type: application/json' \
  -d '{"email":"diner.one@skipq.test","password":"SkipQDemo2026!"}'
```

The response is `{"token": "...", "persona": {...}}`; protected endpoints (the diner and vendor routes, as they land) expect `Authorization: Bearer <token>`. Missing/invalid/expired tokens are refused `401`, a wrong persona is refused `403`, and five failed sign-ins lock an account for 15 minutes with `429`. The token key is your local `TOKEN_SECRET`.

## Test suites

- Unit (offline, no MongoDB needed): `python -m pytest tests/unit -q` — validation, cart, sign-in/lockout/token/role rules, the order-lifecycle guard, and the checkout/order routes; the shared fixture refuses any network socket so the suite fails if it ever touches a database. This is also the default `python -m pytest -q` target (`pytest.ini`).
- Functional (real MongoDB, guarded `skipq_test` database): `python -m pytest tests/functional -q` — the full order lifecycle, cross-account 403s, stale-checkout refusals, the sequential replay/conflict pair, the two-thread same-key checkout against the real unique index, and snapshot persistence. Fixtures refuse the development database name, delete exactly their own records (including route-created carts and orders), and release the MongoEngine alias after every app, so the suite can run twice against the same database with no manual reset.
- Browser system test (Playwright against the real running app, guarded `skipq_system_test` database): `python -m pytest tests/playwright -q` — `tests/playwright/test_order_lifecycle.py` signs the diner and the vendor in through the UI in two isolated browser contexts, then walks one fresh order through the whole lifecycle: the diner clears any leftover cart lines, adds one item and checks out with the checkout key the screen mints; the vendor accepts, readies and collects that captured queue number; both screens' displayed state is asserted at every stage with `expect` condition waits (no sleeps, no token injection, no mocked API). Prerequisites: Chromium installed (`python -m playwright install chromium`), MongoDB running, the guarded database seeded (`MONGODB_DB=skipq_system_test python -m db_seed.seed`), the API running against **that** database in its own process (`MONGODB_DB=skipq_system_test python -m flask --app app:create_app run --host 127.0.0.1 --port 5001`), and the frontend on `http://127.0.0.1:5173`. The fixtures refuse every other database name, verify both servers and the seed state before the first persona step, delete only the run's order and the test diner's cart lines, and release the MongoEngine alias on teardown — so the suite runs twice against the same seeded database with no manual reset between runs. Per-state screenshots land in `docs/evidence/screenshots/` as `task11-*`.
- Load suite: Locust under `q6-performance/` (Task 12 of the plan).

## API routes so far

With the token from above, the diner and vendor persona routes are available:

| Persona | Endpoint |
|---|---|
| Diner | `GET /api/diner/stalls`, `GET /api/diner/stalls/<id>/menu`, `GET /api/diner/cart`, `POST /api/diner/cart/items`, `PATCH`/`DELETE /api/diner/cart/items/<id>`, `POST /api/diner/orders`, `GET /api/diner/orders?view=all\|current\|history`, `GET /api/diner/orders/<id>` |
| Vendor | `GET`/`PATCH /api/vendor/stall`, `GET`/`POST /api/vendor/menu`, `PATCH`/`DELETE /api/vendor/menu/<id>`, `GET /api/vendor/orders`, `GET /api/vendor/orders/<id>`, `PATCH /api/vendor/orders/<id>/status` |

All of them require the Bearer token, refuse the wrong persona with 403, look up ids through the models (404 when missing or malformed), and scope every mutation to the actor's own records. Money is integer cents; the cart response carries the server-computed total and a checkout freshness fingerprint. Checkout stores one paid order per unique `(diner, checkout_key)` pair — a matching retry returns the stored order (200), a conflicting reuse is refused (409) — and the vendor's status changes go through the model's guarded lifecycle (terminal orders and the 30-minute no-show boundary included); the stall's paid queue stays processable while the stall is closed.

## Remaining build

The assessed unit, functional and browser suites are in place; the diner (Tasks 8 and 10) and vendor (Task 9) screens are complete. Remaining in the [plan](docs/superpowers/plans/2026-10-06-skipq-tma.md): the Locust load suite with measured `q6-performance/` artifacts (Task 12) and the report/screencast evidence and final handover (Task 13). Add the measured q6 artifacts and narrated q7 recording link here when they exist.

## Lab adaptation

Factory/extension structure comes from the declared lab source. The legacy Flask-MongoEngine adapter is replaced with direct MongoEngine, configuration is externalized, CORS is limited to the configured frontend, and hotel/domain/HTML/session/Selenium/deployment code is excluded. See [provenance](docs/report/provenance.md) and [AI disclosure](docs/assessment/ai-prompts.md).
