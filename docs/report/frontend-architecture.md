# Q5(a) — Shared frontend architecture (working note, Task 7)

**Status: shared modules, routes and verification landed in the frontend
repository; this note is condensed into the report at Task 13.**

## Route table

All routes are defined in `src/App.js` (CRA + React Router 6). The diner and
vendor areas are nested under a `RequireRole` gate and a persona layout that
renders the shared feedback banner plus `<Outlet/>`. No registration,
user-administration or OneMap area exists, and no order screen is public.

| Route | Screen | Access |
|---|---|---|
| `/login` | `LoginPage` — seeded-account sign-in with the backend's refusal text | public |
| `/diner/stalls` | `StallsPage` — open-stall discovery | diner |
| `/diner/stalls/:stallId` | `MenuPage` — one stall's menu | diner |
| `/diner/cart` | `CartPage` — cart, server total, fingerprint | diner |
| `/diner/checkout` | `CheckoutPage` — simulated payment, retry key and visible refusals | diner |
| `/diner/orders` | `OrdersPage` — own order list | diner |
| `/diner/orders/:orderId` | `OrderDetailPage` — own order detail | diner |
| `/vendor/menu` | `VendorMenuPage` — own menu + trading state | vendor |
| `/vendor/menu/new` | `MenuItemFormPage` — validated item creation/editing | vendor |
| `/vendor/menu/:itemId/edit` | `MenuItemFormPage` — validated item creation/editing | vendor |
| `/vendor/orders` | `VendorOrdersPage` — stall's paid queue | vendor |
| `/vendor/orders/:orderId` | `VendorOrderDetailPage` — one paid order | vendor |
| `*` | `NotFoundPage` — reachable catch-all | public |

Tasks 7–10 implemented the shared modules and all diner/vendor screens. The current Order List includes All/Current/Past views; checkout and item forms are complete. Accessible headings, links and labels support the browser lifecycle suite.

## Five shared decisions

Each decision names the module or component, the real alternative it was
weighed against, why it was chosen, and what it does not provide.

### 1. `src/config.js` — one configured API base URL

| | |
|---|---|
| **Module** | `src/config.js` exports `API_BASE_URL` from `process.env.REACT_APP_API_BASE_URL`, documented in `.env.example` as `http://127.0.0.1:5001`. |
| **Alternative weighed** | Reading `process.env` in every page, or deriving the origin from `window.location`. |
| **Why** | One value every page and the shared client read; the documented default matches the backend's CORS allowlist for `http://127.0.0.1:5173`, so a fresh clone works with `cp .env.example .env`. Deriving the origin from the page would break the moment the frontend is served from a different port than the CORS allowlist expects. |
| **What it does not provide** | No runtime discovery: a backend moved to another host requires the `.env` change; the file holds no other configuration and no per-route overrides. |

### 2. `src/api/client.js` — one fetch wrapper, one typed error

| | |
|---|---|
| **Module** | `request(path, options)` attaches the Bearer token, resolves the base URL, and throws `ApiError` (`status`, `code`, `message`, plus `expired` for `401 authentication_required`) parsed from the backend's stable `{"error": {"code", "message"}}` contract. |
| **Alternative weighed** | Raw `fetch` calls in each page, or adopting axios. |
| **Why** | Token attachment and refusal parsing happen in exactly one place, so no page can forget the header or render a raw rejection; native `fetch` plus a small error class covers the whole contract without a new dependency. Axios was a real alternative (interceptors, retries) but its features are unused: the contract is one header and one error shape, and adding a library would obscure where the token leaves the browser. |
| **What it does not provide** | No retries, no automatic re-authentication (an expired token routes the user to sign-in; the app never mints its own token), no request caching or offline queueing, and no CORS configuration — cross-origin access is the backend's `FRONTEND_ORIGIN` allowlist decision. |

### 3. `FeedbackContext` + `FeedbackBanner` — the refusal reaches the screen that caused it

| | |
|---|---|
| **Module** | `src/context/FeedbackContext.jsx` (a queue of `show(message, kind)` / `dismiss(id)`) and `src/components/FeedbackBanner.jsx`, rendered inside both persona layouts and the login screen. |
| **Alternative weighed** | Per-component local alert state, or `window.alert`. |
| **Why** | The context sits above the router, so a refusal raised on one screen survives a client-side redirect and still lands where the user is; the banner inside each layout means every protected screen gets the same display. `window.alert` blocks the page and cannot be restyled; local state would vanish on navigation and duplicate the banner markup in every page. |
| **What it does not provide** | Not a global toast system: no per-message expiry timer, no stacking limit beyond the list, no deduplication of identical back-to-back refusals, no translations or event tracking. |

### 4. `RequireRole` — client-side gate with the backend authoritative

| | |
|---|---|
| **Module** | `src/auth/RequireRole.jsx` wraps each persona's nested routes: unauthenticated → `/login` (remembering the intended path); wrong persona → that persona's own home. |
| **Alternative weighed** | No gate at all — let any signed-in user reach any route and let every API call 403. |
| **Why** | A diner who types `/vendor/menu` gets an instant redirect instead of a screen full of refusal banners, and an unauthenticated visitor never sees a persona layout. The gate is explicitly **not** a security boundary: the backend re-verifies the token and role on every request, and Task 7's live check confirmed a diner's token is refused `403 forbidden` on `GET /api/vendor/menu` even while the UI is running. |
| **What it does not provide** | No protection against crafted URLs, direct API calls, or a token whose role the UI misread — the 401/403 boundary, record ownership and the stall relationship are enforced only in `app/auth.py` and the models. The gate also cannot see token expiry itself; it reacts when an API call's 401 clears the session. |

### 5. `AsyncButton` / `useAsyncAction` — shared request-in-flight control

| | |
|---|---|
| **Module** | `src/components/AsyncButton.jsx` — while the wrapped request is in flight the button is disabled and shows progress text; a second click cannot start a second request. `useAsyncAction` exposes the same guard for screens that drive their own control. |
| **Alternative weighed** | Ad-hoc `submitting` state in each page, or no guard (trusting the user not to double-click). |
| **Why** | One shared pending behaviour (disabled + progress text) instead of per-page duplication, and the refusal-then-retry path (e.g. checkout's failed payment) keeps exactly one checkout key with a synchronous re-entry guard, so a double-click cannot queue two payments from this tab. |
| **What it does not provide — and how that differs from database idempotency** | This is **UI-side duplicate control for this tab's own clicks**: a second tab, a second browser, a browser-level retry, or a network-level resend of the same request is invisible to the button. Those cases are handled at the database layer instead — the `(diner, checkout_key)` unique index makes a repeated checkout store at most one order, a matching replay returns the stored order (200) and a conflicting reuse is refused (409), as proven by the functional suite's two-thread race. The button prevents the user's *intent* from firing twice; the index prevents a duplicate *row*. |

## Token state and logout

`src/auth/AuthContext.jsx` stores `{user, token}` in `sessionStorage`
(per-tab, so one browser can hold a diner in one tab and a vendor in
another). `login` exchanges the seeded account's credentials through
`POST /api/user/gettoken`; `logout` clears the tab's entry; any
`authentication_required` 401 on a bound request clears it, which makes
`RequireRole` route the user back to sign-in. Tokens are never stored in
`localStorage` and are never read after logout.

## Verification (7 October 2026)

- `npm run build` (Node 22.17.0, `react-scripts` 5.0.1): **Compiled
  successfully**, no ESLint warnings; production bundle rebuilt after the
  final change.
- Manual two-persona verification against the live dev API (5001) and the
  CRA dev server (5173), script `.local/verification/task7_ui_check.py`
  (Playwright, not an assessed suite) — **all 10 checks passed**, run twice
  (second run after a UI field-name fix): unauthenticated diner visit
  redirects to `/login`; wrong password shows the backend's refusal in the
  banner; diner login lands on the open-stall list with Charcoal Grill
  marked Open; cart and orders load under the token; a diner visiting
  `/vendor/menu` is redirected client-side **and** the backend refuses the
  same API call with the diner token (`403 forbidden`); a forged token's
  401 clears the session and presents sign-in; the unknown path shows the
  not-found view; vendor login lands on the menu and the paid queue loads
  with the seeded orders.
- The first run's screenshot review caught a real UI bug: the stall
  trading-state badge read `stall.open` while the API field is `is_open`,
  so an open stall rendered "Closed". Fixed in `StallsPage`/`VendorMenuPage`
  and re-verified (badge now reads "Open"; the check now asserts the green
  badge).
- No frontend unit/component suite exists, as the TMA does not require one;
  the assessed browser suite is Task 11's Playwright test.
