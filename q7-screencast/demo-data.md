# Q7(a) screencast — demo data checklist

The recording must start from the canonical seed state so every figure in
the narration (prices, queue lengths, refusal messages) is reproducible.
All of this comes from the backend seed (`db_seed/seed.py` +
`db_seed/fixtures.json`); no hand-edited records.

## Accounts (seeded)

| Role | Email | Password | Notes |
|---|---|---|---|
| Diner | `diner.one@skipq.test` | `SkipQDemo2026!` | the recording's diner; owns 8 seed orders spanning all six statuses |
| Vendor | `vendor.one@skipq.test` | `SkipQDemo2026!` | bound to stall S1 Charcoal Grill |

## Stalls (seeded)

- **S1 Charcoal Grill — open.** The recording's stall. Menu:
  - M1 **Charcoal Chicken Rice** — $6.50, available
  - M2 **Mango Sago** — $2.50, available
  - M3 **Pineapple Tart** — $4.00, **sold out** (seeded, greyed on the menu)
- **S2 Noodle Bar — closed.** Not used in the recording; its presence in
  the seed is what makes the "open stalls only" list meaningful.

## Seeded orders and carts (why the screens look lived-in)

- D1 owns 8 seed orders: Pending, Preparing, Ready ×2, Collected,
  Cancelled (refunded), NoShow (payment stays paid) — these power the
  Order List All/Current/Past demo (US10) and the read-only snapshots
  (the Collected order shows the *old* item name and price
  "Grilled Chicken Rice $6.00", proving purchase snapshots are immutable).
- D1 also starts with a seeded cart (2× M1 + 1× M2 = $15.50). The
  recording opens by **emptying it** (shot demo-01) so every amount
  narrated afterwards is the demo's own, not the seed's.

## State the recording itself changes — and restores

| Change | Who | Restored afterwards? |
|---|---|---|
| 1 new paid order (1× M1, $6.50) taken to Collected | the demo | yes — the script's cleanup deletes the run's own order only |
| D1's cart: emptied, then 1× M2, then +1× M1 | the demo | yes — the script clears D1's cart |
| M2 marked sold out, then restored to available | vendor step | yes |
| S1 closed, then restored to open | vendor step | yes |

If you record by hand instead of the script, restore the last two rows
yourself (vendor menu screen: the trading-state switch back to open, and
M2's "Mark sold out" control back to "Available"). The seed itself is
idempotent but *never deletes* existing records, so re-seeding alone does
not remove a run's order — the reliable reset is to drop and re-seed the
guarded database:

```bash
cd backend
.venv/bin/python - <<'PY'
from pymongo import MongoClient
MongoClient('mongodb://127.0.0.1:27017').drop_database('skipq_system_test')
PY
MONGODB_DB=skipq_system_test .venv/bin/python -m db_seed.seed
```

(Or just run `demo_script.py`, which restores the two vendor-side states
and deletes its own order at the end.)

## Invariants to check before you hit record

Run this from `backend/` (or just watch the script's preflight output):

- 9 seed orders, 0 run orders (queue numbers `Q-seed-*` vs `Q-<hex32>`)
- S1 open, S2 closed; M1/M2 available, M3 sold out
- D1's cart is what you expect (the recording starts by emptying it)
- The API answers 401 without a token (you're on the real app, not a stub)
