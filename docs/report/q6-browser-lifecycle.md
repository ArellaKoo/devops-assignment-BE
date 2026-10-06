# Q6(a) — the order lifecycle through two browser personas

Verified 7 October 2026. Suite: `tests/playwright/test_order_lifecycle.py` (fixture guards in `tests/playwright/conftest.py`). Run evidence: `docs/evidence/browser-lifecycle/run-1.log` and `run-2.log` (full pytest output, run time, commit, database and server metadata); per-state screenshots `docs/evidence/screenshots/task11-01…11.png`.

## The finding (report text)

The Playwright suite signs the diner and the vendor in through the real login screen in two isolated browser contexts — no token is injected into either browser, and each context's session lives in its own sessionStorage. The diner clears the leftover seeded cart lines through the cart screen, adds one menu item, and checks out through the checkout screen, which mints the order's checkout key itself; the paid screen displays the new queue number, and the vendor's order queue surfaces that exact queue number through its own 3-second polling before Accept, Mark ready and Mark collected are performed on the vendor's screens. After each transition the diner's tracking screen — polling on its own timer in the other context — is observed to display Preparing, then the Ready-for-collection notice, then the terminal Collected state, with the exact action set asserted on both screens at every stage (Pending: Accept/Reject only; Preparing: Mark ready only; Ready: Mark collected only; terminal: no controls). An in-process functional test cannot establish this: the Flask test client does not render React routing, DOM banners or per-context sessionStorage separation, does not exercise the checkout key the UI mints, and cannot show two independently polling browsers converging on the persisted state — the browser runs are the only evidence that the UI itself drives the complete lifecycle.

## What the runs exercise, step by step

1. Diner UI sign-in (`/login`, email + password) → stall list with the open stall and its Open badge.
2. Leftover cart lines removed through the cart screen's Remove controls until "Your cart is empty." (run 1 removed the two seeded lines; run 2 started with the cart document already gone, so the API lazily created an empty cart — both paths are the UI's own).
3. One item added from the stall menu (Add control, enabled before the action); the success notice and the "Review your cart" card appear.
4. Cart screen: exactly one line, $6.50 each, Remove available, server fingerprint displayed; "Continue to checkout".
5. Checkout screen: PayNow preselected, the demo failure control left unchecked, "Pay $6.50"; the paid screen displays the queue number, PayNow/Paid and $6.50.
6. Diner tracking screen: Pending badge, snapshotted line, "Payment: PayNow · Paid", live-update note.
7. Vendor UI sign-in → order queue: nine rows (8 seed + new), the new queue number's row Pending at the top; Manage.
8. Vendor detail: the exact allowed-action set per state; Accept → Preparing (vendor immediate, diner within its next poll); Mark ready → Ready + diner's Ready notice; Mark collected → Collected + terminal notice on both screens, live-update note gone (polling stopped).
9. US10 closure: the finished order appears in the diner's Past filter (4 rows, newest first, Collected) and is absent from Current (5 rows).
10. Model-level proof in the fixture process: stored order Collected/Paid/650 c with `ready_at`, snapshot ("Charcoal Chicken Rice", 650, 1), a UUID checkout key minted by the UI, exactly one run-owned order among the nine untouched seed orders.

## Runs and state

- Run 1: `1 passed` in 12.02 s; run 2: `1 passed` in 11.48 s — same `skipq_system_test` database, no reset between runs (each run's teardown deletes only its own 32-hex run-id order and the test diner's cart; run 2's "10 orders = 9 seed + 1" assertion is the no-reset check).
- Guard checks: the fixtures refuse `skipq_dev*`/`skipq_test*` names before connecting, verify both servers (the API's JSON 404 envelope, the React document) and the seed state before the first persona step, and disconnect the MongoEngine alias on teardown.
- One defect found by the first full run, in the test itself: the stall screen's "View menu" control is a link styled as a button, so the locator used a button role; corrected to a link role. No application change was needed.
- Post-run state after run 2: 9 seed orders, 0 run orders; `skipq_system_test` re-seeded to canonical state afterwards for later tasks.
