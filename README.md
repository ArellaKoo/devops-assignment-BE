# SkipQ backend

Backend repository: [devops-assignment-BE](https://github.com/ArellaKoo/devops-assignment-BE). Frontend: [devops-assignment-FE](https://github.com/ArellaKoo/devops-assignment-FE).

This is the Flask/MongoEngine startup foundation for the ICT381 SkipQ TMA, adapted from StaycationX. **Domain models, seeded accounts, persona endpoints and assessed tests are the next build tasks; they are not implemented in this foundation.** Read the [complete plan](ASSIGNMENT_PLAN.md), [workspace setup guide](docs/assessment/setup-guide.md), [verified startup checks](docs/assessment/foundation-verification.md) and [actual lab reuse](docs/report/provenance.md).

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

## Foundation checks

```bash
python -m pip check
python -m pytest -q
```

The four startup regression cases preserve HTTP `Allow`/`Retry-After` headers in JSON errors and release the MongoEngine alias between sequential test apps. They run without database access. They do not implement the required domain allow/refuse or lifecycle tests; those remain in the build plan.

## Next assessed deliverables

Implement `app/models/`, `app/controllers/`, `db_seed/`, and the unit/functional/Playwright/Locust suites following the plan. As they are completed, replace this section with verified seed credentials, token/protected-endpoint examples and actual test commands. Add the measured q6 artifacts and narrated q7 recording link. No seed or token command is claimed to work yet.

## Lab adaptation

Factory/extension structure comes from the declared lab source. The legacy Flask-MongoEngine adapter is replaced with direct MongoEngine, configuration is externalized, CORS is limited to the configured frontend, and hotel/domain/HTML/session/Selenium/deployment code is excluded. See [provenance](docs/report/provenance.md) and [AI disclosure](docs/assessment/ai-prompts.md).
