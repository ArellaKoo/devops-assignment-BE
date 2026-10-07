# Q6(b) local load measurement — run metadata (7 Oct 2026)

All three runs target the same seeded database `skipq_system_test` (no reset
between runs), served by a single local Flask process with opt-in query
instrumentation enabled (`SKIPQ_QUERY_TIMING=1`). Locust runs on the same
machine against `127.0.0.1`.

## Machine

- MacBook Air, model `Mac15,13`, Apple M3 (`sysctl hw.model`,
  `machdep.cpu.brand_string`), 8 physical / 8 logical cores, 8 GiB RAM.
- macOS 26.6.2, build 25G83 (`sw_vers`).

## Stack (versions as imported by the test/measure processes)

- Python 3.12.15 · Flask 3.1.3 · MongoEngine 0.29.3 · PyMongo 4.18.2 ·
  Locust 2.46.7 · MongoDB 8.0.32 (native server, `127.0.0.1:27017`).
- Flask server mode: `python -m flask --app app:create_app run --no-reload`
  (development server, threaded, single process) — not a production WSGI
  deployment.

## Dataset (`skipq_system_test`, canonical seed)

users 6 · vendors 2 · menu_items 5 · carts 2 · orders 9. The polled stall
(Charcoal Grill) has 3 live menu items, so every menu find returns 3 rows.

## Instrumentation

`app/query_timing.py` (inactive unless the server process sets
`SKIPQ_QUERY_TIMING=1` + `SKIPQ_QUERY_TIMING_FILE`): one JSONL line per HTTP
request (`type=request`: path, status, request wall ms, the find commands
that request's thread issued with collection, rows, client-observed wall ms
and server-reported ms) and one line per materialised menu list
(`type=segment`, label `menu_materialize`). The find accounting comes from a
PyMongo 4 `CommandListener` installed at `MongoClient` construction via
MongoEngine's `mongo_client_class` — no post-hoc hooks, no added queries.
Client-observed find wall time includes loopback network + document
materialisation; server ms is the MongoDB-reported command duration.

## Runs (exact CLIs, run from `backend/`)

Server for each run (only the JSONL path differs):

```
MONGODB_DB=skipq_system_test MONGODB_HOST=mongodb://127.0.0.1:27017 \
SKIPQ_QUERY_TIMING=1 SKIPQ_QUERY_TIMING_FILE=q6-performance/query-timing-<run>.jsonl \
.venv/bin/python -m flask --app app:create_app run --no-reload --host 127.0.0.1 --port 5001
```

| Run | Locust CLI (same invocation in each) | Purpose |
|---|---|---|
| sanity | `.venv/bin/python -m locust -f tests/stress/locustfile.py --host http://127.0.0.1:5001 --headless -u 5 -r 1 -t 60s --class MenuLoadUser --csv q6-performance/sanity --csv-full-history --html q6-performance/sanity.html` | 5 u / 1 u/s / 60 s stability check |
| main | `.venv/bin/python -m locust -f tests/stress/locustfile.py --host http://127.0.0.1:5001 --headless -u 10 -r 2 -t 120s --class MenuLoadUser --csv q6-performance/menu --csv-full-history --html q6-performance/menu.html` | planned 10 u / 2 u/s / 120 s measurement |
| auth probe | `.venv/bin/python -m locust -f tests/stress/locustfile.py --host http://127.0.0.1:5001 --headless -u 10 -r 2 -t 30s --class LoginProbe --csv q6-performance/login --csv-full-history --html q6-performance/login.html` | repeated sign-ins, reported separately |

Times (SGT): sanity 09:15–09:16, main 09:22:57–09:24:57, auth probe
09:26:26–09:26:56. Each run used its own fresh server process and JSONL.

## Load-test results (locust `*_stats.csv`, the canonical client-side figures)

- **sanity** — 97 menu GETs + 5 one-time sign-ins, **0 failures**: menu
  median 6 ms, p50 6 / p90 10 / p95 14 / p99 20 / max 19.6 ms, 1.66 req/s;
  sign-in median 92 ms.
- **main** — 395 menu GETs + 10 one-time sign-ins, **0 failures**: menu
  avg 7.49 ms, p50 5 / p66 6 / p75 7 / p80 8 / p90 11 / p95 20 / p98 31 /
  p99 65 / p99.9 90 / max 89.7 ms, 3.31 req/s; sign-in median 94 ms,
  max 104 ms.
- **auth probe** — 40 sign-ins, **0 failures**: avg 138.2 ms, p50 95 /
  p90 270 / p95 540 / p98 570 / max 573.9 ms, 1.38 req/s.

Exceptions CSVs: empty for all three runs. Sign-ins are one-time setup
(`MenuLoadUser.on_start`) or the dedicated `LoginProbe`; they never mix into
the menu statistics.

## Server-side query/request timing (JSONL, per run)

- **sanity** (105 request lines, 98 segments): every menu request issues
  exactly 3 finds — `users` (1 row, token auth), `vendors` (1 row, stall
  lookup), `menu_items` (3 rows, `list_for_vendor`). Find server ms:
  min 0.12 / avg 0.51 / p50 0.37 / p95 0.98 / max 12.56 (n=302).
  `menu_materialize` wall: min 0.52 / avg 0.88 / p50 0.75 / p95 1.59 /
  max 6.21 ms.
- **main** (407 request lines, 395 segments): same 3-find shape, 3 rows per
  menu list. Find server ms: min 0.09 / avg 0.54 / p50 0.36 / p95 1.19 /
  max 22.25 (n=1198). `menu_materialize` wall: min 0.42 / avg 0.97 /
  p50 0.73 / p95 2.01 / max 12.36 ms.
- **auth probe** (44 request lines): sign-in issues one `users` find
  (1 row). Find server ms: min 0.25 / avg 1.41 / p50 0.55 / p95 7.09 /
  max 13.50 (n=45). The auth tail (locust p95 540 ms) coincides with the
  server-side find staying ≤ 13.5 ms: it is werkzeug password-hash
  verification under 10 concurrent dev-server threads, not the database.

## Count reconciliation (server JSONL vs client CSV)

The locustfile resolves the stall at import with one plain-`requests`
sign-in + `/api/diner/stalls` call (outside locust's counters), and a
request in flight at the run-time limit can land in the JSONL after the
CSV snapshot: sanity +1 menu/+1 sign-in (resolve), main +1 sign-in
(resolve), auth probe +1 sign-in (resolve) +2 in-flight sign-ins.

## Measurement limits

- Client-side (locust) times include loopback HTTP, dev-server threading,
  Python materialisation and JSON serialisation; they are not production
  WSGI numbers.
- Find "wall" and "server" times are near-identical on loopback; they cannot
  separate network from execution.
- Dataset is tiny (5 menu items, 3 live on the polled stall): query times do
  not scale with data. The verdict (`docs/report/q6-load-verdict.md`) is
  bounded to this machine, server mode and dataset.

## Artifacts

`sanity_stats.csv`, `sanity_stats_history.csv`, `sanity_failures.csv`,
`sanity_exceptions.csv`, `sanity.html`; `menu_stats.csv`,
`menu_stats_history.csv`, `menu_failures.csv`, `menu_exceptions.csv`,
`menu.html`; `login_stats.csv`, `login_stats_history.csv`,
`login_failures.csv`, `login_exceptions.csv`, `login.html`;
`query-timing-sanity.jsonl`, `query-timing-main.jsonl`,
`query-timing-login.jsonl`; `tests/stress/locustfile.py`;
`run-metadata.md`.
