# Q5(b) — Diner flow evidence (working note, Task 8)

**Status: the diner baseline flow is complete and was verified live; the
vendor flow is Task 9 and the US10 list filters are Task 10. This note is
condensed into the report at Task 13.**

## The flow as built

**Login → Stalls → Menu → Cart → Checkout → Tracking**, all under the
protected diner layout from Task 7.

1. **Stalls** — open stalls only, with the explicit Refresh control. Not an
   active-polling view; the menu and order views are.
2. **Menu** — image, description and cents price per item; sold-out items
   are greyed with their Add control disabled *before* the diner can act;
   a closed stall shows its banner and disables every Add control; a newly
   observed sold-out change (vendor toggled availability while the diner
   was on the page) raises a one-time toast. Polls every 3 s, stops on
   unmount, and has an explicit Refresh. "Add" sends the desired line
   quantity (current quantity + 1, because the server *sets* the line's
   quantity), and a refusal (sold out, closed stall, cross-stall cart)
   displays the backend's own message on this screen.
3. **Cart** — per-line quantity stepper (PATCH; decrement to zero removes
   the line server-side) and Remove (DELETE); the server-computed total and
   the read-only server checkout fingerprint. Loads on entry, after every
   mutation and on Refresh — not an auto-polling view.
4. **Checkout** — read-only cart summary with total and fingerprint;
   PayNow/Card/Cashless selection; a demo-only "simulate this payment
   failing" control. One checkout key is minted when the page loads and is
   **retained across retries** of the same attempt; the synchronous
   re-entry guard plus the in-flight disabled control prevents a second
   request from this tab, while requests beyond the UI (second tab, network
   retry) are the database idempotency's job. Success shows the payment
   result with the queue number, order id, status and payment, and a link
   to tracking (the server clears the cart). `payment_failed` keeps the key
   and invites a retry; `price_changed`/`item_unavailable`/`stall_closed`/
   `cart_empty` show the stale-cart refusal screen with Review /
   Refresh-and-retry (the retry re-sends the server's current fingerprint
   under the same key); `checkout_key_conflict` shows the backend message.
5. **Tracking** — live status badge with 3-second polling that stops on a
   terminal state or on unmount, plus an explicit Refresh. The Ready state
   raises the Ready-for-collection banner the moment it is observed;
   Collected, Cancelled (payment refunded) and NoShow (payment stays paid)
   show their terminal notices. A missing/foreign order shows the
   actionable 404/403 text with a way back to the list.

## Live verification (7 October 2026)

`task8_ui_check.py` (Playwright, diner UI context; vendor state changes via
the vendor API so the UI had to react to real server state) passed **all 21
checks on two consecutive runs**, each ending with the dev database
re-seeded to its seed invariants (S1 open, S2 closed, M1 650c, 9 seed
orders, 2 carts, D1's cart 2 lines). The run covered: seeded sold-out state
before any action; a polling-observed sold-out toast; menu add
*incrementing* the existing line; cart stepper/removal with the server
total moving $15.50 → $18.00 → $13.00; a price change under the open
checkout page refused with the stale-cart screen and succeeding after
refresh-and-retry ($14.50, 2× M1 snapshot at the new 725c price); the
Pending→Preparing→Ready walk with the Ready banner and the Collected
terminal; simulated failure then retry under the retained key with exactly
one stored order; a two-click double-submit storing exactly one order; a
vendor-sold-out line refused at checkout and paid out after removal; the
cross-stall refusal; and a forged token's 401 returning the diner to
sign-in.

This verification found and fixed one genuine UI defect: the cart and
checkout screens had no mount-time load, so they sat on "Loading…" until a
manual Refresh (the Task 7 screens, which carry their own loads or
polling, were unaffected; the earlier `stall.open`/`is_open` field-name
bug was found and fixed during Task 7's own screenshot review and is
recorded there).

**5-second target:** the design's status-update target is not claimed as
measured — each state change was observed within one 3-second polling
period in the runs above, but no timing measurement is asserted before the
Task 12 evidence exists.

## Screenshot ledger

All in `docs/evidence/screenshots/` (1280×720, authentic headless-Chromium
captures of the running app on `127.0.0.1:5173` against the dev API):

| File | What it shows |
|---|---|
| task8-01-stalls.png | Diner login lands on the open-stall list (Charcoal Grill, Open) |
| task8-02-menu-sold-out.png | Seeded sold-out Pineapple Tart greyed with the disabled "Sold out" control |
| task8-03-sold-out-toast.png | Toast for the newly observed sold-out change, menu still listing the item |
| task8-04-menu-after-add.png | "Add another (in cart: 2)" increment confirmed; cart total card $22.00 |
| task8-05-cart-edited.png | Cart after stepper/removal edits: 2× M1, total $13.00, fingerprint shown |
| task8-06-checkout.png | Checkout summary, 64-char server fingerprint, PayNow selected |
| task8-07-checkout-stale-refused.png | Stale-cart refusal ("Your cart total changed since it was loaded…") with Review / Refresh-and-retry and the retained-key notice |
| task8-08-checkout-success.png | Payment successful: queue number, order id, Pending, PayNow Paid, $14.50 |
| task8-09-tracking-pending.png | Tracking page: queue number, Pending badge, snapshot lines, payment state |
| task8-10-tracking-ready.png | Ready badge with the green "Your order is ready. Collect it at the counter." banner |
| task8-11-tracking-collected.png | Terminal Collected notice (polling now stopped) |
| task8-12-payment-failed.png | Simulated payment failure with the retained-checkout-key retry notice |
| task8-13-payment-retry-success.png | Retry under the same key: payment successful, one order stored |
| task8-14-double-click-single-order.png | Double-click result screen; exactly one order exists for the attempt |
| task8-15-stale-sold-out-refused.png | Checkout refused because a line sold out before payment |
| task8-16-after-removal-paid.png | Remaining line paid out after the sold-out line was removed |
| task8-17-cross-stall-refused.png | Cross-stall add refusal naming the stall already in the cart |
| task8-18-forged-token-sign-in.png | Forged-token 401: session cleared, sign-in presented |
