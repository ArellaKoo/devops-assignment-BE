# SkipQ implementation continuation record

Updated after every milestone. Records completed work, verification results, commits, remaining tasks and the next action. No unrun command is described as passing; no evidence is invented.

## Baseline (start of execution, 7 October 2026)

- Both repositories clean on `setup/lab-adaptation`. Backend foundation commit `67cd54e`; frontend foundation commit `a10607d`.
- Task 1 (reproducible foundation) verified and committed; domain models, seed data, sign-in, persona flows and assessed suites not yet implemented.
- Environment: Python 3.12.15 in `backend/.venv`; local MongoDB 8.0.32 on `127.0.0.1:27017` (workspace-local archive under `.local/tools/`); Node 22.17.0 via nvm; CRA `react-scripts` 5.0.1 with TypeScript 4.9.5 build peer.
- Original TMA PDF (16 pages) and GBA DOCX (363 paragraphs, 35 tables, 18 embedded images) re-extracted and re-read; the plan's audit of Q1–Q7, GBA stories US1–US17, backlog priorities, Q4 features, Q5 screens and the Q6 UML descriptions confirmed against the source documents.
- US10 (current/past orders) and the documented design/lifecycle corrections approved for execution.

## Task 2 — Domain documents and seed coverage (complete)

**Completed work**

- `app/errors.py`: `DomainError` hierarchy with the design's stable codes (`validation_error` 400; `authentication_required`/`invalid_credentials` 401; `login_locked` 429; `forbidden` 403; `not_found` 404; `stall_closed`, `item_unavailable`, `cross_stall_cart`, `cart_empty`, `price_changed`, `payment_failed`, `checkout_key_conflict`, `invalid_transition`, `no_show_too_early` 409; `internal_error` 500). JSON error handler preserves `Allow`/`Retry-After` headers.
- `app/models/`: `user.py` (normalised unique email, hashed password, role, optional Vendor reference, failed-login count/locked-until, lockout rules in `User.authenticate(email, password, now)`), `vendor.py` (stall with `is_open`, `list_open`, actor authorisation through the stall relationship), `menu_item.py` (typed fields, integer cents, `parse_price_cents`/`validate_name`/`validate_description`/`validate_image_url`/`validate_item_values`, own-stall create/update/soft-delete, `list_for_vendor`), `cart.py` (one cart per diner, embedded CartItems, `parse_quantity`, `total_cents`, SHA-256 `compute_fingerprint`, `set_item`/`remove_item`/`clear_items` re-checking current records), `payment.py` (embedded simulated receipt, PayNow/Card/Cashless, Paid/Refunded), `order.py` (typed references, embedded OrderItem snapshots + Payment, `unique_with=["diner"]` on `checkout_key`, guarded `can_transition`/`transition_to`/`allowed_actions`, `place_from_cart` with stored-key-first replay, scoped reads `get_for_diner`/`get_for_vendor`/`list_for_vendor`/`list_for_diner(view=all|current|history)`). `app/models/common.py` centralises UTC normalisation and id comparison.
- `db_seed/` (`fixtures.json` + `seed.py`): idempotent upserts by natural keys; deterministic handles D0/D1/D2, V1/V1B (S1), V2 (S2), S1 open, S2 closed, M1–M5, carts C1/C2, orders O-P/O-PR/O-R/O-RO/O-C/O-X/O-N/O-F/O-S2; time-relative Ready fixtures recomputed each run; bundled seed images under `static/images/` served by the app factory.
- Report artifacts: `docs/report/seed-coverage.md` (criterion-by-criterion argument + states seeding cannot produce), `docs/report/q1-audit.md` (four capability audits with statuses, five-row tables and a dated maintenance log), README "Seed data and demo accounts" section with the fixture emails and demo password.

**Verification (actual results this session)**

- `python -m pytest tests/unit/test_validation.py tests/unit/test_cart.py -q` before implementation: collection error (`ImportError: cannot import name 'DomainError'`), then after the model skeleton, meaningful rule failures; after implementation all pass.
- `python -m pytest tests/unit -q` with MongoDB **stopped** (port 27017 confirmed down): **75 passed** in 0.04s — unit suite is offline, per Q4(a).
- `python -m db_seed.seed` run **twice** against `skipq_dev`: both runs reported `vendors: 2, users: 6, menu_items: 5, carts: 2, orders: 9` (stable counts; upserts, no unrelated data touched).
- Seeded-state invariant check against real `skipq_dev` through the real model methods: credentials verify via `User.authenticate`; V1/V1B share stall S1; C1 total 1,550 cents; O-RO allows NoShow while O-R refuses `no_show_too_early`; O-C snapshot ("Grilled Chicken Rice", 600c) differs from current M1 ("Charcoal Chicken Rice", 650c) with matching total/payment; O-X Cancelled+Refunded; vendor scope (V1 manages O-P, refused on O-S2); D1's list excludes O-F; current/history views partition correctly; D0 empty. Result: `ALL SEED INVARIANTS PASSED`.
- MongoEngine note: compound unique index is declared via `checkout_key = StringField(required=True, unique_with=["diner"])` (the installed MongoEngine 0.29.3 exposes no `IndexFields`); to be exercised by the real-DB functional suite (Task 6).

**Commit**: `feat: add SkipQ documents and repeatable seed data` on `setup/lab-adaptation` (this milestone).

**Remaining tasks**: 3 (auth + token API + `test_auth_rules.py`), 4 (menu/trading/cart routes + manual API checks), 5 (checkout + lifecycle routes + `test_order_guard.py`), 6 (conftest + functional suites ×2 + Q4(a)/(b) notes), 7 (frontend shared architecture), 8 (diner flow + screenshots), 9 (vendor flow + screenshots), 10 (US10 screens + Q4(c) design table), 11 (Playwright ×2), 12 (Locust + `q6-performance/`), 13 (report, screencast preparation, READMEs, clean-checkout rehearsal, final handover).

**Next action**: Task 3 — write failing `tests/unit/test_auth_rules.py`, implement `app/auth.py` (signed 3,600 s Bearer tokens, `require_role`) and `app/controllers/auth.py` (`POST /api/user/gettoken`), verify against the live API, commit.
