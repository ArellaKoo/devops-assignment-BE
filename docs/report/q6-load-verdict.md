# Q6(b) — Local load measurement and bounded database verdict

## Endpoint choice

The diner UI polls `GET /api/diner/stalls/<id>/menu` every 3 seconds while a
stall menu is open — the application's most frequent request. Order
placement and checkout are once-per-order events, so sustained load on them
would not represent real usage. Load was therefore applied to the menu
endpoint at the UI's polling cadence (Locust `wait_time` 2.9–3.1 s). Sign-in
runs once per simulated user (`on_start`) and in a separate 30 s
`LoginProbe` run, so authentication never mixes into the menu statistics.

## What was measured

10 users / 2 spawn/s / 120 s (after a 5 u / 1 u/s / 60 s sanity run, 0
failures): **395 menu requests, 0 failures** — p50 5 ms, p90 11 ms,
p95 20 ms, p99 65 ms, max 89.7 ms, 3.31 req/s. Opt-in server-side
instrumentation (PyMongo 4 command listener + request/segment wall clocks,
`q6-performance/run-metadata.md`) shows each menu request issues exactly
three finds — `users` (1 row), `vendors` (1 row), `menu_items`
(3 rows) — with driver-observed command durations (historically named `server_ms`), and the
materialised menu list (3 documents to JSON-serialisable dicts) at
p50 0.73 ms / p95 2.01 ms. The separate auth probe (40 sign-ins, 0
failures) put p95 at 540 ms while its single `users` find stayed ≤ 13.5 ms.
All runs: one M3 MacBook Air (8 cores, 8 GiB), macOS 26.6.2, Flask 3.1.3
dev server (`--no-reload`), MongoEngine 0.29.3 / PyMongo 4.18.2, MongoDB
8.0.32 on loopback, seeded dataset of 6 users / 2 vendors / 5 menu items /
9 orders.

## Database verdict (≤100 words)

At 10 users and 3.31 menu requests/s, 395 requests succeeded. Each issued three finds, including `MenuItem.list_for_vendor` returning three items. Combined driver-observed command duration was p95 3.16 ms; API wall time was p95 8.23 ms and Locust latency p95 20 ms. Menu materialisation was p95 2.01 ms. Command time represented a median 39% of paired API wall time. These measurements include transport and driver overhead; they do not isolate MongoDB execution or explain the remaining latency. No large query delay appeared on this small dataset; production bottlenecks remain inconclusive.

## Timing correction and reproducible analysis

PyMongo reports an operation duration observed by the driver, not isolated server execution. Original JSONL measurements are preserved; their `server_ms` key is a historical mislabel. New instrumentation uses `command_ms`. [PyMongo command-monitoring documentation](https://pymongo.readthedocs.io/en/stable/api/pymongo/monitoring.html#pymongo.monitoring.CommandSucceededEvent.duration_micros).

Run `.venv/bin/python scripts/summarize_performance.py` from backend. The resulting `q6-performance/reconciled-analysis.json` sums all three finds for each menu request and pairs that sum with the same request’s API wall time. Percentiles use linear interpolation. Exactly one menu request also recorded one other command; the previous “no extra commands” claim was incorrect. Separate percentile values do not establish per-request causation or CPU attribution.
