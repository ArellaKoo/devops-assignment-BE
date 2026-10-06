# Q4(c) — US10 functional cases (design only)

**Status: designed, not implemented.** The TMA asks for these extra-story
cases to be *designed* and prioritised, not written or run; this table and
the two paragraphs below are the deliverable. The US10 screens themselves
(All/Current/Past on the existing Order List, read-only past detail on the
existing Order Detail screen) are implemented and were verified live in
Task 10 — that verification is ordinary task evidence, not this designed
suite.

**Preconditions and conventions.** Preconditions use the demo handles or
equivalent isolated real-database fixtures; each persona obtains a token
through `POST /api/user/gettoken` (`200`) unless the authentication
failure is the point of the case. `view=all|current|history` maps to the
UI's All/Current/Past filters. The original US10 scroll requirement needs
browser evidence as well as an API list (H11).

| Test case ID | Test case - a short label | What passing it would prove | Persona, and the sequence of endpoints it calls | Expected outcome - the status code, and the state or message the response carries |
|---|---|---|---|---|
| H01 | All own orders | Original US10 AC covers both current and past orders, including every supported state, without another diner's orders. | D1 login → GET `/api/diner/orders?view=all`. | `200`; own Pending/Preparing/Ready/Collected/Cancelled/NoShow records present; O-F absent; IDs unique, queue numbers and statuses present. |
| H02 | Current/Past partition | Filtered views account for all orders without losing or duplicating one between groups. | D1 login → GET same list with `view=all`, `view=current`, then `view=history`. | All `200`; Current only Pending/Preparing/Ready; Past only Collected/Cancelled/NoShow; sets disjoint and their union equals All. |
| H03 | Purchase snapshots survive edits | Historical item names, unit prices, quantities, totals and payment details reflect the purchase after vendor rename/reprice/remove. | D1 login → GET historical O-C detail; V1 login → PATCH linked `/api/vendor/menu/<id>` → DELETE same item; D1 GET O-C detail again. | Reads/updates/soft delete all `200`; historical snapshot and total/payment/queue unchanged; purchase remains readable after soft deletion. |
| H04 | Another diner's history | Both collection queries and direct detail access enforce ownership. | D1/D2 log in separately → each GET `view=all`/`history` → D1 GET `/api/diner/orders/<O-F-id>`. | Lists `200` contain only actor-owned records; foreign existing detail `403`, useful authorization error and no order details. |
| H05 | Authentication and role | History cannot be accessed anonymously, with invalid/expired tokens, or by a vendor persona. | GET list and own detail with no/invalid/expired token; V1 login → same GETs. | Each absent/invalid/expired token request `401`; each vendor request `403`. No orders or payment fields leak in errors. |
| H06 | Empty history | A legitimate diner with no prior orders receives an ordinary empty collection. | D0 login → GET `view=all`, `current`, `history`. | All `200`, `items: []`. Friendly empty-screen copy needs the browser check in H11; the API cannot prove it. |
| H07 | Newest first | Order lists follow the audited newest-first rule and remain stable across repeated reads. | D1 login → GET `view=all` and `history`, repeat each. | `200`, descending `created_at`, then ID descending for equal-time ties per the proposed design; identical order between repeated unchanged reads. |
| H08 | Completed order becomes past | A newly collected own order remains available and moves from Current to Past. | D1 login/add cart/create order; V1 login → PATCH Preparing → Ready → Collected; D1 GET all/current/history and the captured detail. | Cart create/order create `201`, transitions/list/detail `200`; new order in All/Past, absent Current, detail Collected with original snapshots. This remains a designed case, not an extension to Q4(b)'s implemented suite. |
| H09 | Bad view or absent record | Invalid list input and a genuinely absent order have distinguishable JSON outcomes. | D1 login → GET `view=unexpected` → GET detail with a well-formed nonexistent ID. | Invalid view `400`, validation message; absent detail `404`, missing-order message. Foreign existing IDs remain H04's `403`. |
| H10 | Read-only past detail | Diner cannot mutate a historical order through vendor controls/endpoints. | D1 login → GET O-C detail → PATCH `/api/vendor/orders/<O-C-id>/status`; V1 login → PATCH same terminal order to Preparing; D1 rereads detail. | Detail `200`; diner PATCH `403`; vendor invalid terminal transition `409`; reread `200`, Collected/snapshots unchanged. UI absence of edit controls cannot be proved through API alone. |
| H11 | Scroll and navigation | Original story's oldest entry is actually reachable, and detail/empty states work on the shared Order List/Detail screens. | **Not fully runnable against API.** D1/D0 login and GET list/detail establish data `200`; separately use browser/manual navigation to `/diner/orders`, choose All/Past, scroll to oldest record and open it. | API `200` has complete own list; browser shows all own current/past entries, visible queue/status, oldest row, correct read-only detail and friendly empty state. No separate history page is required. |

## Strategy

US10 contributes one original acceptance criterion — the Order List page
shows all current and past orders when scrolled. The suite starts from
that criterion and covers its data completeness (H01: every supported
state, and no other diner's orders), both halves of its partition (H02:
Current and Past together account for the All set without overlap or
loss), actor ownership (H04: the list queries and the direct detail read
both refuse a foreign diner) and the scrolling interaction itself (H11:
the oldest entry reachable in the real screen, with the friendly empty
states). The single criterion cannot decide the edges, so each audited
addition declared in Q1 gets its own case: H03 and H10 for the immutable
purchase snapshots and read-only past detail, H05 for the token/role
boundary around the whole feature, H06 for the empty collection, H07 for
the newest-first ordering with its equal-time tie-break, H08 for the
lifecycle transition that moves a live order into Past, and H09 for the
two distinct error outcomes (invalid view versus absent record). H01/H02
and H11 answer the original criterion; H03–H10 answer the declared
audited additions. Together they support a coverage claim for the
declared story and its additions — not a claim that every conceivable
defect in the ordering feature has been tested.

## Priority

Write H01 first, because it establishes the story's central value (one
list, both halves, own orders only) and every later case reuses its
setup. Next H04 and H05, because a history feature that leaks another
diner's purchases or serves orders without a valid token is the most
serious failure this feature can have; security and privacy outrank
presentation. Then H03, because the purchase history must be *truthful*
after the vendor edits or removes the underlying menu items — the
snapshot rule is the story's reason to exist. H02 and H08 follow: the
filter partition must be exact, and an order that just finished must
actually move into Past (lifecycle persistence). H06, H07 and H09 cover
the routine behaviours (empty result, stable newest-first ordering,
distinguishable error outcomes), and H10 confirms the read-only
guarantee from the diner's side once the read paths are in place. H11
last: it exercises the remaining UI-only claims (scrolling to the oldest
row, visible queue numbers and statuses, the read-only detail, the
friendly empty screens) and can only be meaningful after the screens
exist. In short: security and the preservation of purchase facts come
before presentation refinements, and the browser-only evidence comes
after the API-level cases. This is a hypothetical implementation order
only — Q4(c) requests the design, not the implementation.
