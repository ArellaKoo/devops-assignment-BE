# Clean-checkout rehearsal (Task 13, 7 October 2026)

The plan's final handover step: make temporary fresh clones of both
assignment repositories and follow only each README. This records what was
done and what actually happened, including the one genuine failure found.

## What was done

Two fresh local clones of the committed `setup/lab-adaptation` branches,
made 7 October 2026 under `/tmp/skipq-rehearsal/`:

- backend clone HEAD: `6428570` (`docs: assemble the final report, Q7(a)
  screencast preparation and disclosure`)
- frontend clone HEAD: `5bdecbb` (`docs: record the completed persona
  flows and test locations in the README`)

Everything below ran **from the clones only** — no source, venv, node
modules, `.env` or screenshots were borrowed from the working
repositories. MongoDB 8.0.32 was already running locally on
`127.0.0.1:27017` (the only shared service; both READMEs list it as a
prerequisite).

## Backend clone — commands and actual results

| Step (README command) | Result |
|---|---|
| `python3.12 -m venv .venv` + `python -m pip install -r requirements.txt -r requirements-dev.txt` | installed cleanly |
| `python -m pip check` | `No broken requirements found.` |
| `cp .env.example .env` + the README's `secrets.token_urlsafe(32)` snippet | `.env` created; keys: `MONGODB_HOST`, `MONGODB_DB`, `TEST_MONGODB_DB`, `FRONTEND_ORIGIN`, `TOKEN_SECRET` |
| `python -m pytest tests/unit -q` (no database) | **302 passed in 5.35 s** |
| `MONGODB_DB=skipq_system_test python -m db_seed.seed` | seeded; upserted 2 carts / 9 orders, "unrelated data is not deleted" |
| `MONGODB_DB=skipq_system_test python -m flask --app app:create_app run --host 127.0.0.1 --port 5001` (background) | served the guarded database on 5001 |
| `curl -i http://127.0.0.1:5001/api/nonexistent` | `HTTP/1.1 404 NOT FOUND`, `error.code = not_found` (foundation smoke check) |
| `POST /api/user/gettoken` for `diner.one@skipq.test` | `200`, token + persona returned |
| `GET /api/diner/stalls` with the token | `200`, the open Charcoal Grill stall |
| same endpoint without a token | `401` |
| `python -m pytest tests/functional -q` (run 1) | **10 passed in 3.91 s** |
| `python -m pytest tests/functional -q` (run 2, no reset between) | **10 passed in 3.73 s** |
| `python -m pytest tests/playwright -q` (run 1) | **1 passed in 12.64 s** (Chromium from the shared Playwright cache) |
| `python -m pytest tests/playwright -q` (run 2, no reset between) | **1 passed in 11.02 s** |

Evidence access in the clone: `q6-performance/` (CSV/HTML stats, JSONL
query timings, `run-metadata.md`), `docs/evidence/screenshots/`
(64 captures), `docs/evidence/browser-lifecycle/run-{1,2}.log`,
`q7-screencast/` (script, demo data, recording steps, demo script, run
log, 26 step screenshots) all present and readable.

## Frontend clone — commands and actual results

| Step (README command) | Result |
|---|---|
| Node 22.17.0 (`.nvmrc`; pinned launcher prepended to `PATH`) | `v22.17.0` |
| `npm ci` | clean install from the committed lockfile |
| `cp .env.example .env` | `REACT_APP_API_BASE_URL=http://127.0.0.1:5001`, `HOST=127.0.0.1`, `PORT=5173`, `BROWSER=none` |
| `npm run build` | `Compiled successfully.` — no ESLint warnings |
| `npm start` (background) | dev server on `http://127.0.0.1:5173`, `200` at `/` |

## Genuine failure found, and its disposition

**Finding:** starting `npm start` before `cp .env.example .env` puts the
dev server on CRA's default port **3000** instead of 5173, so the
Playwright suite (which expects 5173 per the backend README) cannot
reach it. **Root cause:** nothing in either repository — the README's
install section does say `cp .env.example .env`, and `.env.example`
carries `PORT=5173`; the rehearsal simply skipped that line on the first
attempt. **Fix:** performed the documented copy and restarted; no code
or README change was required, and no workaround was invented. This is
recorded so the marker can see the README sequence was followed
line-by-line and the one deviation was the rehearsal's own omission.

## Conclusion

From committed code alone, both repositories install, configure, seed,
run and pass: the offline unit suite (302), the guarded real-DB
functional suite twice with no reset, and the two-persona browser suite
twice with no reset. No concrete failures remained in the repositories
themselves; the single failure above was a procedure omission in the
rehearsal and is documented here rather than papered over.
