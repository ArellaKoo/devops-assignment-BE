# Q3 — Role/scope enforcement and model-guard placement (living document)

**Status: implemented for auth; finalised into the report at Task 13.** The
workbook budgets ~150 counted words for Q3; this working note is longer and
will be condensed, with the same code references, when the report is
assembled.

## Where the role enforcement lives

All persona Blueprints share the two helpers in `app/auth.py`:
`current_user()` resolves the request's `Authorization: Bearer <token>`
header into a trusted `User` document — refusing with 401
`authentication_required` when the header is missing/malformed, the token
was not signed with the configured secret, it is past its 3,600-second
life (inclusive boundary: exactly 3,600 s still verifies), or its id
matches no stored account — and `require_role(user, role)` raises 403
`forbidden` before any controller body runs when the verified account's
role does not match the persona the route belongs to. `role_required(role)`
wraps that pair for route registration; login itself lives in
`app/controllers/auth.py` (`POST /api/user/gettoken`), which returns the
signed token plus the persona identity (id, normalised email, role, stall
id) and never returns a password hash.

## Why record ownership stays in the models

A role answer is not a scope answer: a valid vendor token must still fail
on another stall's menu item or order, and a valid diner token on another
diner's cart or order. So every scoped read and mutation in `app/models/`
takes the actor and checks the relationship itself — `Vendor.authorizes`,
`MenuItem.authorizes_vendor`, the cart owner check in `Cart.set_item`, and
`Order.can_transition`/`get_for_diner`/`get_for_vendor` — and raises the
same 403/409 codes no matter which persona made the request. The shared
gate therefore answers "is this the right *kind* of account?"; the model
methods answer "is this *this* account's record?". Neither layer reads
persona-identifying ids from the request body: the actor always comes from
the verified token, and the record always comes from a model query scoped
to that actor.

## Why the lifecycle guard lives in `Order.transition_to`

The order lifecycle is state, not presentation: any caller — the vendor
route, the seed script, a future admin tool — must be able to move an
order, and none of them may carry its own copy of the rules. So the guard
is a model method, `Order.transition_to`, which re-checks the actor's
role and stall ownership, the current state, the five permitted edges,
and the 30-minute NoShow boundary, then persists with an
expected-current-state update so two racing vendors cannot both apply a
move; `Order.allowed_actions` reuses the same pure decision, and the
routes (`PATCH /api/vendor/orders/<id>/status`, the order reads, and
checkout via `Order.place_from_cart`) only translate the request into the
call and map the model's `DomainError` codes to the JSON error contract.

## Verified so far (actual results, 7 October 2026)

- Unit, offline (MongoDB stopped, socket sentinel active): 120 passed,
  including the 45 auth-rule cases in `tests/unit/test_auth_rules.py` —
  real `User.authenticate` lockout sequence with supplied record access,
  token round-trip/boundary/tamper/secret/unknown-account cases with an
  injected clock, `require_role` persona refusals, and
  `POST /api/user/gettoken` 200/400/401/429 through the Flask test client.
- Live against the dev API on 127.0.0.1:5001 with seeded `skipq_dev`:
  diner/vendor/shared-stall logins 200 with token + persona and no
  credential fields; wrong password 401 `invalid_credentials`; missing/
  empty/absent body fields 400 `validation_error`; a throwaway account
  locked on its fifth failure (attempts 1–4 401, 5th and while-locked 429
  `login_locked`) then removed; a live-issued token verified through the
  real `User.find_by_id` seam to the right account, and refused when the
  injected clock was placed past the TTL.
- Protected-route live checks (Task 4, dev API on 5001): no token 401
  `authentication_required`, garbage token 401, a 3,601-second-old token
  401, vendor token on a diner route 403, diner token on a vendor route
  403, and cross-stall item edits 403 — all through real HTTP against
  `skipq_dev` (`.local/verification/live_persona_check.py`). Cross-diner
  scope through the real API is exercised in Task 6.
- Lifecycle guard and routes (Task 5): offline 75 guard cases in
  `tests/unit/test_order_guard.py` (all 36 state pairs plus an unknown
  target, the 29:59/30:00/30:01 NoShow boundary with an injected clock,
  actor/scope refusals, expected-state update semantics, and the
  `place_from_cart` allow/refuse matrix including replay, conflict,
  stale price, failed payment and the duplicate-key race) and 38 route
  cases in `tests/unit/test_order_routes.py`; live, a full
  Pending→Preparing→Ready→Collected walk with separately signed diner and
  vendor tokens, matching replay 200 / conflicting key 409, failed
  payment 409 with the cart intact, the diner's All/Current/Past views,
  and — the item deferred from Task 4 — the stall's paid queue staying
  processable while the stall is closed (`.local/verification/live_order_check.py`,
  63/63 checks on the dev API).
