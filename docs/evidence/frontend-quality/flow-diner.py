"""Task 8 manual verification: the full diner flow against the live dev API.

Diner side is driven through the real UI (one Playwright context, UI login);
vendor-side state changes (sold-out toggle, price change, order transitions,
stall open/close) are made with the vendor API so the diner's screens must
react to real server state. Screenshots land in
backend/docs/evidence/screenshots/.

Scenario:
  1. diner login -> stall list
  2. menu with a seeded sold-out item (greyed out, control disabled)
  3. newly observed sold-out change raises the toast while polling
  4. add-to-cart from the menu ("Add another" increments the line)
  5. cart editing: quantity stepper and removal, server total updates
  6. checkout loads the server fingerprint; a price change underneath the
     open checkout page is refused (stale-cart screen), then
     refresh-and-retry succeeds
  7. tracking: Pending -> Preparing -> Ready banner -> Collected (polling
     stops at the terminal state)
  8. simulated payment failure keeps one checkout key; retry succeeds
  9. double-click on the Pay control stores exactly one order
 10. a vendor-sold-out line is refused at checkout; removing it succeeds
 11. cross-stall add is refused while the cart holds another stall's items
 12. a forged token's 401 returns the diner to sign-in

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
created_order_ids = []


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


v1 = None  # vendor.one token (Charcoal Grill)
v2 = None  # vendor.two token (Noodle Bar)


def diner_login(page, email="diner.one@skipq.test"):
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()


def clear_banners(page):
    """Dismiss every queued feedback banner so each step judges its own
    output instead of a stale one from an earlier step (the shared queue
    persists across SPA navigation on purpose)."""
    for close in page.locator(".alert .btn-close").all():
        try:
            close.click(timeout=1000)
        except Exception:
            pass


# Start from the seeded state (idempotent upserts; any residue from a prior
# partial run is overwritten).
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
    diner_ctx = browser.new_context()
    diner = diner_ctx.new_page()
    payment_keys = []
    def capture_payment(request):
        if request.method == 'POST' and request.url == API + '/api/diner/orders':
            payment_keys.append(request.post_data_json['checkout_key'])
    diner.on('request', capture_payment)

    try:
        # --- vendor API tokens and record ids -------------------------------
        v1 = login_token("vendor.one@skipq.test")
        v2 = login_token("vendor.two@skipq.test")
        status, s1 = api("GET", "/api/vendor/stall", token=v1)
        stall1_id = s1["stall"]["id"]
        status, s2 = api("GET", "/api/vendor/stall", token=v2)
        stall2_id = s2["stall"]["id"]
        status, menu = api("GET", f"/api/diner/stalls/{stall1_id}/menu", token=login_token("diner.one@skipq.test"))
        items = {item["name"]: item for item in menu["items"]}
        m1 = items["Charcoal Chicken Rice"]
        m2 = items["Mango Sago"]
        m5_id = None
        status, menu2 = api("GET", f"/api/vendor/menu", token=v2)
        for item in menu2["items"]:
            if item["name"] == "Hokkien Mee":
                m5_id = item["id"]
        check("seed state located (S1, S2, M1, M2, M5)", stall1_id and stall2_id and m1 and m2 and m5_id)

        # --- 1. diner login -> stall list ------------------------------------
        diner_login(diner)
        expect(diner).to_have_url(f"{BASE}/diner/stalls")
        expect(diner.get_by_role("heading", name="Stalls")).to_be_visible(timeout=5000)
        expect(diner.get_by_role("link", name="Charcoal Grill").first).to_be_visible()
        check("diner login lands on the open-stall list", True)
        diner.screenshot(path=f"{SHOTS}/task8-01-stalls.png")

        # --- 2. menu: seeded sold-out item is greyed with control disabled ---
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        m3_row = diner.locator(".list-group-item", has_text="Pineapple Tart")
        expect(m3_row.get_by_role("button", name="Sold out")).to_be_visible(timeout=5000)
        check("seeded sold-out item shows a disabled 'Sold out' control", not m3_row.get_by_role("button", name="Sold out").is_enabled())
        diner.screenshot(path=f"{SHOTS}/task8-02-menu-sold-out.png")

        # --- 3. newly observed sold-out change raises a toast ----------------
        clear_banners(diner)
        status, _ = api("PATCH", f"/api/vendor/menu/{m1['id']}", token=v1, body={"is_available": False})
        expect(diner.locator(".alert-warning", has_text="Charcoal Chicken Rice is no longer available")).to_be_visible(timeout=10000)
        check("polling observes the new sold-out state and toasts it", True)
        diner.screenshot(path=f"{SHOTS}/task8-03-sold-out-toast.png")
        status, _ = api("PATCH", f"/api/vendor/menu/{m1['id']}", token=v1, body={"is_available": True})

        # --- 4. add-to-cart from the menu (increment, not reset) -------------
        # Seed cart C1 = 2x M1 + 1x M2. The control must read the line state.
        clear_banners(diner)
        m1_btn = diner.locator(".list-group-item", has_text="Charcoal Chicken Rice").get_by_role("button")
        expect(m1_btn).to_have_text("Add another (in cart: 2)", timeout=5000)
        m1_btn.click()
        expect(diner.locator(".alert-success", has_text="Charcoal Chicken Rice added")).to_be_visible(timeout=5000)
        # total: 3x 650 + 1x 250 = 2200
        expect(diner.locator(".card-body span strong", has_text="$22.00")).to_be_visible()
        check("menu add increments the existing line (server total $22.00)", True)
        diner.screenshot(path=f"{SHOTS}/task8-04-menu-after-add.png")

        # --- 5. cart editing --------------------------------------------------
        diner.goto(f"{BASE}/diner/cart")
        m1_line = diner.locator(".list-group-item", has_text="Charcoal Chicken Rice")
        m1_line.get_by_role("button", name="Decrease quantity of Charcoal Chicken Rice").click()
        expect(diner.locator("strong", has_text="$15.50")).to_be_visible(timeout=5000)
        check("cart decrement returns the total to $15.50", True)
        m2_line = diner.locator(".list-group-item", has_text="Mango Sago")
        m2_line.get_by_role("button", name="Increase quantity of Mango Sago").click()
        expect(diner.locator("strong", has_text="$18.00")).to_be_visible(timeout=5000)
        check("cart increment updates the server total to $18.00", True)
        m2_line.get_by_role("button", name="Remove Mango Sago from the cart").click()
        expect(diner.locator(".list-group-item", has_text="Mango Sago")).to_have_count(0, timeout=5000)
        expect(diner.locator("strong", has_text="$13.00")).to_be_visible(timeout=5000)
        check("cart removal drops the line and the total to $13.00", True)
        diner.screenshot(path=f"{SHOTS}/task8-05-cart-edited.png")

        # --- 6. checkout: stale price refused, refresh-and-retry succeeds ----
        diner.goto(f"{BASE}/diner/checkout")
        expect(diner.get_by_role("heading", name="Checkout")).to_be_visible(timeout=5000)
        status, before = api("GET", "/api/diner/cart", token=diner.evaluate("() => JSON.parse(sessionStorage.getItem('skipq.session')).token"))
        assert status == 200
        fingerprint_before = before["cart"]["fingerprint"]
        assert len(fingerprint_before) == 64, f"fingerprint: {fingerprint_before!r}"
        expect(diner.get_by_role("button", name="Pay $13.00", exact=True)).to_be_enabled()
        check("checkout shows the server total and an enabled payment action", True)
        diner.screenshot(path=f"{SHOTS}/task8-06-checkout.png")

        # Price changes underneath the open checkout page (fingerprint goes stale).
        # The vendor API takes the price as a decimal dollar string.
        status, _ = api("PATCH", f"/api/vendor/menu/{m1['id']}", token=v1, body={"price": "7.25"})
        assert status == 200, f"price PATCH failed: {status}"
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible(timeout=10000)
        check("a price change under the open checkout page is refused (stale-cart screen)", True)
        diner.screenshot(path=f"{SHOTS}/task8-07-checkout-stale-refused.png")

        diner.get_by_role("button", name="Refresh and retry").click()
        expect(diner.get_by_role("button", name="Pay $14.50", exact=True)).to_be_enabled()
        # Cart is 2x M1 at the new 725c price = $14.50.
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$14\.50"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        queue_number = diner.locator("p strong", has_text=re.compile(r"Queue number: Q-")).inner_text().split("Queue number: ")[1]
        check("refresh-and-retry stores the order with the fresh fingerprint", True, queue_number)
        diner.screenshot(path=f"{SHOTS}/task8-08-checkout-success.png")

        diner_token = diner.evaluate("() => JSON.parse(sessionStorage.getItem('skipq.session')).token")
        status, orders = api("GET", "/api/diner/orders?view=current", token=diner_token)
        order_a = next(o for o in orders["items"] if o["queue_number"] == queue_number)
        # One cart line (2x M1) stores as one snapshot line with quantity 2.
        check("the stored order is Pending, Paid, $14.50 with the 2x M1 snapshot", order_a["status"] == "Pending"
              and order_a["payment"]["status"] == "Paid" and order_a["total_cents"] == 1450
              and len(order_a["items"]) == 1 and order_a["items"][0]["quantity"] == 2
              and order_a["items"][0]["name"] == "Charcoal Chicken Rice"
              and order_a["items"][0]["price_cents"] == 725, str(order_a))
        created_order_ids.append(order_a["id"])

        # --- 7. tracking: Pending -> Preparing -> Ready banner -> Collected --
        diner.goto(f"{BASE}/diner/orders/{order_a['id']}")
        expect(diner.get_by_role("heading", name=re.compile(order_a["queue_number"]))).to_be_visible(timeout=5000)
        check("tracking page shows the queue number and Pending status", True)
        diner.screenshot(path=f"{SHOTS}/task8-09-tracking-pending.png")

        status, _ = api("PATCH", f"/api/vendor/orders/{order_a['id']}/status", token=v1, body={"status": "Preparing"})
        expect(diner.locator(".badge", has_text="Preparing")).to_be_visible(timeout=10000)
        check("polling picks up Preparing without a manual refresh", True)

        status, _ = api("PATCH", f"/api/vendor/orders/{order_a['id']}/status", token=v1, body={"status": "Ready"})
        expect(diner.locator(".alert-success", has_text="Your order is ready.")).to_be_visible(timeout=10000)
        check("the Ready-for-collection banner appears when tracking observes Ready", True)
        diner.screenshot(path=f"{SHOTS}/task8-10-tracking-ready.png")

        status, _ = api("PATCH", f"/api/vendor/orders/{order_a['id']}/status", token=v1, body={"status": "Collected"})
        expect(diner.locator(".alert-secondary", has_text="Collected")).to_be_visible(timeout=10000)
        check("terminal Collected state is shown (polling now stops)", True)
        diner.screenshot(path=f"{SHOTS}/task8-11-tracking-collected.png")

        # --- 8. simulated payment failure keeps one checkout key --------------
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        clear_banners(diner)
        diner.locator(".list-group-item", has_text="Mango Sago").get_by_role("button", name="Add").click()
        expect(diner.locator(".alert-success", has_text="Mango Sago added")).to_be_visible(timeout=5000)
        diner.goto(f"{BASE}/diner/checkout")
        diner.get_by_label("Simulate this payment failing (demo control)").check()
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$2\.50"))
        pay_btn.click()
        expect(diner.locator(".alert-danger", has_text="Payment was not completed")).to_be_visible(timeout=10000)
        check("failed simulation is refused with the retained-key notice", True)
        diner.screenshot(path=f"{SHOTS}/task8-12-payment-failed.png")

        diner.get_by_label("Simulate this payment failing (demo control)").uncheck()
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$2\.50"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        assert payment_keys[-1] == payment_keys[-2], "Payment retry must retain the same checkout key"
        check("retry with the retained checkout key stores exactly one order", True)
        diner_token = diner.evaluate("() => JSON.parse(sessionStorage.getItem('skipq.session')).token")
        status, orders = api("GET", "/api/diner/orders?view=current", token=diner_token)
        mango_orders = [o for o in orders["items"] if o["total_cents"] == 250 and o["payment"]["method"] == "PayNow"]
        check("only one $2.50 order exists (the failed attempt persisted nothing)", len(mango_orders) == 1, str(len(mango_orders)))
        order_b = mango_orders[0]
        created_order_ids.append(order_b["id"])
        diner.screenshot(path=f"{SHOTS}/task8-13-payment-retry-success.png")

        # --- 9. double-click stores exactly one order -------------------------
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        clear_banners(diner)
        with diner.expect_response(lambda r: r.url.endswith("/api/diner/cart/items") and r.request.method == "POST") as add_info:
            diner.locator(".list-group-item", has_text="Charcoal Chicken Rice").get_by_role("button", name=re.compile(r"^Add")).click()
        assert add_info.value.status == 201, f"add failed: {add_info.value.status} {add_info.value.json()}"
        expect(diner.locator(".alert-success", has_text="Charcoal Chicken Rice added")).to_be_visible(timeout=5000)
        diner.goto(f"{BASE}/diner/checkout")
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$7\.25"))
        expect(pay_btn).to_be_visible(timeout=10000)
        # Two DOM clicks in one JS task: both reach the handler before React
        # can re-render the disabled/progress state, so exactly this sequence
        # exercises the synchronous re-entry guard.
        pay_btn.evaluate("el => { el.click(); el.click(); }")
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        diner_token = diner.evaluate("() => JSON.parse(sessionStorage.getItem('skipq.session')).token")
        status, orders = api("GET", "/api/diner/orders?view=current", token=diner_token)
        rice_orders = [o for o in orders["items"] if o["total_cents"] == 725]
        check("double-click on the Pay control stored exactly one order", len(rice_orders) == 1, str(len(rice_orders)))
        created_order_ids.append(rice_orders[0]["id"])
        diner.screenshot(path=f"{SHOTS}/task8-14-double-click-single-order.png")

        # --- 10. vendor-sold-out line is refused, then removed, then paid -----
        # Cart is empty after step 9's success: build 1x M1 + 1x M2 (975c).
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        clear_banners(diner)
        diner.locator(".list-group-item", has_text="Charcoal Chicken Rice").get_by_role("button", name="Add").click()
        expect(diner.locator(".alert-success", has_text="Charcoal Chicken Rice added")).to_be_visible(timeout=5000)
        diner.locator(".list-group-item", has_text="Mango Sago").get_by_role("button", name="Add").click()
        expect(diner.locator(".alert-success", has_text="Mango Sago added")).to_be_visible(timeout=5000)
        diner.goto(f"{BASE}/diner/checkout")
        expect(diner.get_by_role("button", name="Pay $9.75", exact=True)).to_be_enabled()
        status, _ = api("PATCH", f"/api/vendor/menu/{m2['id']}", token=v1, body={"is_available": False})
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$9\.75"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible(timeout=10000)
        check("a line that sold out before payment is refused at checkout", True)
        diner.screenshot(path=f"{SHOTS}/task8-15-stale-sold-out-refused.png")

        diner.get_by_role("link", name="Review your cart").click()
        expect(diner.get_by_role("heading", name="Your cart")).to_be_visible(timeout=5000)
        diner.locator(".list-group-item", has_text="Mango Sago").get_by_role("button", name="Remove Mango Sago from the cart").click()
        expect(diner.locator("strong", has_text="$7.25")).to_be_visible(timeout=5000)
        check("removing the sold-out line leaves a payable cart", True)
        diner.get_by_role("link", name="Continue to checkout").click()
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$7\.25"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        diner_token = diner.evaluate("() => JSON.parse(sessionStorage.getItem('skipq.session')).token")
        status, orders = api("GET", "/api/diner/orders?view=current", token=diner_token)
        order_d = next(o for o in orders["items"] if o["total_cents"] == 725 and o["id"] not in created_order_ids)
        created_order_ids.append(order_d["id"])
        check("the remaining line pays out after the sold-out line is removed", True)
        diner.screenshot(path=f"{SHOTS}/task8-16-after-removal-paid.png")

        # --- 11. cross-stall add is refused -----------------------------------
        # Cart is empty again: hold one S1 line, then try to add an S2 line.
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        clear_banners(diner)
        diner.locator(".list-group-item", has_text="Charcoal Chicken Rice").get_by_role("button", name="Add").click()
        expect(diner.locator(".alert-success", has_text="Charcoal Chicken Rice added")).to_be_visible(timeout=5000)
        status, _ = api("PATCH", "/api/vendor/stall", token=v2, body={"is_open": True})
        diner.goto(f"{BASE}/diner/stalls/{stall2_id}")
        expect(diner.get_by_role("heading", name="Noodle Bar")).to_be_visible(timeout=5000)
        m5_row = diner.locator(".list-group-item", has_text="Hokkien Mee")
        m5_row.get_by_role("button", name="Add").click()
        expect(diner.locator(".alert-danger", has_text="Charcoal Grill")).to_be_visible(timeout=5000)
        check("adding from a second stall is refused while the cart holds the first", True)
        diner.screenshot(path=f"{SHOTS}/task8-17-cross-stall-refused.png")
        status, _ = api("PATCH", "/api/vendor/stall", token=v2, body={"is_open": False})

        # --- 12. forged token returns the diner to sign-in --------------------
        diner.evaluate("() => { const s = JSON.parse(sessionStorage.getItem('skipq.session')); s.token = 'forged-token'; sessionStorage.setItem('skipq.session', JSON.stringify(s)); }")
        diner.goto(f"{BASE}/diner/cart")
        expect(diner).to_have_url(f"{BASE}/login", timeout=10000)
        check("a forged token's 401 clears the session and presents sign-in", True)
        diner.screenshot(path=f"{SHOTS}/task8-18-forged-token-sign-in.png")

        diner_ctx.close()
    finally:
        # --- cleanup: delete the run's orders, drop D1's leftover cart -------
        # Orders have no public delete route: remove them through the model.
        try:
            subprocess.run(
                [
                    f"{BACKEND}/.venv/bin/python",
                    "-c",
                    (
                        "import json, sys; "
                        "from mongoengine import connect; "
                        "connect('skipq_system_test', host='mongodb://127.0.0.1:27017', connect=False); "
                        "from app.models.order import Order; from app.models.cart import Cart; "
                        "from app.models.user import User; from bson import ObjectId; "
                        "d1 = User.objects(email='diner.one@skipq.test').first(); "
                        "run_pattern = Order.objects(queue_number__regex=r'^Q-[0-9a-f]{32}$'); "
                        "orders = run_pattern.count(); "
                        "run_pattern.delete(); "
                        "carts = Cart.objects(diner=d1).delete(); "
                        "leftover = Order.objects(queue_number__regex=r'^Q-[0-9a-f]{32}$').count(); "
                        "print(f'cleaned orders={orders} carts={carts} leftover_run_orders={leftover}')"
                    ),
                    json.dumps(created_order_ids),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            print("cleanup: OK")
        except Exception as exc:  # noqa: BLE001
            check(f"cleanup ran ({exc})", False)
        browser.close()

# Final re-seed and invariant check (restores M1 to 650c, C1 to 2x M1 + 1x M2,
# S2 closed).
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
