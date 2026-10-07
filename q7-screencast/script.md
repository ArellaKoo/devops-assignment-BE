# Q7(a) screencast — timed narration script

**Target:** one continuous take, **under 8 minutes** (this script lands at
about 7 minutes 20 seconds at a calm pace; cut the closing recap if you run
long). 720p, ≤100 MB. Two logged-in browsers/contexts: **diner**
(`diner.one@skipq.test`) and **vendor** (`vendor.one@skipq.test`) — same
password for both, `SkipQDemo2026!`. Start from the seeded state described
in `demo-data.md`.

The TMA requires that, for each rule violation, the **expected outcome is
stated on screen before it happens**. Both markers ("Before I pay…") are in
this script for that reason — do not skip them.

---

## 0:00–0:20 — Introduction (on the diner's sign-in screen)

> "SkipQ is a food-court ordering system with two personas: a diner and a
> stall vendor. In the next seven minutes I'll place one order as a diner,
> then follow *that same order* to collection on the vendor side — and then
> I'll show two cases where the system must refuse a checkout."

*(Sign in as `diner.one@skipq.test`.)*

## 0:20–0:50 — Diner: stalls and menu

> "I'm signed in as a diner. This is the stall list — only open stalls show
> up here. Charcoal Grill is open. I open its menu. Pineapple Tart is
> already sold out — notice it's greyed and its Add control is disabled,
> before I can even try."

*(Open the stall, show the menu.)*

## 0:50–1:30 — Diner: add, cart, checkout, paid

> "I add one Charcoal Chicken Rice — the button now says 'Add another, in
> cart: 1', so the server confirmed the line. I review the cart: one item,
> six dollars fifty. At checkout I leave the 'simulate this payment failing'
> control off — I want a real success — and I pay.
> Payment is simulated, but the checkout logic is the real one: it checks
> that the stall is open, that every line is still available, and that the
> cart hasn't changed since I loaded it. It succeeds, and here is my new
> queue number — the server minted it, so it's different every run."

*(Pay $6.50 → success screen with the queue number.)*

## 1:30–1:45 — Diner: tracking

> "I track the order. It's Pending — the stall hasn't picked it up yet. I'll
> leave this screen open; it polls every three seconds."

## 1:45–2:30 — Vendor: accepts and prepares the same order

> "Now the vendor side, in the second browser. I sign in as the vendor of
> Charcoal Grill. My paid queue shows that exact queue number — the same
> order the diner just paid for, not a copy. I open it, and accept. It's
> now Preparing. And if I cut back to the diner — the diner's own screen has
> already updated to Preparing, by its own polling, without any refresh.
> That's the two-persona lifecycle on the same order."

*(Vendor: Manage → Accept order. Cut to diner's tracking screen.)*

## 2:30–3:30 — Vendor: ready, then collected; diner sees both

> "I mark it ready. The diner's tracking screen now shows the green 'Your
> order is ready — collect it at the counter' banner — again, observed by
> its own polling. Finally I mark it collected. The order is terminal: the
> vendor's screen is read-only, and so is the diner's — 'Collected, thanks
> for ordering'. One quick last check on the diner side: the Order List,
> Past filter. That order is there, read-only with its snapshot — this is
> the US10 history view reusing the existing list, no separate page."

*(Mark ready → cut to diner banner → Mark collected → diner's Collected
screen → diner's Order List, Past filter.)*

## 3:30–4:30 — Violation 1: sold-out line, refusal expected

> "Now the first refusal. Back on the diner side: I open the menu again and
> add a Mango Sago. My cart now has one item, two fifty.
> **Before I pay:** the vendor is about to mark that exact item sold out.
> The expected outcome — and this is what the design promises — is that my
> checkout is *visibly refused* because the line I'm paying for is no longer
> available, that my cart is *retained* so I can review it, and that *no new
> order is stored*. Let's see if that's what happens."

*(Diner adds M2. Vendor marks M2 Sold out.)*

## 4:30–5:20 — Violation 1: the refusal

> "I go to checkout and press Pay two fifty. And there it is: 'Checkout
> refused — Mango Sago is no longer available. Remove it from your cart to
> check out.' The message names the item, I still have my checkout key for
> this attempt, and the cart is retained — I review it and the line is
> still there. The script also checked the API after this step: exactly one
> order exists — the one from phase one. This refused checkout stored
> nothing."

*(Pay → refused screen → Review your cart.)*

## 5:20–6:10 — Violation 2: closed stall, refusal expected

> "Second refusal. Still on the diner side, I add a Charcoal Chicken Rice,
> so the cart is now nine dollars.
> **Before I pay:** the vendor is about to close the whole stall. Expected
> outcome: checkout is *visibly refused* because the stall is closed — the
> paid queue stays accessible to the vendor, but no new order may be
> created. Let's see."

*(Diner adds M1 → cart two lines $9.00. Vendor flips the trading-state
switch.)*

## 6:10–7:00 — Violation 2: the refusal

> "The stall now shows Closed, with its banner: new orders refused at
> checkout, every paid order below stays accessible. I go to checkout and
> press Pay nine dollars. Refused again — 'Charcoal Grill is currently
> closed. Try again once the stall opens.' Same behaviour as before: a clear
> message, the cart retained, no order stored."

*(Pay → refused screen.)*

## 7:00–7:20 — Close

> "To recap: one order went from the diner's checkout, through Pending,
> Preparing and Ready, to Collected on both personas' screens; and two
> rule violations — a sold-out line and a closed stall — each produced a
> visible refusal with the cart retained and nothing stored. The scripted
> version of exactly this run is in `demo_script.py`, and the run log with
> all 26 screenshots is `demo-run-log.md` in the backend repository's
> `q7-screencast` folder."

*(End.)*

---

## Production notes

- **Two windows, one screen:** keep the diner window on the left and the
  vendor on the right (or switch between two tabs); the narration above
  assumes a single 1280×720 window with quick cuts — either is fine as long
  as both personas' screens are genuinely shown.
- **No fakes:** never pre-stage a screenshot and play it; the polling waits
  are real (about 3 seconds each). If a poll takes longer than the
  narration, just say "it polls every three seconds" and wait — that keeps
  the take honest and under the time limit.
- **If you drop the take:** restart from the last phase boundary
  (A/B/C). The app state is idempotent at those boundaries — the run's own
  order can be removed with one Mongo command, and the demo script's
  cleanup section shows the exact one.
- **Length control:** if you exceed 7:50, cut the US10 recap sentence and
  the close's last clause — the TMA-critical content is the same order
  across both roles and the two pre-narrated refusals.
