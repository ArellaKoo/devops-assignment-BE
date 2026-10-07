# Q7(a) demo-script run log (authentic record)

**What this is.** `demo_script.py` is a scripted, headless Playwright
verification of the exact steps the narrated screencast will perform
(`script.md`). It is NOT the submission recording — the narrated
≤8-minute 720p MP4 is recorded by the student following
`recording-steps.md`. This log records that every step of the script
executes against the running app and produces the expected visible
outcome, including both rule violations.

## Verified run

- **Date:** 7 October 2026
- **Machine:** Arellas-MacBook-Air, Apple M3 8-core / 8 GiB, macOS 26.6.2
- **Command (from `backend/`):**
  `MONGODB_DB=skipq_system_test .venv/bin/python q7-screencast/demo_script.py`
- **Environment:** MongoDB 8.0.32 at `127.0.0.1:27017`; the guarded
  database `skipq_system_test` freshly seeded; the plain (uninstrumented)
  Flask API serving that database on `127.0.0.1:5001`; the CRA dev server
  on `127.0.0.1:5173` (Node 22.17.0).
- **Result:** `DEMO SCRIPT: ALL STEPS PASSED` — 26 per-step screenshots in
  `demo-screenshots/`, preflight and post-cleanup invariants re-verified
  (9 seed orders, 0 run orders, M2 available, Charcoal Grill open).

### Console output (verbatim, passing run)

```text
preflight: servers up, seed state verified (9 seed orders, 0 run orders)
Phase A: diner places an order, vendor moves it to Collected
  [shot] demo-01-diner-empty-cart
  [shot] demo-02-diner-stalls
  [shot] demo-03-diner-menu
  [shot] demo-04-diner-added-m1
  [shot] demo-05-diner-cart
  [shot] demo-06-diner-paid
  paid: Q-c614c5d8bca24eb9a8b7b6708e912d64
  [shot] demo-07-diner-tracking-pending
  [shot] demo-08-vendor-queue-pending
  [shot] demo-09-vendor-preparing
  [shot] demo-10-diner-preparing
  [shot] demo-11-vendor-ready
  [shot] demo-12-diner-ready-banner
  [shot] demo-13-vendor-collected
  [shot] demo-14-diner-collected
  [shot] demo-15-diner-past-filter
Phase B: sold-out line is refused at checkout, cart retained
  [shot] demo-16-diner-added-mango-sago
  [shot] demo-17-diner-cart-mango-sago
  [shot] demo-18-vendor-marked-sold-out
  [shot] demo-19-diner-checkout-before-pay
  [shot] demo-20-diner-checkout-refused-sold-out
  [shot] demo-21-diner-cart-retained
  refused checkout stored no order (run orders: exactly the phase-A one)
Phase C: closed stall is refused at checkout, cart retained
  [shot] demo-22-diner-added-again
  [shot] demo-23-diner-cart-two-lines
  [shot] demo-24-vendor-stall-closed
  [shot] demo-25-diner-checkout-before-pay-closed
  [shot] demo-26-diner-checkout-refused-closed
cleanup
DEMO SCRIPT: ALL STEPS PASSED
```

## What was verified, step by step

**Preflight** — the API refuses a tokenless request with 401; the CRA
dev server serves the React app; the guarded `skipq_system_test`
database holds the 9 seed orders and 0 run orders; both demo accounts
exist.

**Phase A — the same order through both personas** (shots 01–15):

1. Diner signs in at `/login`, lands on the stall list (Charcoal Grill
   open), and the seeded cart is emptied (shot 01).
2. The menu is opened; `Add` on Charcoal Chicken Rice increments the
   line (shot 04); the cart shows 1 × M1 = $6.50 (shot 05).
3. At checkout the simulated-failure control is off; `Pay $6.50` succeeds
   and shows the fresh queue number
   `Q-c614c5d8bca24eb9a8b7b6708e912d64` (shot 06).
4. The diner's tracking screen shows the order **Pending** (shot 07).
5. The vendor signs in; the vendor's polling queue surfaces that exact
   queue number as **Pending** (shot 08). The same order, not a copy.
6. `Manage` → `Accept order`: the vendor detail shows **Preparing**
   (shot 09) and the diner's tracking screen observes **Preparing** by
   its own polling (shot 10).
7. `Mark ready`: **Ready** (shot 11); the diner's
   "Collect it at the counter." banner appears (shot 12).
8. `Mark collected`: **Collected** on the vendor detail (shot 13) and on
   the diner's tracking screen with the terminal "thanks for ordering"
   notice (shot 14).
9. US10: the diner's Order List, Past filter, shows the finished order
   read-only with the **Collected** badge (shot 15).

**Phase B — violation 1: sold-out line refused at checkout**
(shots 16–21):

10. The diner adds Mango Sago (shot 16); the cart now holds 1 × M2 =
    $2.50 (shot 17).
11. The vendor marks Mango Sago **Sold out** (shot 18).
12. The diner's `Pay $2.50` is refused: the **Checkout refused** screen
    names the item — "Mango Sago is no longer available. Remove it from
    your cart to check out." (shot 20).
13. `Review your cart` shows the line retained, not deleted (shot 21).
14. API check: exactly one run order exists — the refused checkout stored
    nothing.

**Phase C — violation 2: closed stall refused at checkout**
(shots 22–26):

15. The diner adds Charcoal Chicken Rice again (shot 22); the cart now
    holds 1 × M2 + 1 × M1 = $9.00 (shot 23).
16. The vendor flips the trading-state switch; the stall shows the
    **Closed** badge and the closure banner (shot 24).
17. The diner's `Pay $9.00` is refused: **Checkout refused** with
    "Charcoal Grill is currently closed. Try again once the stall
    opens." (shot 26). The cart stays retained.

**Cleanup** — the script deletes exactly its own run order (asserts the
count), clears the test diner's cart, restores Mango Sago to available
and Charcoal Grill to open, then re-verifies the seed invariants
(9 seed orders, 0 run orders, both demo accounts present).

## Genuineness notes

- The script is a real end-to-end execution: real HTTP calls to the
  running API through the running UI, real polling waits (3-second UI
  poll, 15-second assertion windows), real database state before and
  after. No step is faked, replayed or mocked.
- The queue number in shot 06 is minted at run time; it differs from
  every earlier run and from the seed queue numbers.
- Failures encountered while developing this script (a mis-mapped
  control role, a strict-mode alert collision, a post-disconnect
  verification call) are genuine development iterations, not
  demonstrations: each fix is in the committed script, and this log
  records only the passing run.
- Screenshots are headless-Chromium captures at 1280×720, the same
  viewport the recording will use.

## Re-running it

See `recording-steps.md` for the full setup (both servers, the guarded
database, the seed state). The script refuses to start unless
`MONGODB_DB` names the guarded `skipq_system_test` database and the
seed invariants hold.
