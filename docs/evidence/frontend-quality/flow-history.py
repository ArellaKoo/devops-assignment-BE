"""Task 10 manual verification: the US10 All/Current/Past Order List filters.

The diner Order List gains All/Current/Past over the server's
view=all|current|history (UI Past maps to view=history). Two logged-in UI
contexts: diner.one (seeded mixed statuses across both stalls, plus
another diner's order that must stay out of the list) and diner.empty
(no orders at all — the friendly empty screens). One timing measurement
(windowed request counting, wait_for_timeout used as a measurement, not a
condition wait) proves Past does not poll while Current does. A vendor
API reprice under an open current-order detail proves the purchase
snapshots survive menu edits. Screenshots land in
backend/docs/evidence/screenshots/ as task10-*.

Exit 0 only when every check passes and the database is re-seeded clean.
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

from playwright.sync_api import expect, sync_playwright

API = "http://127.0.0.1:5001"
BASE = "http://127.0.0.1:5173"
PASSWORD = "SkipQDemo2026!"
from flow_preflight import verify
BACKEND = verify()
SHOTS = BACKEND + "/docs/evidence/screenshots"

failures = []


def check(name, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'}: {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(name)


def api(method, path, token=None, body=None):
    url = f"{API}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as err:
        return err.code, json.load(err)


def login_token(email):
    status, data = api("POST", "/api/user/gettoken", body={"email": email, "password": PASSWORD})
    assert status == 200, f"login failed for {email}: {status} {data}"
    return data["token"]


def ui_login(page, email, home):
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{BASE}{home}", timeout=10000)


# Start from the seeded state (idempotent upserts).
seed_out = subprocess.run(
    [f"{BACKEND}/.venv/bin/python", "-m", "db_seed.seed"],
    capture_output=True,
    text=True,
    cwd=BACKEND,
)
print(seed_out.stdout.strip())
if seed_out.returncode != 0:
    print("SEED FAILED:", seed_out.stderr)
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    d1_ctx = browser.new_context()
    d1 = d1_ctx.new_page()
    d0_ctx = browser.new_context()
    d0 = d0_ctx.new_page()

    try:
        # --- record ids --------------------------------------------------------
        d1_token = login_token("diner.one@skipq.test")
        v1 = login_token("vendor.one@skipq.test")
        status, menu = api("GET", "/api/vendor/menu", token=v1)
        m1 = next(item for item in menu["items"] if item["name"] == "Charcoal Chicken Rice")
        status, orders = api("GET", "/api/diner/orders?view=all", token=d1_token)
        by_queue = {o["queue_number"]: o for o in orders["items"]}
        check(
            "seed state located (D1 owns 8 orders across both stalls; D2's 0008 separate)",
            len(orders["items"]) == 8 and "Q-seed-0008" not in by_queue,
            str(sorted(by_queue)),
        )

        # --- 1. All view: own orders only, all six statuses --------------------
        ui_login(d1, "diner.one@skipq.test", "/diner/stalls")
        d1.goto(f"{BASE}/diner/orders")
        rows = d1.locator(".list-group-item")
        expect(rows).to_have_count(8, timeout=5000)
        expect(d1.get_by_text("Q-seed-0008")).to_have_count(0)  # another diner's order
        for status_label in ("Pending", "Preparing", "Ready", "Collected", "Cancelled", "NoShow"):
            expect(d1.locator(".badge", has_text=status_label).first).to_be_visible()
        check("All lists all 8 own orders (every status) and never another diner's order", True)
        d1.screenshot(path=f"{SHOTS}/task10-01-orders-all.png")

        # --- 2. newest-first order ---------------------------------------------
        expect(rows.nth(0).get_by_text("Q-seed-0009")).to_be_visible()  # -15 min, newest
        expect(rows.nth(1).get_by_text("Q-seed-0003")).to_be_visible()  # -20 min
        check("All lists newest-first (0009 before 0003)", True)

        # --- 3. Current filter ---------------------------------------------------
        # Windowed request counting (listener first, then the click): a
        # measurement over two 3-second periods, not a condition wait.
        current_requests = []
        d1.on(
            "response",
            lambda resp: current_requests.append(resp)
            if resp.url.endswith("/api/diner/orders?view=current") else None,
        )
        d1.get_by_role("button", name="Current", exact=True).click()
        current_rows = d1.locator(".list-group-item")
        expect(current_rows).to_have_count(5, timeout=5000)
        for queue in ("Q-seed-0009", "Q-seed-0003", "Q-seed-0004", "Q-seed-0002", "Q-seed-0001"):
            expect(current_rows.get_by_text(queue)).to_be_visible()
        for queue in ("Q-seed-0005", "Q-seed-0006", "Q-seed-0007"):
            expect(current_rows.get_by_text(queue)).to_have_count(0)
        check("Current shows only the 5 Pending/Preparing/Ready orders, no terminal ones", True)
        d1.screenshot(path=f"{SHOTS}/task10-02-orders-current.png")
        d1.wait_for_timeout(8000)  # intentional: two polling periods of measurement
        check("Current keeps polling while visible (2+ requests in 8 s)", len(current_requests) >= 2, str(len(current_requests)))

        # --- 4. Past filter: terminal orders only, and it never polls -------------
        history_requests = []
        d1.on(
            "response",
            lambda resp: history_requests.append(resp)
            if resp.url.endswith("/api/diner/orders?view=history") else None,
        )
        d1.get_by_role("button", name="Past", exact=True).click()
        past_rows = d1.locator(".list-group-item")
        expect(past_rows).to_have_count(3, timeout=5000)
        expect(past_rows.nth(0).get_by_text("Q-seed-0007")).to_be_visible()  # newest past (-300 min)
        for queue in ("Q-seed-0005", "Q-seed-0006"):
            expect(past_rows.get_by_text(queue)).to_be_visible()
        for queue in ("Q-seed-0001", "Q-seed-0009"):
            expect(past_rows.get_by_text(queue)).to_have_count(0)
        check("Past shows exactly the 3 terminal orders, newest-first", True)
        d1.screenshot(path=f"{SHOTS}/task10-03-orders-past.png")
        d1.wait_for_timeout(8000)  # intentional: two polling periods of measurement
        check("Past does not poll (exactly 1 request in 8 s)", len(history_requests) == 1, str(len(history_requests)))

        # --- 6. read-only past detail: stale snapshot survives ---------------------
        d1.goto(f"{BASE}/diner/orders/{by_queue['Q-seed-0005']['id']}")
        expect(d1.locator(".badge", has_text="Collected")).to_be_visible(timeout=5000)
        expect(d1.locator(".alert-secondary", has_text="Collected")).to_be_visible()
        expect(d1.get_by_text("Grilled Chicken Rice")).to_be_visible()  # old snapshot name
        expect(d1.get_by_text("$6.00").first).to_be_visible()  # old snapshot price
        check("a past order's detail is read-only and keeps its stale name/price snapshot", True)
        d1.screenshot(path=f"{SHOTS}/task10-04-past-collected-snapshot.png")

        # --- 7. read-only past detail: the refund is still shown ---------------------
        d1.goto(f"{BASE}/diner/orders/{by_queue['Q-seed-0006']['id']}")
        expect(d1.locator(".badge", has_text="Cancelled")).to_be_visible(timeout=5000)
        expect(d1.locator(".alert-warning", has_text="$2.50")).to_be_visible()
        check("a past cancelled order's detail still shows the refunded amount", True)
        d1.screenshot(path=f"{SHOTS}/task10-05-past-cancelled-refund.png")

        # --- 8. a live reprice does not touch an already-made order -----------------
        status, _ = api("PATCH", f"/api/vendor/menu/{m1['id']}", token=v1, body={"price": "7.00"})
        assert status == 200
        d1.goto(f"{BASE}/diner/orders/{by_queue['Q-seed-0001']['id']}")
        expect(d1.locator(".badge", has_text="Pending")).to_be_visible(timeout=5000)
        # 2 x snapshot 650c — unchanged by the menu's new $7.00 price.
        expect(d1.locator(".list-group-item", has_text="Charcoal Chicken Rice").locator("span").last).to_have_text("$13.00")
        check("an in-progress order keeps its snapshot total after the menu item is repriced", True)
        d1.screenshot(path=f"{SHOTS}/task10-06-current-snapshot-after-reprice.png")
        status, _ = api("PATCH", f"/api/vendor/menu/{m1['id']}", token=v1, body={"price": "6.50"})
        assert status == 200

        # --- 9. the explicit Refresh re-loads the selected view ----------------------
        all_requests = []
        d1.on(
            "response",
            lambda resp: all_requests.append(resp)
            if resp.url.endswith("/api/diner/orders?view=all") else None,
        )
        d1.goto(f"{BASE}/diner/orders")
        expect(d1.locator(".list-group-item").first).to_be_visible(timeout=5000)
        d1.get_by_role("button", name="Refresh").click()
        d1.wait_for_timeout(2000)  # intentional: let the refresh response land
        check("Refresh re-requests the selected (All) view", len(all_requests) >= 2, str(len(all_requests)))

        # --- 10. a diner with no orders: friendly empty screens -----------------------
        ui_login(d0, "diner.empty@skipq.test", "/diner/stalls")
        d0.goto(f"{BASE}/diner/orders")
        expect(d0.get_by_text("You have no orders yet.")).to_be_visible(timeout=5000)
        expect(d0.get_by_role("link", name="Browse open stalls")).to_be_visible()
        check("a diner with no orders gets the friendly All-view empty state", True)
        d0.screenshot(path=f"{SHOTS}/task10-07-empty-diner-all.png")

        d0.get_by_role("button", name="Current", exact=True).click()
        expect(d0.get_by_text("No orders in progress right now.")).to_be_visible(timeout=5000)
        check("the same diner gets the Current-view empty state", True)
        d0.get_by_role("button", name="Past", exact=True).click()
        expect(d0.get_by_text("No past orders yet.")).to_be_visible(timeout=5000)
        check("and the Past-view empty state", True)
        d0.screenshot(path=f"{SHOTS}/task10-08-empty-diner-past.png")

        d1_ctx.close()
        d0_ctx.close()
    finally:
        browser.close()

# Final re-seed and invariant check (restores M1 to 650c and any residue).
seed = subprocess.run([f"{BACKEND}/.venv/bin/python", "-m", "db_seed.seed"], capture_output=True, text=True, cwd=BACKEND)
print(seed.stdout.strip())
invariant = subprocess.run(
    [
        f"{BACKEND}/.venv/bin/python",
        "-c",
        "from mongoengine import connect; connect('skipq_system_test', host='mongodb://127.0.0.1:27017', connect=False); "
        "from app.models.vendor import Vendor; from app.models.menu_item import MenuItem; from app.models.order import Order; "
        "from app.models.cart import Cart; from app.models.user import User; "
        "s1 = Vendor.objects(name='Charcoal Grill').first(); s2 = Vendor.objects(name='Noodle Bar').first(); "
        "m1 = MenuItem.objects(name='Charcoal Chicken Rice').first(); m2 = MenuItem.objects(name='Mango Sago').first(); "
        "d1 = User.objects(email='diner.one@skipq.test').first(); "
        "print('invariant:', s1.is_open, s2.is_open, m1.price_cents, m1.is_available, m2.is_available, Order.objects.count(), Cart.objects.count(), len(Cart.objects(diner=d1).first().items))",
    ],
    capture_output=True,
    text=True,
    cwd=BACKEND,
)
print(invariant.stdout.strip())
check(
    "final reseed restores seed state (S1 open, S2 closed, M1 650c, 9 seed orders, 2 carts, C1 2 lines)",
    invariant.stdout.strip()
    == "invariant: True False 650 True True 9 2 2",
    invariant.stdout.strip(),
)

print()
if failures:
    print(f"SUMMARY: {len(failures)} check(s) FAILED: {failures}")
    sys.exit(1)
print("SUMMARY: ALL PASSED")
