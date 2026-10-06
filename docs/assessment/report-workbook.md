# ICT381 report and GBA audit workbook

**Planning worksheet, 6 October 2026.** The lab-adapted startup foundation and four setup regressions exist; domain functionality, assessed suites and measurements are not yet implemented. Revise these tables against the actual build before using them in a submission. Sources: supplied TMA pp. 5–16 and Group 5 GBA Q2–Q6, including the embedded UML images. All proposed outcomes below are additions to be declared, not quotes from existing criteria.

The GBA does not number acceptance criteria. For traceability, `US7-AC2` means the second Given/When/Then block under User Story 7 in GBA Q2(b). The TMA refers to Q2(c), which is a numbering mismatch; cite the story/block precisely. Do not copy whole GBA paragraphs into the report.

## Q1(a): Four capabilities

Each final capability section must start with its Status, then contain the five-row artifact table. Status reflects actual evidence: fully supported only if the additions column is empty, not supported only if the evidence column is empty. These initial sections are **partially supported** because evidence and required corrections both exist. Update them before/during/after implementing each capability.

### C1: Diner browsing, ordering, and tracking

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Diner US4 adds/changes cart items; US5 pays and receives queue number; US6 views changing queue/order status. Their happy path covers ordering and tracking. | Limit US6 to baseline status viewing. TMA requires simulated payment, so describe US5 as simulation; do not claim a gateway or implemented email delivery. Open-stall browsing requires trading-state linkage from US12. |
| Acceptance criteria | US4-AC1/2 cover add/remove/quantity and updated price. US5-AC2/3 distinguish paid confirmation/queue from failure/retry. US2-AC4 blocks checkout of an item sold out after adding. US6-AC1/3/4 cover refresh and terminal display. | Add empty cart, invalid/noninteger quantities, single-stall cart, changed-price review, closure after browsing, request-in-flight lock, and matching checkout retry outcomes. Original criteria do not specify these refusals or duplicate handling. |
| Specification: feature/data/rules/workflow | Q4(a) Add to cart identifies Cart/Diner/item/quantity/price; Payment requires amount=total and no order/queue before success; Order status & notification gives Pending→Preparing→Ready→Collected. | Store money as integer cents and calculate server-side. Specify methods/refusal codes, menu/stall revalidation and cart price fingerprint. Persist line-item purchase snapshots. Define in-app Ready feedback as the selected notification channel; actual email is outside chosen scope. |
| Class diagram and state machine | Q6(a) Diner→FoodOrder, FoodOrder→OrderedFood/Payment, FoodItem data; Q6(b) shows payment/accept/preparation/collection concepts. | Add Cart/CartItem, order-to-Vendor reference, image, queue number and timestamp/snapshot fields. Resolve Q6's PendingPayment/Accepted/PendingPreparation/PendingCollection against Q4's canonical states; failed payment makes no Order. Separate payment refund state from fulfillment. |
| Persona screens | Q5 Diner Home/Vendor/Item Details/Cart/Checkout/Payment Success/Order Tracking screens cover the ordering sequence. | Remove preorder time and registration from selected scope. Add open/closed/sold-out state before action, explicit simulation/failure/retry, pending-submit feedback, stale cart refusal and a readable Ready banner. Document which screens are combined and why. |

### C2: Vendor menu and order operation

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Vendor US1/US3 create/edit menus; US2 toggles sold out; US7 manages paid incoming orders; US12 opens/closes the store. | US12 is High in Q3's table but absent from Q4 features/Q7 task list. Include it because the TMA baseline explicitly requires open/close. Do not mistake US17 capacity pause for US12. |
| Acceptance criteria | US1/US3 validate required menu fields; US2-AC1/2 sold-out/restock; US7-AC1–6 incoming/accept/reject/ready/collect/no-show; US12-AC4/5 blocks new ordering while preserving existing orders. | Correct US7-AC5's `Completed` to `Collected` to agree with Q4/Q5; add disallowed transition, vendor ownership, closed-stall existing-order operation and the precise Ready+30m boundary. Explain that accepting begins Preparing. |
| Specification: feature/data/rules/workflow | Q4 Menu Management has name 1–80, price >0/<9999/2 decimals, description≤500 and image formats. Diner's order list specifies paid-only queue, rejection/refund and terminal immutability. | Add explicit Vendor.is_open/open-close feature, paid-order scope to the vendor, simulated refund, NoShow remains paid, deletion as inactive menu item, permitted next actions, and actionable 400/403/409 mapping. |
| Class diagram and state machine | Q6 Vendor→Menu→FoodItem; FoodOrder/OrderedFood identify orders/items. Q6(b) has rejection/refund and 30-minute no-show concepts. | Distinguish vendor account from stall; add Order→Vendor, trading state, Ready timestamp and payment method/amount. Canonical reject means Order Cancelled + Payment Refunded. Stored is persistence, not a lifecycle state; duplicate refund nodes are not two distinct states. |
| Persona screens | Q5 Vendor Admin/Item Details/Diner's Order/Order Details include menu edits and accept/reject/ready/collect/no-show controls. | Add open/close switch/banner and current-state permitted controls. Remove business insights/profile editing if unnecessary to this scope. Keep paid queue accessible after closing. Add refund/early-no-show/refused transition display. |

### C3: Authentication and roles

**Status: partially supported.**

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User stories: ID/text/persona | Vendor US8 signs in to only its stall; Diner US16 signs in and accesses its own cart/orders. | Seeded account sign-in is in TMA scope; registration/password reset/user administration are excluded by Q5. State this adaptation of US16 rather than claiming full registration coverage. |
| Acceptance criteria | US8-AC1/2 correct/incorrect login; US16-AC3/4 login outcomes and AC5 own-data visibility. | Add missing/invalid/expired token 401, wrong role 403 and wrong owner/stall 403. Clarify no mutation/data on refusal, email normalization and account lock/unlock behavior. |
| Specification: feature/data/rules/workflow | Q4 User authentication uses email/password/vendor_id, unique email, hashed credentials, correct-role redirect and lock after five failures. | Specify signed expiring tokens, model-owned scope checks and safe example config. Set 15-minute lock duration and 429 while locked because original lock has no unlock mechanism. Do not claim locally hosted development HTTP satisfies the GBA's production HTTPS/uptime claims. |
| Class diagram and state machine | Q6 abstract User has email/password, Diner and Vendor specialization. | Store password hash rather than raw password. Model User role plus optional Vendor reference, allow multiple accounts per stall as Q4 says, and define failure-count/locked-until fields. Authentication events are not fulfillment states. |
| Persona screens | Q5 shared Login and Diner-only Registration distinguish personas. | Keep seeded Login only; add role redirect, protected navigation, shared token-expiry feedback and logout. UI route gating is usability; server is the security boundary. |

### C4: Extra story US10 current and past orders

**Status: partially supported.**

**Reason for choice:** US10 is a Medium-priority backlog story outside baseline order-status tracking. It adds historical visibility using existing orders and the existing Order List/Detail screens, avoiding multi-stall payment complexity. Confirm this is the user's selected extra story before implementation.

| GBA artifact | Evidence it supports this capability | What needs adding/changing, and why |
|---|---|---|
| User story: ID/text/persona | US10: Diner wants past orders to know what they ordered previously. US16-AC5 supplies ownership intent for Order History. | Treat past-order visibility as the extra capability, separate from mandatory tracking of a new order. Do not add reorder/analytics, which this story does not request. |
| Acceptance criteria | US10-AC1 says the Order List shows all current and past orders when scrolled. | Add All default plus Current/Past filters, empty results, only own orders, newest-first with tie-breaker, login persistence, read-only historical detail, and unchanged purchase snapshots. Original criterion cannot determine these test outcomes. |
| Specification: feature/data/rules/workflow | Q4 Authentication mentions individual history; order features include Order ID/items/quantity/status/payment. Q4 does not have a history feature. | Add explicit query contract: view=all/current/history, history terminal categories Collected/Cancelled/NoShow, invalid view 400, empty list 200, and owner filtering inside model. State why immutable snapshots support trustworthy history. |
| Class diagram and state machine | Q6(a) Diner creates zero/many FoodOrders; date/time, cost and OrderedFood quantity/subtotal exist. Q6(b) mentions terminal orders and Stored. | Keep completed/cancelled/no-show orders in database without a Stored workflow state or one-year deletion job. Add immutable purchased name/unit-price snapshots and own-diner reference. Define actual retention scope; no unimplemented yearly deletion claim. |
| Persona screens | Q5 Order List Page lists current and past orders with statuses. | Reuse one list with All/Current/Past and readable empty state; reuse Order Detail for read-only past details. Remove multi-stall cancellation actions because multi-stall/cancel-anytime are outside scope and conflict with vendor preparation rules. |

## Audit maintenance log

Keep a short real dated log while building; final Q1 uses final findings, not abandoned speculation. Suggested columns: capability, artifact, discovered gap, final decision, code/test evidence, date/commit. Do not backdate discoveries or commits.

## Q1(b): Provenance worksheet

| Actual source repository + commit | Copied module/file | Reused or substantially rewritten? | What it does and why SkipQ needs it | Verification / final location |
|---|---|---|---|---|
| Fill only after inspecting/copying actual lab sources | Actual file | Accurate classification | 1–2 sentences in your own words | Actual behavior and code path |

Lab adaptation is selected. The populated [foundation provenance](../report/provenance.md) records actual source commits and retained/reworked modules. Use it to replace this blank final-report worksheet, then extend it as domain/auth modules are adapted. Distinguish lab reuse, your implementation and AI assistance accurately.

## Q5(a): Required architecture reasoning table

The final report must name actual modules and explain tradeoffs against alternatives. Adapt these planned rows to the built code.

| Decision | Where it lives | Why there versus alternative | What it does not give you |
|---|---|---|---|
| Attach token | `src/api/client.js`, consuming AuthContext | A single request path handles diner/vendor polling and mutation consistently; per-page headers risk one flow forgetting auth. | Does not verify identity; API token validation does. |
| API base URL | `src/config.js` + example env | Both seeded local runs and isolated system-test API can change address once; hardcoded per-page strings make the browser test depend on edits in many files. | Does not start the API, configure CORS or ensure it is reachable. |
| Refusal handling and visibility | API client + FeedbackContext/Banner | Menu, checkout and lifecycle mutations share actionable server messages; local catch blocks otherwise produce inconsistent feedback for the same stale-stock/role refusal. | Does not predict concurrent stock change or replace server business validation. |
| Persona reachability/offered actions | RequireRole + persona layouts; order action availability | Nested layouts prevent vendor/diner navigation leaking into the other flow; each route/page rebuilding auth checks is easy to miss. | Browser gating cannot authorize requests or prevent direct HTTP calls; models enforce scope and states. |
| Fifth: request-in-flight controls | AsyncButton + guarded checkout handler | The same pending state disables repeated checkout and lifecycle submissions, instead of each screen forgetting to prevent re-entry. | Does not alone prevent retries from two tabs or after an uncertain response; backend request-key uniqueness supplies that protection. |

Provide a separate route table using the design's actual paths and 1–2 sentences on why nested persona layouts match these flows. If the final implementation changes filenames/paths, change the table too.

## Report structure and word budget

Reserve roughly **2,700 words of counted prose**, keeping a 300-word margin. Tables, screenshots and appendices are excluded by the assignment, but should stay purposeful.

| Section | Suggested counted prose | Contents |
|---|---:|---|
| Cover | Minimal | ICT381/title, your PI/name/submission date, both repository URLs |
| Q1 | 350 | Group 5, four statuses/audit tables, extra-story reason, concise provenance |
| Q2 | 200 | Seed coverage table and criterion-specific explanations/manual actions |
| Q3 | 150 | Blueprint role/scope explanation and model-guard placement, code references |
| Q4 | 550 | Mocking comparison, two functional strengths, designed test table, strategy and priority |
| Q5 | 350 | Route structure and five architecture tradeoffs/limits, flow screenshots and reused US10 screens |
| Q6 | 250 | Concrete browser-vs-functional result, selected endpoint/load/measurements, ≤100-word DB verdict |
| Q7 | 500 | Screencast link and 400–500 words for the two PMF hypotheses combined |
| Captions/transitions | 350 | Actual evidence identification and necessary clarifications |
| **Planned total** | **2,700** | Recount after drafting; do not exclude ordinary prose by relabeling it |

Appendices: exact AI prompts with question labels and verification, additional command output if useful, clear evidence references. Do not paste entire source files; link final repo file/line and commit where needed.

## Q7(b): Hypothesis worksheet

Write these after experiencing the actual MVP. Each must be falsifiable and tied to the built screen/step, not a generic food-app proposal.

| Required label | Diner hypothesis prompts | Vendor hypothesis prompts |
|---|---|---|
| The pain | Which ordering/tracking step felt costly? Who experiences it, and when? | Which queue/menu/preparation step made stall operation difficult? |
| The hypothesis | One change or different user segment; what observable benefit do you predict? | One change/removal/segment; what observable operating benefit do you predict? |
| The market, and who pays | Who else has the pain? Rough count with counted population/basis; who pays and for what? | Estimate stalls/operators with explicit basis/assumption; who would pay and why? |
| The test | Cheapest interview/prototype/concierge evidence; success and falsification thresholds. | Cheapest operational trial/interview; result that would make you reject the hypothesis. |

No fabricated market data or test execution is needed. Label assumptions, and combine both hypotheses into 400–500 words.

## Report readiness check

- Every statement of behavior/results refers to actual final code or measured evidence.
- All Q1 gap additions have matching code/scope decisions and tests/screens where appropriate.
- Q2 seed matrix argues each criterion, rather than merely listing records.
- Q4 named methods/test strengths refer to these suites; Q4(c) is explicitly designed, not executed.
- Q5 includes actual screenshots of all screens in all four capability flows and the fifth decision.
- Q6 verdict cites actual query/request evidence and does not propose a fix.
- Recording links work for the marker, and show prediction/refusal for both violations.
- Both remote repositories contain required artifacts, with no secrets or hotel/OneMap/Selenium remnants.
- Prompt disclosure includes planning/code/tests/test-data use and how each output was verified.
