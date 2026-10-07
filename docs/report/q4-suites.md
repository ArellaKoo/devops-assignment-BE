# Q4 — Test suite arguments (working note, Task 6)

**Status: both assessed suites exist and have been run; this note is condensed into the report at Task 13.**

## Q4(a) — which methods the offline tests actually exercise

The offline suite supplies records and stubs only the persistence
boundary; the named methods run for real.

- `Order.transition_to` (and the `can_transition` decision it embeds) runs
  for real in `tests/unit/test_order_guard.py`: every one of the 36 state
  pairs, the 29:59/30:00/30:01 no-show boundary with an injected clock,
  the actor/scope refusals, and the expected-current-state update
  assertion (the test records the exact `{"set__status": ...}` update and
  the `(id, status)` filter, and the 0-modified race case proves a lost
  race raises `invalid_transition` without moving the local document).
  Mocking the persistence seam here still exercises the real guard,
  because the guard is the method under test and only its write call is
  supplied.
- The seam the test supplies is *narrow on purpose*: swapping
  `Order.objects` for a recorder cannot substitute for the query, because
  asserting on a mocked return value is not query verification. Asserting
  that a fake `list_for_diner` returns the rows the test told it to prove
  nothing about owner filtering, `status__in` semantics, or
  newest-first ordering in MongoDB. Those behaviours are not claimed offline; sorting is not independently established by the small functional fixtures: the real-DB suite drives `list_for_diner` through
  `GET /api/diner/orders?view=current|history` and checks the partition
  against documents that only the database wrote.
- `Order.place_from_cart` is the same story: the offline cases exercise
  the real stored-key replay, cart revalidation, fingerprint comparison,
  snapshot construction and cart clearing; only `find_by_checkout_key`,
  `save` and the cart write are supplied. The unique-index behaviour
  itself is only proven by the functional suite's concurrent checkout
  against the real index.

## Q4(b) — two concrete strengths of the assessed suites

1. **Actual token/route/model integration, not canned records.** The
   functional tests never inject users: `User.create` writes a real hashed
   account, `POST /api/user/gettoken` must verify it and mint a signed
   3,600-second token, and every subsequent request carries that token
   through `current_user()` → `require_role` → the model scope check. The complete real-persistence chain cannot be established by the unit suite — the unit route tests
   patch `User.find_by_id` and cannot say anything about
   authentication against a stored hash, token round-trips through the
   JSON body, or the 401/403 boundary that only a real request exercises.
   The full `test_diner_and_vendor_complete_order` walks
   Pending→Preparing→Ready→Collected with two separately signed tokens
   and asserts both the HTTP response and the diner-visible state after
   each vendor move — an end-to-end sequence the offline suites, which
   supply the actor directly, structurally cannot contain.
2. **Real database references, updates and fixture isolation.** The
   functional pair proves things that only the database can say: the
   two-thread same-key checkout hits the real
   `(checkout_key, diner)` unique index — exactly one request stores the
   order (201), the other returns the stored order as a replay (200),
   and `Order.objects(checkout_key=...).count() == 1` is read back from
   MongoDB, not from a mocked collection. The stale-checkout cases prove
   *no* order row was inserted for each refused key, and the snapshot
   test re-reads the stored order after the menu item was renamed and
   re-priced, showing the purchased name/price survive in the database.
   Fixture isolation is real too: the conftest rejects the development
   database name before any connection, registers every created
   document, sweeps route-created carts and orders by reference, and
   disconnects the MongoEngine alias after each app — which is why the
   suite has been run twice against the same `skipq_test` database,
   leaving it at zero documents after each run with no manual reset.

## Run results (7 October 2026)

- `python -m pytest tests/functional -q` — run 1: **10 passed**; run 2
  (same guarded `skipq_test`, no reset between runs): **10 passed**.
  Post-run state after each run: orders/carts/users/vendors/items all 0.
- Guard check: `SKIPQ_FUNCTIONAL_DB=skipq_dev` fails every functional
  test at fixture setup (`Refusing to run the functional suite against
  the development database name`); `SKIPQ_FUNCTIONAL_DB=skipq_test_extra`
  is accepted and passes with its own cleaned state.
- Offline unit suite with MongoDB stopped (socket sentinel active):
  **287 passed** (re-run after the duplicate-key fix landed).
- Fix found by the suite: MongoEngine's `Document.save()` re-raises the
  pymongo duplicate-key error as its own `NotUniqueError`, which
  `Order.place_from_cart` did not catch — the concurrent loser would have
  leaked a 500 instead of returning the winner. The model now catches
  both; the offline race case covers `DuplicateKeyError` and the
  functional race covers `NotUniqueError` through the real index.

## Q4(c) — designed extra-story suite (not implemented)

US10's history cases (the H01–H11 design table and the strategy/priority
argument) are written as a design only in
`docs/report/q4-extra-story-tests.md` (landed with Task 10); this build
does not implement that suite, and nothing in Tasks 6–11 runs it.

## Final review clarification

The functional suite proves ownership/status filtering, stored purchase snapshots, guarded transitions and checkout concurrency. Its small order fixtures do not independently prove equal-time sorting or full newest-first ordering. Sorting was observed in the US10 browser checks; H09 remains a designed, unexecuted Q4(c) case. Current unit verification blocks socket access; MongoDB can remain running for other suites.
