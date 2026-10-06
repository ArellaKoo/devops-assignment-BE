# SkipQ testing and evidence plan

**Status: assessed feature tests and evidence are planned.** Both repositories now contain lab-adapted startup foundations. Four setup regressions, clean installation/build, MongoDB connectivity and a startup browser smoke have passed, as recorded in [foundation verification](foundation-verification.md). Domain/lifecycle suites, load runs and recordings below are not implemented/executed; their expected results are assertions to verify later, not observed results. These documents are also copied into the backend repository for the build handover.

Sources: ICT381 TMA July 2026, Q2(c), Q4, Q6 and Q7(a); Group 5 GBA, US1–US8, US10, US12 and the sign-in/ownership portion of US16; `docs/superpowers/specs/2026-10-06-skipq-design.md`. The GBA's acceptance criteria appear under Q2(b), although the TMA calls them Q2(c). Within each story, `AC1`, `AC2`, etc. below mean criteria in their order of appearance in the supplied GBA, not pre-existing numbered IDs.

The proposed assessed capabilities are C1 diner ordering, C2 vendor operation, C3 seeded authentication/roles, and C4 US10 past orders. Order states are `Pending → Preparing → Ready → Collected`, with `Pending → Cancelled` and `Ready → NoShow` after 30 minutes from `ready_at`. Payments are simulated; rejection makes payment `Refunded`, while NoShow remains `Paid`. All/Current/Past filters share `/diner/orders`; historical details reuse the order-detail screen.

## Contract used by the planned assertions

Every response is JSON. Errors use `{"error":{"code":"...","message":"..."}}`; lists use `{"items":[...]}`; order responses use `{"order":{...}}`. Tests assert a stable error code from the design contract and useful message, not an entire prose string. The proposed design fixes the code names and must be reviewed before implementation.

| Outcome | Planned HTTP status and body |
|---|---|
| Successful read, update or soft delete | `200`, relevant JSON data |
| Newly added cart line/menu item/new paid order | `201`, created JSON data; a new order is `Pending` with `Paid` payment and a queue number |
| Invalid input, price/quantity/type, payment method or `view` | `400`, actionable validation error |
| No token, invalid/expired token, wrong credentials | `401`, authentication error |
| Wrong persona or existing record owned by another diner/stall | `403`, authorization error |
| Well-formed ID for an absent record | `404`, missing-record error |
| Sold-out/inactive item, closed stall, stale price, cross-stall cart, invalid transition or premature NoShow | `409`, actionable conflict; no forbidden mutation |
| Five failed logins and attempts during the 15-minute lock | `429`, lockout message; after expiry valid login is `200` |

Two contract details are audited additions fixed in the proposed design: failed simulated payment returns `409`/`payment_failed` with no order or queue number and the cart retained; replaying a successful checkout key with the same fingerprint returns `200` and the original order/queue number, while conflicting reuse returns `409`/`checkout_key_conflict`. The initial paid creation remains `201`. These choices were not already specified by the GBA and still require user design review.

## Q2(c): seed data and criterion coverage

Use deterministic seed handles and fixed demo credentials, documented in `README.md`. Store password hashes in MongoDB. Proposed public local-demo password: `SkipQDemo2026!`; these are demonstration accounts, never personal credentials. The seed script targets only the configured database, is repeatable, and preserves valid reference relationships. Its README must state whether re-running replaces its own demo records or recreates a dedicated demo database; never silently erase unrelated data.

| Seed handle | Planned records and why they are needed |
|---|---|
| `D1`, `D2`, `D0` | `diner.one@skipq.test`, `diner.two@skipq.test`, `diner.empty@skipq.test`. D1 has current/past orders; D2 has foreign orders to expose ownership leaks; D0 has no orders for the empty state. |
| `V1`, `V1B`, `V2` | `vendor.one@skipq.test` and `vendor.one.backup@skipq.test` reference the same stall S1; `vendor.two@skipq.test` references S2. This tests stall ownership rather than ownership by one vendor user. All login counters start at zero. |
| `S1`, `S2` | S1 open; S2 closed with an existing paid order. A closed stall can remain accessible through its cached/direct menu link and must display closed state, even though open-stall discovery excludes it. |
| `M1`, `M2`, `M3`, `M4` | S1 has two available items priced at 650 and 250 cents, one sold-out item, and one soft-deleted item. Each has a name, description and bundled JPG/PNG image served through a valid image URL. Distinct prices make arithmetic errors visible. |
| `M5` | Available S2 item, so opening S2 enables a cross-stall cart attempt. |
| `C1` | D1 cart: two M1 and one M2, expected total 1,550 cents. D2 has a distinct cart. D0 cart is empty. Unit/functional fixtures use their own copies, not these mutable demo carts. |
| `O-P`, `O-PR`, `O-R`, `O-RO` | D1/S1 paid Pending, Preparing, recently Ready, and Ready for at least 30 minutes orders. Recent/overdue timestamps are calculated relative to seed time; they cannot remain boundary fixtures indefinitely. |
| `O-C`, `O-X`, `O-N` | D1 terminal Collected/Paid, Cancelled/Refunded and NoShow/Paid orders. Distinct creation times and queue numbers establish history and sorting. At least one historical line has an older name/price snapshot than its current MenuItem. |
| `O-F`, `O-S2` | D2's distinct historical order; an existing S2 paid Pending order. They expose diner isolation and show that closing a stall does not erase its queue. |

Criterion-by-criterion argument follows. Shared criteria appear once with both capabilities named. An action is necessary whenever the criterion describes an event or a refusal: a seed record alone is not evidence that a notification, guard or validation works.

| Capability / GBA criterion | Seeded precondition and marker action | Expected result and why the state is sufficient |
|---|---|---|
| C1/C2 US1 AC1: add menu item | V1 can sign in to S1; submit a new valid item. | `201`; reload gives `200` and saved fields. A vendor/stall reference is needed; a pre-existing item would not prove creation. |
| C2 US1 AC2: missing required fields | V1/S1; submit item without name, then without price. | `400`; useful field error and no new item. Invalid records are produced by the action, not seeded. |
| C1/C2 US1 AC3: display menu details | D1 selects open S1 with M1/M2. | `200` menu; images, prices and descriptions appear in the browser. API data alone does not prove rendering. |
| C1/C2 US2 AC1: mark sold out | V1 updates available M1. | `200`, availability false; a fresh read persists it. |
| C1/C2 US2 AC2: restock | V1 updates sold-out M3. | `200`, availability true; a fresh read persists it. |
| C1/C2 US2 AC3: toast on availability change | Keep D1 on S1 menu; V1 marks an initially available item sold out. | A newly observed update produces the toast and greyed-out item. Seeded sold-out M3 proves initial display only; cross-context action produces the notification event. |
| C1/C2 US2 AC4: sold-out checkout | D1 loads checkout from C1; V1 then marks M1 sold out. | Checkout `409` identifies M1; cart remains and no new paid order/queue number exists. Loading checkout first makes this a server stale-data guard test. |
| C2 US3 AC1: valid edit | V1 edits M1 name, price, description and image. | `200`; fresh vendor/diner reads show saved fields. |
| C2 US3 AC2: invalid edit | V1 submits a missing name/invalid price/image. | `400`; error leaves the previous saved item unchanged. No invalid stored fixture is needed. |
| C1 US4 AC1: add/remove | D1 starts with C1 or clears it, then adds/removes available M1/M2. | New line `201`, read/remove `200`; cart lines and total match the remaining quantities. |
| C1 US4 AC2: change quantity | D1 changes M1 quantity in C1 from two to three. | `200`; total becomes 2,200 cents. Updating to zero removes the line; invalid quantities return `400`. |
| C1 US5 AC1: preferred payment method | D1 has available items in open S1; repeat with a fresh order for each supported method. | Valid simulated PayNow/Card/Cashless checkout is `201`; recorded method and amount match the order. No gateway or financial details are used. |
| C1 US5 AC2: success and queue number | Same precondition; choose successful simulation. | `201`, Pending/Paid order, queue number and payment-success screen. No pre-seeded paid order can prove this event. |
| C1 US5 AC3: failure and retry | Same precondition; choose failed simulation, then successful retry. | Proposed failure `409`, no order/queue and unchanged cart; subsequent valid success `201`. Failure message and retry control are checked in the browser. |
| C1 US6 AC1: latest status on refresh | D1 opens O-P; V1 accepts; D1 refreshes. | Status read `200`, Preparing in API and screen. Two actors create the change that the refresh must fetch. |
| C1 US6 AC2: Ready notification | V1 advances O-PR to Ready while D1 tracks it. | Update/read `200`, Ready and browser ready feedback. GBA email delivery is an explicitly narrowed scope item: no email evidence is claimed. |
| C1 US6 AC3: not-ready refresh | D1 refreshes O-P or O-PR. | `200`, actual Pending/Preparing state, queue number and no Ready indication. |
| C1 US6 AC4: collected refresh | D1 reads O-C, and separately refreshes a newly collected order. | `200`, Collected. The seeded record proves display; the transition action proves refresh sees a change. |
| C2 US7 AC1: incoming paid order | V1 reads O-P and then refreshes after D1 places a fresh order. | `200` list/detail contains order/queue number, item names and quantities; new order appears. Failed payment never enters this list. |
| C2 US7 AC2: accept | V1 accepts O-P. | `200`, Preparing. |
| C2 US7 AC3: reject/refund | V1 rejects a separate O-P copy. | `200`, Cancelled and payment Refunded; D1 read agrees. Refund is simulated. |
| C2 US7 AC4: ready | V1 marks O-PR Ready. | `200`, Ready with `ready_at`; D1 sees ready feedback. |
| C2 US7 AC5: collected | V1 collects O-R. | `200`, Collected. Audit explicitly replaces this criterion's inconsistent “Completed” label with GBA Q4/Q5's Collected. |
| C2 US7 AC6: NoShow | V1 acts on O-RO and tries premature action on O-R. | Overdue `200`, NoShow/Paid; premature `409` and Ready unchanged. Exact 30-minute boundary uses an injected clock in unit tests rather than waiting. |
| C3 US8 AC1: vendor valid login | Sign in using V1 credentials. | Token `200`; UI opens own vendor menu/admin screen and displays S1. V1B separately confirms shared-stall access. |
| C3 US8 AC2: vendor invalid login | Submit a wrong password for V1. | `401`; helpful message and retry option. Reset counters through fixtures before lockout testing. |
| C2 US12 AC1: open stall | V2 opens S2. | Update `200`, is_open true; discovery includes S2 and valid checkout can create an order. |
| C2 US12 AC2: close stall | V1 closes S1. | Update `200`, is_open false; new checkout is refused `409`. |
| C1/C2 US12 AC3: show closed | D1 visits S2 through a direct/cached menu link. | Menu `200` carries closed state; browser shows Closed and excludes the stall from open discovery. |
| C1/C2 US12 AC4: prevent closed checkout | D1 loads a valid S1 checkout before V1 closes S1. | `409`, closed-stall message; no new order/queue and cart retained. S2 seeded closed also proves a direct attempt is refused. |
| C2 US12 AC5: preserve paid queue | V2 reads O-S2 while S2 is closed, then processes it. | List `200` still includes it; valid lifecycle updates remain `200`. |
| C3 US16 AC3: diner valid login | Sign in using D1 credentials. | Token `200`; UI opens diner stall list. |
| C3 US16 AC4: diner invalid login | Submit a wrong password for D1. | `401`; access denied and useful error. |
| C3 US16 AC5: own cart/orders/history | D1/D2 distinct carts and orders; sign in separately, then request another diner's existing order. | Lists/cart `200` include only own records; direct foreign order read `403`. Authentication and owner filters are both necessary. |
| C4 US10 AC1: all current/past own orders | D1 reads `view=all`, then scrolls the Order List; compare current/history filters. | `200` All includes O-P/O-PR/O-R/O-RO and O-C/O-X/O-N, excludes O-F; current/history partition it. Browser can reach the oldest order. |

US16 AC1/AC2 registration is outside this TMA's seeded-login baseline and is not claimed as covered. Record this scope adaptation in C3's Q1 audit. Generated email delivery and real payment processing are likewise not seedable evidence of the proposed build. Validate added criteria too: D0 empty history, D2 isolation, menu snapshot edits/removal, duplicate checkout, token expiry/lockout, forbidden lifecycle transitions and invalid input require the actions described below.

## Q4(a): unit tests and honest mock boundaries

Planned files: `tests/unit/test_order_guard.py`, `test_cart.py`, `test_validation.py`, `test_auth_rules.py`. Every test has a behaviour-focused GIVEN/WHEN/THEN docstring. Names below are proposed method/test seams, not existing code. Unit fixtures supply actor, stall, menu and order records and an injected clock; they do not connect, seed or query MongoDB. Mock only record retrieval and persistence at their narrow boundaries. Calling the real guard/validation/calculation is essential.

| Logic executed for real | Planned allow/refuse coverage |
|---|---|
| `Order.transition_to(actor, target, now)` with persistence mocked | Every canonical allowed edge; all other state pairs including backwards, skips, same-state and terminal mutations; wrong vendor/diner actor; Ready-to-NoShow at 29:59, exactly 30:00 and 30:01; missing `ready_at`; Cancelled/Refunded and NoShow/Paid consistency. |
| Menu validation | Name trimmed/nonblank, lengths 1/80/81; description 500/501; prices 0, negative, valid 0.01/9998.99, 9999, >2 decimals and nonnumeric values; JPG/JPEG/PNG URL/query suffix and invalid scheme/format; valid versus missing required fields. |
| Cart quantity and cents arithmetic | One/multiple lines, quantity one/positive/zero removal, negative/fraction/string/bool refusal, total 1,550 then 2,200 cents, no float rounding, empty checkout, available/inactive/sold-out item, open/closed stall and one-stall rule using supplied records. |
| Checkout decisions | Fresh versus stale fingerprint, client total cannot override server cents, failed payment yields no save/queue, same-key replay versus conflicting key, successful receipt fields and preservation of purchase snapshots. Simulate cart-clear failure after order save and require confirmation/retry to use the saved order. A mocked lookup can prove the branch decision, not the unique database constraint or atomic persistence. |
| Authentication/ownership decisions | Normalized email, real password verification, wrong role/owner/stall, lock threshold and expiry with injected clock, real token signature/expiry verification using test-only configuration. No production secret is required. |

Proposed report distinction, to write only after inspecting actual tests: `test_guard_rejects_pending_to_collected` calls the real `Order.transition_to` with supplied records and only its persistence mocked, so the fake cannot choose the guard's answer. By contrast, mocking `Order.list_for_diner`'s MongoEngine query to return a prepared list cannot prove MongoDB actually filters by diner or orders records correctly; omit a pretend isolation test at that boundary and prove it through real-database API evidence. A fake `save()` likewise cannot establish uniqueness or durability.

Planned verification: run all of `tests/unit/` with MongoDB stopped or inaccessible and without a database setup fixture. Patch unintended query/save access to raise, so accidental I/O fails immediately. Retain actual output showing the complete unit suite passes only after it does. Delete/adapt all Staycation tests and remove the lab `tests/selenium/`; no frontend unit/component suite is planned.

## Q4(b): repeatable real-database API lifecycle

Planned artifacts: `tests/conftest.py` and `tests/functional/test_order_lifecycle.py`. Function-scoped fixtures create a small, isolated set of real MongoEngine documents in configured `skipq_test`, with unique run identifiers, zero login-failure counts, open stall and available items. A function-scoped application fixture passes host/name through `create_app(config)`; a Flask client uses that application. A guard refuses a non-test database name before initialization/cleanup. Teardown removes only fixture-owned records in dependency order, then disconnects the global MongoEngine alias; no development-database drop or live connection retargeting is allowed. Failed tests still run finalizers, and the next run uses fresh identifiers so an interrupted run cannot cause collisions. Keep app fixtures lazy and separate from the offline unit fixture.

| Step in one planned lifecycle test | Request / required assertion |
|---|---|
| Both personas authenticate | Diner and vendor each call `POST /api/user/gettoken` with their own seeded fixture credentials; both `200`, separate valid tokens and correct roles. Do not manufacture tokens or log in by patching auth. |
| Diner selects and orders | GET stalls/menu `200`; POST cart item `201`; GET cart `200`, correct cents total; POST order with successful simulation, fresh key and current fingerprint `201`, state Pending, payment Paid, amount/method and nonempty queue number. Capture this order's ID/queue. |
| Vendor finds the same paid order | GET vendor orders/detail `200`, same ID/queue/items/quantity and Pending. |
| Vendor accepts | PATCH own order status to Preparing `200`, body Preparing; diner GET same order `200`, Preparing. |
| Vendor marks ready | PATCH Ready `200`, body Ready and `ready_at`; diner GET `200`, Ready. |
| Vendor confirms pickup | PATCH Collected `200`, body Collected; diner GET `200`, Collected, unchanged queue/total/items and Paid payment. |

Assert status and response state after **every** transition, not just collection. Fresh reads demonstrate persistence rather than merely echoing the request. Run `pytest -q tests/functional/` twice consecutively against the same configured test database, retain each complete run's actual output, and confirm no fixture-owned leftovers. The planned extra-story cases in Q4(c) must remain unimplemented; they are not smuggled into this lifecycle test as a history test suite.

A small implemented refusal/integration suite may separately check cross-diner/cross-stall `403`, sold-out/closed/stale checkout `409`, failed payment and idempotent replay. The real database is necessary to prove persisted scoping, duplicate-key uniqueness and unchanged records; unit fakes cannot establish these. For a true duplicate-race claim, two concurrent same-key submissions must yield exactly one stored order and one queue number; sequential retries establish only retry behaviour. Include a concurrency test only if that claim is made.

Planned Q4(b) write-up points: the complete authenticated client sequence will exercise Blueprint selection, JSON parsing, role checks, guard calls and response serialization together, which isolated rule tests do not. Reading the same order through separate persona tokens after each update will establish real MongoDB persistence and actor scope, whereas the unit suite explicitly replaces record access. Express these as findings only when the named test and results support them.

## Q4(c): US10 functional cases — design only

**Do not implement this table as a test suite.** Preconditions use the demo handles or equivalent isolated real-database fixtures; each persona obtains a token through `POST /api/user/gettoken` (`200`) unless authentication failure is the point of the case. `view=all|current|history` maps to UI All/Current/Past. Original US10's scroll requirement needs browser evidence as well as an API list.

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

**Strategy (planned report paragraph).** Start with US10's one original criterion and cover its data completeness, both current and terminal states, actor ownership and the scrolling interaction. Expand the under-specified edges explicitly in Q1: empty results, newest-first order, terminal membership, immutable purchase details, read-only access and errors. H01/H02/H11 account for the original criterion; H03–H10 cover those audited additions. This supports coverage of the declared story and additions, rather than a claim that every conceivable defect has been tested.

**Priority (planned report paragraph).** Write H01 first to establish the central value, then H04/H05 for privacy, H03 for truthful purchase history, and H02/H08 for filter membership and lifecycle persistence. H06/H07/H09 follow for empty/sort/error behaviour; H10 confirms immutability, and H11 exercises the remaining UI-only claims after screens exist. Security and preservation of purchase facts come before presentation refinements. These are a hypothetical implementation order only: Q4(c) requests design, not implementation.

## Q6(a): browser lifecycle and evidence

Planned location: `tests/playwright/test_order_lifecycle.py` in the backend, with planned command `pytest -q tests/playwright/ --browser chromium` and required running-app setup in the backend README. Use configured `skipq_system_test`, seeded credentials and a fresh order on every run. Maintain **two browser contexts**, each with its own login/sessionStorage state; sign both personas in through `/login` and clear leftover diner cart lines through the UI before adding this run's item. Seeding/setup can prepare accounts/menu, but order placement and every vendor lifecycle action must happen through UI controls.

Planned assertions: diner sees open stall, menu, correct cart total and selected payment method; placement displays queue number and Pending/Paid. Vendor finds that exact queue/order and displays Pending, then Preparing after Accept, Ready after Ready, and Collected after pickup confirmation. Diner's screen must display the corresponding state after each vendor action, with the same queue number and purchase details. Use `expect(locator)` condition waits, precise role/text locators and the captured queue number; never `time.sleep`/`wait_for_timeout`. Allow polling time with a condition timeout rather than asserting an unmeasured five-second guarantee.

Run the browser lifecycle twice consecutively against the same seeded database, without reseeding between them. Fresh order/key per run prevents collisions; the vendor locates its captured queue rather than “first order”. Stop polling on unmount and retain only intended seed plus clearly identified run-owned records; planned cleanup must not remove another run's data. Save actual complete outputs, screenshots at Pending/Preparing/Ready/Collected, and trace/screenshot on failure. Artifacts must be labelled with run time, commit and database; retain real failures rather than replacing them with staged passing images.

The eventual three-to-four-sentence Q6(a) finding must name browser steps: UI sign-in creates usable bearer sessions; cart/payment controls call the API with the expected values; vendor actions and diner polling/refresh display each persisted state across separate browser contexts. Q4(b)'s Flask client cannot establish React routing, DOM feedback, browser session separation or the page's polling behaviour. Record a five-second update claim only if actual vendor-action and diner-observation timestamps support it.

## Q6(b): local load and database analysis

Planned frequent endpoint: `GET /api/diner/stalls/<S1-id>/menu`. The choice is a hypothesis grounded in Q5: diners browse menus before purchase, and active menu views poll every three seconds to detect availability. Use only this menu endpoint as the measured Locust task; obtain seeded diner tokens during setup, avoid repeated login in the load loop, and group its path under a stable request name. Authentication requests/warm-up must be distinguished from the cited menu results.

Planned files: `tests/stress/locustfile.py`; actual CSV or HTML under `q6-performance/`. Begin with 5 users, spawn 1 user/second, 60-second measured duration and pacing near the designed three-second polling cadence. If the machine can sustain it, a second 10-user/2-per-second/120-second run is optional. Record the load actually used; larger load earns no extra marks. Run browser tests and load measurements separately. Use local application server without reloader, record server mode, and do not interpret local measurements as production capacity.

| Evidence to capture later | What it would establish / limit |
|---|---|
| Run metadata | Date/time, backend/frontend commits, OS/CPU/RAM, Python/MongoDB/Locust versions, seed/menu count, database name, server mode, users, spawn rate, pacing, warm-up and measured duration. These define the experiment actually performed. |
| Locust output | Menu request count, failures/statuses, requests/second, median/p95/p99 and maximum latency. Verify `200` body shape as well as status so fast errors are not counted as valid menu success. |
| Request-stage timing | Correlate total server request time with stall lookup, `MenuItem.list_for_vendor` query **execution/materialization**, and serialization. Timing only construction of MongoEngine's lazy QuerySet does not time database work. |
| Database-side observation where available | A time-bounded local profiler/query-duration sample or equivalent diagnostic output for the cited menu queries, plus application/MongoDB process CPU observations. Use only the local test database and restore any temporary profiling setting. Omit unavailable measurements and explain the remaining uncertainty. |
| Comparison and limits | Compare stage durations/distributions from the same load window. Model elapsed time also includes driver wait and document hydration, so a large model duration alone does not prove server-side database execution is the bottleneck. Local client/server contention and logging overhead may remain confounders. |

The eventual verdict is **at most 100 words**, naming `MenuItem` and the actual `list_for_vendor` implementation. Structure it around measured total latency, materialized model/query time, serialization/other time, and any database-side observation; say what those support and what they cannot distinguish. An evidenced “inconclusive” is valid. Locust percentiles alone do not establish a database bottleneck. Q6(b) asks for analysis, so do not spend the answer proposing indexes or query rewrites. No figures or verdict are available yet.

## Q7(a): planned screencast, including stale sold-out refusal

Target 6–7 minutes, maximum 8; narrated MP4, 720p. Use two visible signed-in browser contexts/tabs and known demo records. Start recording from a prepared app state; any cut to startup/seeding waits is disclosed on screen. Preserve errors and retries honestly. The final same-order lifecycle demonstration must identify its queue number in both persona views.

| Approximate segment | Planned demonstration |
|---|---|
| 0:00–1:20 | Identify roles and simulation; diner UI sign-in, open-stall/menu browse, add available item, quantity/total and reach checkout. |
| 1:20–2:30 | **Sold-out violation:** while diner remains on the already-loaded checkout page, vendor UI sign-in and mark that cart item sold out. Say: “This cart was loaded while the item was available. I expect checkout to refuse the now sold-out item and create no order.” Return to diner and click Place order; show actionable item-specific refusal and retained cart. Expected API result `409`; capture network/result evidence separately if useful. A greyed-out menu button alone does not demonstrate stale checkout refusal. |
| 2:30–3:20 | Restock through vendor UI. **Second violation, closed stall:** keep a valid loaded checkout, vendor closes S1; narrate the closed-stall rule and expected refusal, then attempt placement and show closed-stall error (`409`), retained cart and no new queue. Reopen S1. |
| 3:20–4:20 | Diner successfully places the order with simulated method; show Pending/Paid and queue number. |
| 4:20–6:00 | Vendor locates the **same** order and accepts, marks Ready, then Collected; show each vendor state and diner state after the action, using Refresh/polling as implemented. |
| 6:00–6:40 | Optional US10 evidence: All/Current/Past on existing Order List, now-past Collected order and unchanged historical detail. |

The stale sold-out scene needs no artificial API bypass: design polls active menus/order views, and the diner is held at checkout with its prior fingerprint. During implementation, confirm that checkout still permits the attempt when its loaded data becomes stale. If checkout refresh automatically detects and disables submission, prepare a reproducible stale interval or show the application's visible refusal and an accompanying functional `409` test; do not pretend a disabled button produced a server rejection. Do not pause the video to hide polling races or failed attempts.

Planned delivery: backend `q7-screencast/skipq-demo.mp4`, linked from both repository READMEs and Canvas. Measure size after recording; if over 100 MB, use an accessible permitted external link and verify playback outside the owner's account. Check actual playback/audio/access before claiming the deliverable exists.

## Q1 audit additions surfaced by testing

Carry these to the **Acceptance criteria** row for the named capability, with an explicit expected outcome; retain related entity/state/screen gaps in their appropriate rows. They are proposed additions, not wording attributed to the original GBA.

| Capability | Missing/sharpened acceptance outcome to record |
|---|---|
| C1 | Empty checkout refused; positive integer quantity/type rules and zero-removal; one-stall cart; server-derived cents total; changed price/fingerprint requires review (`409`); sold-out/inactive/closed checks use current records at checkout; payment failure creates no order/queue and preserves cart; same-key retry returns original order, conflicting reuse refused; cart-clear failure preserves the saved order and retry confirmation; purchased name/price snapshots survive menu edit/remove. |
| C2 | Exact canonical transitions and refusal of skips/backwards/repeats/terminal edits; replace Completed/No-Show variants with Collected/NoShow; define no-show clock origin at `ready_at` and the inclusive 30-minute boundary; Cancelled means simulated Refunded while NoShow stays Paid; closing blocks new orders but preserves paid queue and processing; only own stall may be managed; soft deletion retains historical references. |
| C3 | Seeded sign-in replaces US16 registration; absent/invalid/expired token `401`, wrong role and foreign record `403`; no leaked data in errors; normalized email; failures 1–4 return `401`, failure 5 and locked attempts `429`, 15-minute lock and unlock/reset behaviour; tokens expire after 3,600 seconds; shared-stall vendor accounts authorize by stall relationship. |
| C4 | All/Current/Past on existing Order List with All default; Past consists of Collected/Cancelled/NoShow; complete own-only lists, empty `200` collection, newest-first sort and equal-time tie-breaker; immutable historical purchase/payment details and read-only detail; absent `404` versus foreign `403`; scrolling oldest entry and friendly empty screen verified through browser, not API. |
| C1/C2 notification scope | Retain browser Ready feedback and sold-out toast, with explicit action-based evidence; no actual email notification is claimed. Clarify the local five-second update measurement independently of a condition-waiting lifecycle test. |

## Planned evidence ledger and completion gate

| Question | Planned repository artifact | Planned report evidence |
|---|---|---|
| Q2(c) | `db_seed/`, README credentials/setup | Criterion-to-record/action coverage table; honest unsupported/narrowed criteria |
| Q4(a) | `tests/unit/` and actual full offline run output | Two-to-three sentences naming one meaningful mocked-rule test and one DB claim a fake cannot prove |
| Q4(b) | `tests/conftest.py`, `tests/functional/`, two actual consecutive outputs | Three-to-four sentences giving two concrete strengths from this test |
| Q4(c) | This **design** table; no implemented extra-story suite | Exact five-column table plus strategy/priority paragraphs |
| Q6(a) | `tests/playwright/`, README run command, actual two-run outputs/screenshots | Three-to-four sentences grounded in UI steps/screens and the API-test limit |
| Q6(b) | `tests/stress/locustfile.py`, cited CSV/HTML in `q6-performance/`, timing metadata | Endpoint rationale, actual local load/results and ≤100-word grounded database verdict |
| Q7(a) | `q7-screencast/` MP4 or verified accessible link; both READMEs | Playable link, ≤8 minutes, same-order lifecycle and two narrated visible refusals |

Before reporting success, verify from clean backend/frontend checkouts using their READMEs alone, record exact commands and commit IDs, and inspect every generated artifact for authentic content. Include every AI prompt labelled with related question(s), plus the actual verification performed; this testing-plan prompt relates to Q1, Q2(c), Q4, Q6 and Q7(a). At present only requirements/design review and this document have been produced; no passing-test or performance claims are authorized by the available evidence.
