# Frontend assessment review — 7 October 2026

User request: “can you help me to ensure the frontend is up tonstandard so i will not lose point due to it”.

The original TMA Q5 awards 9 marks for route/shared-decision architecture and 11 for the four implemented flows. It explicitly excludes presentation fidelity and frontend unit/component tests. This review checks the existing approved design against those requirements; a marker's score is not guaranteed.

## Requirement-to-proof review

| Requirement | Current implementation and proof |
|---|---|
| React SPA with React Router; every flow reachable | src/App.js has public entry/sign-in, six diner routes, five vendor routes and catch-all. Root now leads to sign-in. Correct-persona return paths are retained. Route table updated in frontend-architecture.md. |
| Five shared decisions with concrete alternatives and limits | Configuration, API client, refusal feedback/recovery, persona gate and synchronous in-flight guard remain shared. The fifth decision is request-in-flight behaviour, distinct from database idempotency. LoadState provides consistent failed-read recovery. |
| Diner state visible before action | Menu sold-out/closure badges disable Add; cart and checkout show known unavailable lines plus stall closure and block increases/checkout/payment. Cart API now treats soft-deleted items as unavailable and includes a derived stall DTO alongside the existing vendor ID. Unknown cart quantities disable Add until the cart can be read. |
| Actions match persona/current record state | RequireRole isolates the persona routes; vendor detail renders only server allowed_actions; terminal orders are read-only. Ready explains the 30-minute no-show wait. Real role/scope refusal checks and all vendor-state screens were rechecked. |
| No duplicate payment from an in-flight action | Checkout keeps its retry key and synchronous guard. Payment radios, failure toggle, refresh and cart editing are locked during payment. Real failed-payment retry emitted the same key and stored one order; real double-click stored one order. |
| Diner ordering and vendor menu/trading/fulfillment work end to end | Supplementary current-flow checks: diner 26 passed, vendor 37 passed. Covered menu create/edit/remove, validation, restock, closure, closed queue, accept/reject/refund, Ready/collection, no-show and diner feedback. Authentic task8/task9 screenshots refreshed. |
| US10 on reachable existing screens | Order List All/Current/Past and Order Detail remain the extra story's screens. Supplementary history UI checks: 15 passed, including snapshots, empty views, newest-first display and polling split. Q4(c)'s H01–H11 functional-test design is unchanged and remains unimplemented. |
| Screenshots/report match code | All existing flow screenshots refreshed with readable navigation; route table, flow notes and Q1 persona-screen gap explanations updated. Generated report includes the actual screen evidence. |
| Clean handover | Pinned prerequisites, configuration/install/run/build commands remain in both READMEs; no product dependency changes. Production build succeeds; no node_modules or build output tracked. No hotel/OneMap feature code remains. |
| Real Q6(a) system lifecycle | Both roles sign in through the UI; the same new order reaches Collected with both screens asserted at every step. 1 passed twice, 11.28 s / 11.36 s; no reset between. Real API, no response mocks/token injection, condition waits. |

## Corrections and meaningful failures

Navigation text originally had 1.00:1 contrast against the dark background. It now has readable contrast and an active-route indicator. Sign-in originally offered no working pending state and dropped valid non-home return paths. Cart/checkout ignored known unavailable-line state. Vendor menu mutations could overlap, and an empty/terminal queue stopped polling for incoming orders. Failed reads could leave a permanent “Loading…” placeholder. These were reproduced before fixing.

`docs/evidence/frontend-quality/red.log` retains the first diagnostic run; `queue-red.log` corrects an initial queue probe that was masked by React StrictMode's duplicate initial read. `removed-red.log` and `cart-availability-red.log` prove the removed-item defect. The first adapted diner walkthrough failed on an obsolete technical-copy assertion; `flow-diner-first.log` preserves it. The assertion was changed to visible payment-failure behaviour and actual emitted checkout keys, not hidden debug text.

After correction, `review.py` passed **24/24** supplementary checks. Held/faulted/empty HTTP responses are deliberately limited to diagnostic pending/error/queue checks; they are not the assessed lifecycle or genuine outage screenshots. These diagnostics create no orders and restore the original guarded cart/item document. The real flow scripts have an explicit preflight requiring exactly nine canonical orders and an API stall ID matching the guarded database, before any mutation/cleanup. They never target the development database.

Fresh final verification: default offline suite **313 passed in 8.01 s**, functional **10 passed twice (4.27/3.88 s)**, browser **1 passed twice (11.28/11.36 s)**, production build **compiled successfully**. Browser runs retain the existing non-failing MongoEngine UUID-representation warning. Current-flow and lifecycle logs are under docs/evidence/frontend-quality/.

This review adds no frontend unit/component suite. Historical Qwen/Codex evidence remains labelled historical. Personal cover details, missing historical prompt exports, narrated MP4, final publication/access and submission remain human actions.

Layout review: 30 captures at 1280, 375 and 320 pixels, zero horizontal overflow and zero uncaught page errors. Navigation contrast passed for both personas; active areas are indicated. Item metadata wraps rather than squeezing names. Full demo rehearsal passed, producing 26 authentic captures and restoring its own state. `layout.log`, `frontend-quality-final/audit.json`, `build.log` and `demo.log` retain the outputs.

Local code commits: frontend `b655615`; backend `665bd16`. Both remain on setup/lab-adaptation; final report/evidence packaging follows them. Nothing was pushed or submitted.
