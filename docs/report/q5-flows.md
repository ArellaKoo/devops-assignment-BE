# Q5(b) — Flow evidence (working note, Tasks 8–10)

**Status: the diner baseline flow (Task 8), the vendor baseline flow
(Task 9) and the US10 order-list filters (Task 10) are complete and were
verified live. This note is condensed into the report at Task 13.**

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

## The vendor flow as built (Task 9)

**Login → Menu → (item form) / Orders → Order detail**, all under the
protected vendor layout from Task 7.

1. **Menu** — the own-stall name with an Open/Closed badge and a
   trading-state switch (`PATCH /api/vendor/stall`); the switch state is
   echoed in a label and, while closed, in a closure banner that states
   new orders are refused while the paid queue stays accessible. Each item
   row carries its image, description, cents price, updated time, a
   Sold-out badge when unavailable, a sold-out/restock toggle
   (`PATCH /api/vendor/menu/<id>` with `is_available`), an Edit link and a
   confirm-gated Remove (soft delete). The screen loads on mount, after
   every mutation and on Refresh — the vendor is this screen's actor, so
   it does not poll; the paid queue does.
2. **Item form** — one screen for create (`/vendor/menu/new`) and edit
   (`/vendor/menu/:itemId/edit`): name (1–80), price (decimal string
   above 0 and below 9999, at most two decimals), description (≤500),
   image URL (http(s) JPG/JPEG/PNG) and an available-now checkbox. The
   rules are stated on the screen, and a refused save shows the backend's
   own 400 message verbatim; the server remains the final validator. The
   edit screen loads the stall's menu list and picks out its item (the API
   has no single-item read), reporting an item that left the menu as
   removed.
3. **Paid queue** — the stall's stored orders, newest first, with queue
   number, status badge, item count, total and placed time. It polls every
   3 s while any order is still active (a second account on the shared
   stall can move one) and stops once every order is terminal; explicit
   Refresh always works. While the stall is closed it carries the closure
   banner but every order and Manage control stays available — the queue
   is a fulfillment obligation, not a trading surface.
4. **Order detail** — queue number, status badge, item quantities with the
   snapshotted names/prices, total, placement/ready times and the payment
   line (method, state, amount, refunded time when present). The action
   row is rendered **strictly from the response's `allowed_actions`**:
   Pending offers Accept order / Reject order, Preparing offers only
   Mark ready (rejection stops once preparation has started — the
   canonical lifecycle has no Preparing→Cancelled edge), Ready offers
   Mark collected and, only after `ready_at` + 30 minutes, Mark no-show,
   and terminal orders offer nothing at all, showing instead their notice
   (Collected = complete; Cancelled = refunded with time; NoShow =
   payment stays paid). The 30-minute rule is therefore visible in the UI,
   not only enforced by the backend; destructive moves (Reject,
   NoShow) ask for confirmation.

## Live verification — vendor run (7 October 2026)

`task9_ui_check.py` (Playwright, **two logged-in UI contexts** — vendor.one
on Charcoal Grill and diner.one; both personas sign in through the login
screen) passed **all 37 checks on two consecutive runs**, each starting
from a reseed and ending with the dev database re-seeded to its seed
invariants (`invariant: True False 650 True True 9 2 2`). The run covered:
the menu listing the three active items while hiding the soft-deleted one;
the switch closing the stall (badge, banner, a diner cart add refused
`409 stall_closed`, and the diner's direct-link view of the closed stall
with every Add control disabled) and reopening it; the create form
showing the backend's own 400 price message; a valid create, an edit
(pre-filled, renamed, repriced) and a removal; a sold-out toggle and
restock on a seeded item; the queue listing the stall's eight paid orders
newest-first with the other stall's order absent; the exact control sets
on Pending (Accept/Reject only), Preparing (Mark ready only), Ready +5 min
(Mark collected only — NoShow still hidden) and Ready +35 min (Collected
plus NoShow); all three terminal orders read-only, including the seeded
refunded cancellation, the seeded no-show (payment stays paid) and the
stale purchase snapshot ("Grilled Chicken Rice" at $6.00, old name and
price); another stall's order refused in the UI with the 403 screen and,
at the API level, a premature NoShow refused `409 no_show_too_early`; the
closed stall keeping its whole paid queue accessible; and — the same new
order in both contexts — the diner paying the seeded cart ($15.50, 2× M1 +
1× M2) through the checkout screen while the vendor's polling queue
surfaced it, accepted it, marked it ready (the diner's Ready banner
appeared on the diner's tracking page without a manual refresh) and
collected it; seeded Q-seed-0001 was then rejected (Cancelled, refunded,
the diner seeing the $13.00 refund notice) and seeded Q-seed-0004 was
marked no-show past the 30-minute boundary (the diner seeing the
stays-paid notice); finally a diner account was routed out of the vendor
area to its own home.

This verification found and fixed two genuine UI defects: the vendor menu
screen had no mount-time load (it sat on "Loading…" until a manual
Refresh), and the item form initially requested a single-item read the API
does not offer — it now loads the menu list and selects its item,
reporting an off-menu item as removed. The earlier mount-load and
field-name defects are recorded under the diner run.

## The US10 order-list filters as built (Task 10)

**All / Current / Past on the existing Order List — no new history page.**
The two reused screens are the Order List (`/diner/orders`) and the Order
Detail (`/diner/orders/:orderId`): the list gains a three-button filter
group mapping All/Current/Past to the server's `view=all|current|history`
(All is the default), and the detail screen already renders terminal
orders read-only with their notices, so a past order simply re-uses the
tracking screen in its terminal form. All and Current keep the 3-second
polling (vendor moves can appear at any time; the server recomputes the
lists from current statuses); **Past never polls** — terminal orders
cannot change — and the explicit Refresh re-loads whichever view is
selected. Empty states are per-view: "You have no orders yet." (All, with
the Browse open stalls link), "No orders in progress right now."
(Current) and "No past orders yet." (Past).

## Live verification — US10 run (7 October 2026)

`task10_ui_check.py` (Playwright, two logged-in UI contexts — diner.one
with the seeded mixed statuses across both stalls, and diner.empty with
no orders at all; a vendor API call reprices M1 under an open order detail
to prove snapshot stability; the script re-seeds at start and ends with
cleanup-independent reseed + invariant check) passed **all 15 checks on
two consecutive runs**, each ending with `invariant: True False 650 True
True 9 2 2`. The run covered: All listing exactly the 8 own orders across
all six statuses while another diner's order stayed out of the list;
newest-first ordering (Q-seed-0009 before Q-seed-0003); Current showing
only the 5 live orders; a windowed request count proving Current keeps
polling (2+ requests in 8 s) while Past does not (exactly 1 in 8 s — the
measurement uses a timed window, a deliberate measurement rather than a
condition wait); a past Collected order read-only with its stale
snapshot ("Grilled Chicken Rice" at $6.00); a past Cancelled order still
showing its $2.50 refund; an in-progress order keeping its $13.00
snapshot total after the menu item was live-repriced to $7.00; the
explicit Refresh re-requesting the selected view; and the three friendly
empty states on the order-free diner.

This verification found and fixed one genuine UI defect: switching the
filter to Past left the Current list on screen (the polling hook returns
early for the non-polling view, so the switch had no load); a one-shot
effect now loads the Past view when the filter moves there, and one load
per filter transition holds in both directions.

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

Task 9 (vendor flow, two logged-in contexts):

| File | What it shows |
|---|---|
| task9-01-vendor-menu-open.png | Vendor login lands on the own menu: stall name, Open badge, 3 active items, seeded Pineapple Tart badged Sold out |
| task9-02-closed-banner.png | After the switch: Closed badge and the closure banner (new orders refused, paid queue stays accessible) |
| task9-03-diner-closed-stall.png | The diner's direct-link view of the closed stall: closure notice, every Add control disabled |
| task9-04-form-rejection.png | The create form showing the backend's own 400 message for a malformed price |
| task9-05-item-created.png | The run-created item listed with its $9.99 price and the success banner |
| task9-06-item-edited.png | The renamed/repriced item ($10.50) after the edit form saved |
| task9-07-m2-sold-out.png | A seeded item marked sold out from its row control (badge + success banner) |
| task9-08-orders-queue.png | The paid queue: 8 own-stall orders newest-first, other-stall order absent, status badges |
| task9-09-pending-controls.png | A Pending order: exactly Accept order / Reject order |
| task9-10-preparing-controls.png | A Preparing order: exactly Mark ready (rejection no longer offered) |
| task9-11-ready-no-noshow.png | Ready +5 min: Mark collected only — the NoShow control is still hidden |
| task9-12-ready-with-noshow.png | Ready +35 min: both Mark collected and Mark no-show are offered |
| task9-13-terminal-cancelled.png | Cancelled order: read-only, "This order is final", refund shown with time |
| task9-14-terminal-noshow.png | NoShow order: read-only, payment-stays-paid notice |
| task9-15-terminal-collected-snapshot.png | Collected order: read-only, stale purchase snapshot (Grilled Chicken Rice $6.00) |
| task9-16-forbidden-order.png | Another stall's order: the 403 screen, no order data rendered |
| task9-17-closed-queue-accessible.png | While the stall is closed: closure banner plus the full paid queue with every Manage control enabled |
| task9-18-diner-checkout-success.png | The diner context: the seeded cart ($15.50) paid, fresh queue number shown |
| task9-19-vendor-accepted.png | The vendor detail of the same order after Accept: Preparing badge, success notice |
| task9-20-diner-preparing.png | The diner's tracking page observing Preparing (polling, no manual refresh) |
| task9-21-diner-ready-banner.png | The Ready-for-collection banner on the diner's tracking page after Mark ready |
| task9-22-vendor-collected.png | The vendor detail after Mark collected: terminal, read-only notice |
| task9-23-diner-collected.png | The diner's terminal Collected notice for the same order |
| task9-24-cancel-refund.png | The vendor rejecting the seeded Pending order: Cancelled badge, refund shown |
| task9-25-diner-cancelled.png | The diner's cancellation notice with the refunded $13.00 amount |
| task9-26-vendor-noshow.png | Mark no-show accepted past the 30-minute boundary: NoShow badge, stays-paid notice |
| task9-27-diner-noshow.png | The diner's no-show notice ("The payment stays paid.") |

Task 10 (US10 order-list filters):

| File | What it shows |
|---|---|
| task10-01-orders-all.png | All (default): the diner's 8 own orders across all six statuses, newest-first, another diner's order absent |
| task10-02-orders-current.png | Current filter: only the 5 Pending/Preparing/Ready orders |
| task10-03-orders-past.png | Past filter: exactly the 3 terminal orders, newest-first (this view never polls) |
| task10-04-past-collected-snapshot.png | Read-only past detail: Collected notice, stale snapshot (Grilled Chicken Rice $6.00) |
| task10-05-past-cancelled-refund.png | Read-only past detail: Cancelled notice with the refunded $2.50 and time |
| task10-06-current-snapshot-after-reprice.png | An in-progress order keeping its $13.00 snapshot total after the menu item was live-repriced |
| task10-07-empty-diner-all.png | An order-free diner: "You have no orders yet." with the Browse open stalls link |
| task10-08-empty-diner-past.png | The same diner on Past: "No past orders yet." |
