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
- Remaining live items (no protected persona route exists yet): 401 on a
  protected request without/with an invalid or expired token, and 403 for
  the wrong persona, verified over HTTP when the diner/vendor routes land
  in Task 4, with cross-stall/diner scope exercised through the real API
  in Task 6.
