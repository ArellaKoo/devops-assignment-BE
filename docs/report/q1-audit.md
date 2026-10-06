# Q1(a) — Capability audits (living document)

**Group 5 (T02).** This document is maintained during the build and will be
finalised for the report. Each capability gets a Status followed by the
five-row artifact table, citing the GBA by story/criterion/feature/screen
name rather than transcribing it. Gaps discovered at any point are recorded
in the affected row as though always known, with the evidence that
settled them.

The GBA does not number its acceptance criteria; `US7-AC2` means the
second Given/When/Then block under User Story 7 in GBA Q2(b). The TMA's
"Q2(c)" numbering refers to the same criteria; this report cites the story
and block.

## C1: Diner browsing, ordering, and tracking

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Diner US4 adds/changes cart items; US5 pays and receives a queue number; US6 views changing queue/order status. Their happy path covers ordering and tracking. | Limit US6 to baseline status viewing: the TMA requires simulated payment and the build uses in-app Ready feedback, so US5 is described as a simulation and email delivery is not claimed. Open-stall browsing needs the trading-state linkage from US12, which US6's screens do not show. |
| Acceptance criteria | US4-AC1/AC2 cover add/remove/quantity and the updated price; US5-AC2/AC3 distinguish paid confirmation with queue number from failure/retry; US2-AC4 blocks checkout of an item sold out after it was added; US6-AC1/AC3/AC4 cover refresh and terminal display. | Added outcomes the criteria never state: empty cart refused; positive-integer quantity/type rules with zero-removal; one-stall cart; server-derived cents total; a changed price/fingerprint requiring review (`409` price_changed); sold-out/inactive/closed rechecks using current records at checkout; a failed payment creating no order/queue and preserving the cart; the same-key retry returning the original order while conflicting reuse is refused; and purchased name/price snapshots surviving menu edit/removal. The original criteria do not specify these refusals or duplicate handling, so each is asserted as an audited addition. |
| Specification: feature/data/rules/workflow | GBA Q4(a) "Add to cart" names Cart/Diner/item/quantity/unit price/total; "Payment" requires amount = total, no order or queue number before success, and success/failure retry; "Order status & notification" fixes the Pending→Preparing→Ready→Collected workflow. | Money is stored as integer cents and calculated server-side; the method and refusal codes, menu/stall revalidation, and the cart price fingerprint are specified by this build. Line-item purchase snapshots are persisted so history survives menu edits. In-app Ready feedback is the chosen notification channel; actual email is outside the selected scope. |
| Class diagram and state machine | GBA Q6(a) shows Diner→FoodOrder and FoodOrder→OrderedFood/Payment with FoodItem data; Q6(b) shows the payment/accept/preparation/collection concepts. | The diagram lacks the Cart/CartItem entities, the order-to-Vendor reference, the item image URL, the queue number, and the timestamp/price-snapshot fields; building `app/models/` made each gap concrete. Q6's `PendingPayment`, `Accepted`, `PendingPreparation`, `PendingCollection`, `Rejected`, `Stored` and duplicate refund nodes conflict with the paid-before-order rule or duplicate the canonical states, so the build reconciles them to `Pending`, `Preparing`, `Ready`, `Collected`, `Cancelled` (payment Refunded) and `NoShow` (payment stays Paid), with `Stored` dropped as persistence rather than a workflow state. |
| Persona screens | GBA Q5's Diner Home / Vendor / Item Details / Cart / Checkout / Payment Success / Order Tracking screens cover the ordering sequence. | Preorder time and registration are removed from the selected scope. Added: open/closed/sold-out state visible before the action, explicit simulation success/failure with retry, pending-submit feedback, the stale-cart refusal screen, and a readable Ready banner. The Payment Success screen is merged into Order Tracking so the queue number and live status live on one screen; US10's history reuses the Order List/Detail screens (see C4). |

## C2: Vendor menu and order operation

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Vendor US1/US3 create/edit menus; US2 toggles sold out; US7 manages incoming paid orders; US12 opens/closes the stall. | US12 is High in GBA Q3's table but absent from GBA Q4's features and Q7's task list; the TMA baseline explicitly requires open/close, so it is included and the omission recorded here. US17 (capacity pause) is a different story and is not conflated with US12. |
| Acceptance criteria | US1/US3 validate required menu fields; US2-AC1/AC2 sold-out/restock; US7-AC1–AC6 incoming/accept/reject/ready/collect/no-show; US12-AC4/AC5 block new ordering while preserving existing orders. | US7-AC5's "Completed" is corrected to Collected to agree with GBA Q4/Q5; the disallowed-transition, vendor-ownership, and closed-stall existing-order outcomes are added, the no-show clock origin is defined at `ready_at` with the inclusive 30-minute boundary, and "accepting begins Preparing" is stated (US7-AC2 only says the status becomes Preparing). |
| Specification: feature/data/rules/workflow | GBA Q4(a) Menu Management fixes name 1–80, price >0/<9999 with two decimals, description ≤500, JPG/JPEG/PNG images; "Diner's order list" specifies the paid-only queue, rejection/refund and terminal immutability. | Added the explicit `is_open` trading state and open/close operations, paid-order scope restricted to the vendor's stall, the simulated refund on rejection, NoShow staying paid, soft-deletion for menu removal, the permitted next-action list, and the actionable 400/403/409 mapping with stable error codes. |
| Class diagram and state machine | GBA Q6(a) Vendor→Menu→FoodItem and FoodOrder/OrderedFood; Q6(b) shows rejection/refund and the 30-minute no-show concept. | The diagram does not distinguish a vendor account from the stall; the build models the stall (`Vendor` document) plus accounts that reference it, so several accounts can manage one stall. Added the Order→Vendor reference, the trading state, the `ready_at` timestamp, and the payment method/amount. The canonical reject is Order Cancelled plus Payment Refunded; `Stored` is persistence, not a lifecycle state, and the duplicate refund nodes are not two distinct states. |
| Persona screens | GBA Q5's Vendor Admin / Item Details / Diner's Order / Order Details screens include menu edits and the accept/reject/ready/collect/no-show controls. | Added the open/close switch and closed banner, current-state permitted controls (only the allowed next statuses are offered), the paid queue staying accessible after closure, and the refund/early-no-show/refused-transition displays. Business-insights and profile editing (US11) are outside the selected scope. |

## C3: Authentication and roles

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Vendor US8 signs in and edits only its own stall; Diner US16 signs in and accesses its own cart/orders. | Seeded account sign-in is the TMA baseline, so US16's registration side is adapted rather than built: the adaptation (seeded sign-in replaces registration/user administration, per TMA Q5) is stated instead of claiming full registration coverage. |
| Acceptance criteria | US8-AC1/AC2 correct/incorrect vendor login; US16-AC3/AC4 login outcomes and AC5 own-data visibility. | Added the outcomes the criteria omit: missing/invalid/expired token `401`, wrong role `403`, and foreign record `403` with no mutation or data leak; email normalisation; and the lock/unlock behaviour (failures 1–4 `401`, fifth failure locks 15 minutes and returns `429`, attempts while locked `429`, reset at expiry or on success). The GBA says "locked after 5 attempts" without a duration or unlock mechanism, so both are audited additions. |
| Specification: feature/data/rules/workflow | GBA Q4(a) User authentication: email/password/vendor_id, unique email, hashed credentials, correct-role redirect, lock after five failures; a vendor_id may have many users. | Specified signed expiring tokens (3,600 s) from the configured secret, model-owned scope checks, and a credential-free example config. The 15-minute lock and `429` while locked are set because the original lock has no unlock mechanism. The GBA's production HTTPS/uptime claims are not claimed by this locally hosted build. |
| Class diagram and state machine | GBA Q6(a) abstract User with email/password and Diner/Vendor specialisation. | Store the password hash rather than the raw password; model one `User` document with a role plus optional `Vendor` reference so several accounts can share a stall, and add the failure-count/locked-until fields. Authentication events are not fulfillment states. |
| Persona screens | GBA Q5's shared Login and Diner-only Registration screens distinguish personas. | Keep the seeded Login only; add the role redirect, protected navigation, shared token-expiry feedback, and logout. UI route gating is usability; the server remains the security boundary. |

## C4: Extra story US10 — current and past orders

**Status: partially supported.**

**Reason for choice (TMA Step 3):** US10 is a Medium-priority GBA Q3 backlog
story outside the baseline order-status tracking. It adds historical
visibility using the orders the build already stores and the Order List and
Order Detail screens the baseline already needs, so it reuses
functionality instead of adding multi-stall payment or analytics
complexity. It was chosen as the one story beyond the baseline, and its
selection is approved for this build.

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User story: ID/text/persona | US10: "As a diner, I want to be able to view my past orders, so that I can know what I have ordered previously." US16-AC5 supplies the ownership intent (only that diner's information is displayed). | Treat past-order visibility as the extra capability, distinct from the mandatory tracking of a new order (US6). Reorder and analytics are not requested by the story and are not added. |
| Acceptance criteria | US10-AC1 says the Order List page shows all current and past orders when scrolled. | Added the outcomes the single criterion cannot determine: All default plus Current/Past filters, empty results, only-own orders, newest-first sort with an equal-time tie-breaker, read-only historical detail, and unchanged purchase snapshots. Each is asserted as an audited addition. |
| Specification: feature/data/rules/workflow | GBA Q4(a) authentication mentions individual history; the order features list Order ID/items/quantity/status/payment, but Q4 has no history feature. | Added the explicit query contract: `view=all|current|history` (invalid view `400`), Past = Collected/Cancelled/NoShow, empty list `200` with `items: []`, owner filtering inside the model, and newest-first by `created_at` with id tie-breaker. The immutable name/unit-price snapshots make history trustworthy after menu edits or removals. |
| Class diagram and state machine | GBA Q6(a) Diner creates zero/many FoodOrders with date/time, cost and OrderedFood quantity/subtotal; Q6(b) mentions terminal orders and `Stored`. | Orders are kept in the database after Collected/Cancelled/NoShow without a `Stored` workflow state or a yearly deletion job (retention scope: the local build keeps them). Added the immutable purchased name/unit-price snapshots and the own-diner reference the diagram lacks. |
| Persona screens | GBA Q5's Order List Page lists current and past orders with statuses. | One list with All/Current/Past and a readable empty state; the Order Detail screen is reused for read-only past details, so no separate history page is built. Multi-stall cancellation actions are removed because multi-stall and diner-cancel-anytime are out of scope and conflict with the vendor's preparation rules. |

## Audit maintenance log

| Date | Capability | Discovered gap | Decision and evidence |
|---|---|---|---|
| 2026-10-07 | C1/C2 | GBA Q6 class diagram has no Cart/CartItem, queue number, image URL, trading state, order→vendor link, or price snapshots | Modelled each explicitly in `app/models/`; seed order O-C keeps an older name/price snapshot to prove the point (see seed-coverage.md). |
| 2026-10-07 | C2 | US12 open/close is High in GBA Q3 but missing from GBA Q4/Q7 | Included in scope per TMA baseline; recorded here and in the C2 story row. |
| 2026-10-07 | C2 | US7-AC5 says "Completed" while Q4/Q5 use Collected | Canonical terminal state is Collected; recorded in the C2 criteria row. |
| 2026-10-07 | C3 | GBA lock rule has no duration or unlock mechanism | 15-minute lock, `429` while locked, reset at expiry/success; implemented in `User.authenticate` and unit-tested with an injected clock. |
| 2026-10-07 | C4 | US10's single criterion cannot determine filters/sorting/ownership outcomes | Added All/Current/Past contract, empty/sort/ownership outcomes; designed (not implemented) as Q4(c) cases. |
| 2026-10-07 | C3 | Token lifetime needs an explicit boundary rule and live proof | `app/auth.py` `verify_token` accepts exactly 3,600 s (inclusive) and refuses 3,601 s/future-dated tokens (unit, injected clock). Live `POST /api/user/gettoken` verified 200/400/401/429 on the dev API, including the 5-attempt lockout on a throwaway account; protected-route 401/403 over HTTP verified live in Task 4 (missing/garbage/expired token 401, wrong persona 403). See docs/report/q3-roles.md. |
| 2026-10-07 | C1/C2 | Malformed ids in URLs must be 404s, not 500s, and the model `get()` seams misused MongoEngine's `with_id` (which returns the document, not a queryset) | `Vendor.get`/`MenuItem.get`/`Order.get` now treat malformed ids as missing (unit + live 404 checks); patching/deleting a cart line that is not present returns 404, and closed stalls stay reachable by direct link while new cart adds are refused 409 (unit + live two-persona checks, 7 October). |
