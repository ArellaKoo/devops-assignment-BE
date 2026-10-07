# Q2(c) — Seeded-data plan and criterion coverage

**Status: implemented and verified.** The seed script is `db_seed/seed.py`
(data in `db_seed/fixtures.json`, run with `python -m db_seed.seed`), and
the seeded credentials are documented in `README.md`. This document argues
the seed's coverage criterion by criterion, as the report needs.

## Seed records and what they establish

All records use deterministic handles; re-running the script upserts the
same records and refreshes time-relative fixtures. It never deletes
unrelated data.

| Handle | Record and why it is needed |
|---|---|
| `D1` / `D2` / `D0` | `diner.one@skipq.test`, `diner.two@skipq.test`, `diner.empty@skipq.test`. D1 owns current and past orders across every lifecycle state; D2 owns foreign orders that expose ownership leaks; D0 has no orders for the empty-state requirement. |
| `V1` / `V1B` / `V2` | `vendor.one@skipq.test` and `vendor.one.backup@skipq.test` both reference stall S1; `vendor.two@skipq.test` references S2. Two accounts on one stall test that vendor authorisation flows through the stall relationship, not one user. All login counters start at zero. |
| `S1` / `S2` | S1 is open; S2 is closed and already carries a paid order. Closed stalls stay reachable through their direct menu link and must display closed state, while open-stall discovery excludes them. |
| `M1` / `M2` / `M3` / `M4` | S1 has two available items priced 6.50 and 2.50, one sold-out item, and one soft-deleted item. Each has a name, description and bundled image served at a valid PNG URL. Distinct prices make arithmetic errors visible. |
| `M5` | Available S2 item, so opening S2 enables a cross-stall cart attempt. |
| `C1` | D1's cart: two M1 and one M2, expected total 1,550 cents. D2 has a distinct cart on S2. D0 has no cart. |
| `O-P`, `O-PR`, `O-R`, `O-RO` | D1/S1 paid orders in Pending, Preparing, recently Ready, and Ready at least 30 minutes. Recent/overdue timestamps are computed relative to seed time, so the two Ready records are always on opposite sides of the no-show boundary at verification time. |
| `O-C`, `O-X`, `O-N` | D1 terminal orders: Collected/Paid, Cancelled/Refunded, NoShow/Paid. O-C's line keeps an older name and unit price than the current menu item, which proves snapshots survive menu edits. Distinct creation times and queue numbers establish history and sorting. |
| `O-F`, `O-S2` | D2's distinct historical order (isolates diner ownership) and an existing S2 paid Pending order (shows closing a stall does not erase its queue). |

## Criterion-by-criterion argument

Shared criteria are listed once with both capabilities named. Where a
criterion describes an event or a refusal, a seed record alone is not
evidence that the notification, guard, or validation works, so the marker
action is stated.

| Capability / GBA criterion | Seeded precondition and marker action | Expected result and why the state is sufficient |
|---|---|---|
| C1/C2 US1 AC1: add menu item | V1 signs in to S1; submits a new valid item. | `201`; reload gives `200` and the saved fields. A vendor/stall reference must exist, but a pre-existing item would not prove creation. |
| C2 US1 AC2: missing required fields | V1/S1; submit an item without a name, then without a price. | `400` with a field-specific error and no new item. Invalid records are produced by the action, not seeded. |
| C1/C2 US1 AC3: display menu details | D1 selects open S1 with M1/M2. | `200` menu; images, prices and descriptions render in the browser. API data alone does not prove rendering. |
| C1/C2 US2 AC1: mark sold out | V1 updates available M1. | `200`, availability false; a fresh read persists it. |
| C1/C2 US2 AC2: restock | V1 updates sold-out M3. | `200`, availability true; a fresh read persists it. |
| C1/C2 US2 AC3: toast on availability change | D1 stays on S1's menu; V1 marks an initially available item sold out. | The newly observed change produces the toast and greyed-out item. Seeded M3 proves initial display only; the cross-context action produces the notification event. |
| C1/C2 US2 AC4: sold-out checkout | D1 loads checkout from C1; V1 then marks M1 sold out. | Checkout `409` names M1; the cart remains and no new paid order or queue number exists. Loading the checkout first makes this a server stale-data guard test. |
| C2 US3 AC1: valid edit | V1 edits M1's name, price, description and image. | `200`; fresh vendor/diner reads show the saved fields. |
| C2 US3 AC2: invalid edit | V1 submits a missing name or invalid price/image. | `400`; the error leaves the previous saved item unchanged. No invalid stored fixture is needed. |
| C1 US4 AC1: add/remove | D1 starts from C1 or clears it, then adds/removes available M1/M2. | New line `201`, read/remove `200`; lines and total match the remaining quantities. |
| C1 US4 AC2: change quantity | D1 changes M1's quantity in C1 from two to three. | `200`; total becomes 2,200 cents. Updating to zero removes the line; invalid quantities return `400`. |
| C1 US5 AC1: preferred payment method | D1 has available items on open S1; repeat with a fresh order per method. | Valid simulated PayNow/Card/Cashless checkout is `201`; recorded method and amount match the order. No gateway or financial details are used. |
| C1 US5 AC2: success and queue number | Same precondition; choose the successful simulation. | `201` with a Pending/Paid order, queue number and payment-success screen. No pre-seeded paid order can prove this event. |
| C1 US5 AC3: failure and retry | Same precondition; choose the failed simulation, then a successful retry. | Failure `409` with no order/queue and an unchanged cart; the subsequent valid success is `201`. The failure message and retry control are checked in the browser. |
| C1 US6 AC1: latest status on refresh | D1 opens O-P; V1 accepts; D1 refreshes. | Status read `200` shows Preparing in the API and on screen. Two actors create the change the refresh must fetch. |
| C1 US6 AC2: Ready notification | V1 advances O-PR to Ready while D1 tracks it. | Update/read `200` shows Ready plus in-app ready feedback. GBA email delivery is an explicitly narrowed scope item; no email evidence is claimed. |
| C1 US6 AC3: not-ready refresh | D1 refreshes O-P or O-PR. | `200` shows the actual Pending/Preparing state, queue number, and no Ready indication. |
| C1 US6 AC4: collected refresh | D1 reads O-C, and separately refreshes a newly collected order. | `200` shows Collected. The seeded record proves display; the transition action proves refresh sees a change. |
| C2 US7 AC1: incoming paid order | V1 reads O-P, then refreshes after D1 places a fresh order. | `200` list/detail contains the order, queue number, item names and quantities; the new order appears. Failed payments never enter this list. |
| C2 US7 AC2: accept | V1 accepts O-P. | `200`, Preparing. |
| C2 US7 AC3: reject/refund | V1 rejects O-P or a fresh S1 Pending order; alternatively V2 rejects its own O-S2. | `200`, Cancelled with payment Refunded; D1's read agrees. The refund is simulated. |
| C2 US7 AC4: ready | V1 marks O-PR Ready. | `200` with `ready_at`; D1 sees ready feedback. |
| C2 US7 AC5: collected | V1 collects O-R. | `200`, Collected. The audit replaces this criterion's inconsistent "Completed" label with Collected, matching GBA Q4/Q5. |
| C2 US7 AC6: NoShow | V1 acts on O-RO and tries the early action on O-R. | Overdue `200` NoShow/Paid; premature `409` with Ready unchanged. The exact 30-minute boundary uses an injected clock in unit tests rather than waiting. |
| C3 US8 AC1: vendor valid login | Sign in with V1's credentials; repeat with V1B. | Token `200`; the UI opens the vendor's own menu screen and displays S1. V1B separately confirms shared-stall access. |
| C3 US8 AC2: vendor invalid login | Submit a wrong password for V1. | `401` with a helpful message and retry option. |
| C2 US12 AC1: open stall | V2 opens S2. | Update `200`, `is_open` true; discovery includes S2 and a valid checkout can create an order. |
| C2 US12 AC2: close stall | V1 closes S1. | Update `200`, `is_open` false; new checkout is refused `409`. |
| C1/C2 US12 AC3: show closed | D1 visits S2 through its direct menu link. | Menu `200` carries closed state; the browser shows Closed and open discovery excludes the stall. |
| C1/C2 US12 AC4: prevent closed checkout | D1 loads a valid S1 checkout before V1 closes S1. | `409` closed-stall message; no new order or queue, cart retained. S2's seeded-closed state also proves a direct attempt is refused. |
| C2 US12 AC5: preserve paid queue | V2 reads O-S2 while S2 is closed, then processes it. | List `200` still includes it; valid lifecycle updates remain `200`. |
| C3 US16 AC3: diner valid login | Sign in with D1's credentials. | Token `200`; the UI opens the diner stall list. |
| C3 US16 AC4: diner invalid login | Submit a wrong password for D1. | `401`; access denied with a useful error. |
| C3 US16 AC5: own cart/orders/history | D1/D2 have distinct carts and orders; sign in separately, then request the other diner's existing order. | Lists/cart `200` include only own records; a direct foreign order read is `403`. Authentication and owner filters are both necessary. |
| C4 US10 AC1: all current/past own orders | D1 reads `view=all`, then compares the current/history filters. | `200`; All includes O-P/O-PR/O-R/O-RO/O-S2 and O-C/O-X/O-N, excludes O-F; current/history partition it. The browser reaches the oldest order. |

## States seeding alone cannot produce

- **Transient invalid input** (bad price strings, over-long names, malformed
  quantities, non-image URLs): produced by submitting the invalid value.
- **Lockout sequence**: five consecutive failed logins; the seed resets all
  counters to zero on every run so the marker can start clean.
- **Duplicate/concurrent checkout races**: require two submissions of the
  same checkout key; the functional and unit suites cover them.
- **Notification events** (sold-out toast, Ready banner): require a second
  actor to change state while the first persona stays on screen.
- **The exact 30-minute boundary**: O-R/O-RO sit on opposite sides relative
  to seed time, but the precise 29:59/30:00/30:01 instants are unit-tested
  with an injected clock.

## Notes for the audit

- US16 AC1/AC2 (registration) is outside this TMA's seeded-login baseline
  and is recorded as a C3 scope adaptation in Q1, not as covered seed data.
- Email delivery and real payment processing are not seedable evidence of
  this build; both are explicitly narrowed in Q1.
- The GBA's PaymentMethod is represented by the typed payment-method choice
  on the embedded `Payment`; saved payment instruments are out of scope.
