"""Task 9 manual verification: the vendor baseline flow against the live dev API.

Two signed-in browser contexts drive the real UI:
  * the vendor context (vendor.one@skipq.test, Charcoal Grill) for the menu,
    the open/close switch, item management, the paid queue and every
    lifecycle control;
  * the diner context (diner.one@skipq.test) to prove the diner's screens
    react to what the vendor does (closed stall, live order moves,
    cancel/refund and no-show notices) and to place one new order that the
    vendor then walks through preparation to collection.
Forbidden/stale/overdue rules are asserted in the UI (no button, read-only
detail) and, where the UI cannot reach them, through the API (cross-stall
403, no-show-too-early 409, closed-stall cart add 409).
Screenshots land in backend/docs/evidence/screenshots/ as task9-*.

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


def ui_login(page, email, home):
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{BASE}{home}", timeout=10000)


def clear_banners(page):
    """Dismiss every queued feedback banner so each step judges its own
    output instead of a stale one from an earlier step (the shared queue
    persists across SPA navigation on purpose)."""
    for close in page.locator(".alert .btn-close").all():
        try:
            close.click(timeout=1000)
        except Exception:
            pass


v1 = None  # vendor.one token (Charcoal Grill)
d1_token = None  # diner.one token


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
    vendor_ctx = browser.new_context()
    vendor = vendor_ctx.new_page()
    diner_ctx = browser.new_context()
    diner = diner_ctx.new_page()
    vendor.on("dialog", lambda dialog: dialog.accept())
    diner.on("dialog", lambda dialog: dialog.accept())

    try:
        # --- tokens and record ids -------------------------------------------
        v1 = login_token("vendor.one@skipq.test")
        d1_token = login_token("diner.one@skipq.test")
        status, s1 = api("GET", "/api/vendor/stall", token=v1)
        stall1_id = s1["stall"]["id"]
        status, menu = api("GET", f"/api/diner/stalls/{stall1_id}/menu", token=d1_token)
        items = {item["name"]: item for item in menu["items"]}
        m1 = items["Charcoal Chicken Rice"]
        m2 = items["Mango Sago"]
        status, orders = api("GET", "/api/diner/orders?view=all", token=d1_token)
        seed_ids = {o["queue_number"]: o for o in orders["items"]}
        check(
            "seed state located (S1 open, M1, M2, seed orders 0001-0007 + 0009)",
            s1["stall"]["is_open"] and m1 and m2 and all(f"Q-seed-000{i}" in seed_ids for i in range(1, 8))
            and "Q-seed-0009" in seed_ids,
            str(seed_ids.keys()),
        )

        # --- 1. vendor login lands on the menu --------------------------------
        ui_login(vendor, "vendor.one@skipq.test", "/vendor/menu")
        expect(vendor.get_by_role("heading", name="Charcoal Grill")).to_be_visible(timeout=5000)
        expect(vendor.locator(".badge", has_text="Open")).to_be_visible()
        rows = vendor.locator(".list-group-item")
        expect(rows).to_have_count(3, timeout=5000)  # M4 (soft-deleted) absent
        expect(vendor.get_by_text("Special Kaya Toast")).to_have_count(0)
        expect(
            vendor.locator(".list-group-item", has_text="Pineapple Tart").locator(".badge", has_text="Sold out")
        ).to_be_visible()
        check("vendor menu lists 3 active items, hides the soft-deleted one, badges sold-out", True)
        vendor.screenshot(path=f"{SHOTS}/task9-01-vendor-menu-open.png")

        # --- 2. open/close switch: closed state blocks new diner adds ---------
        clear_banners(vendor)
        vendor.locator("#stall-trading-switch").click()
        expect(vendor.get_by_role("heading", name="Charcoal Grill").locator(".badge", has_text="Closed")).to_be_visible(timeout=5000)
        expect(vendor.locator(".alert-secondary", has_text="This stall is closed")).to_be_visible()
        check("closing the stall flips the badge and raises the closure banner", True)
        vendor.screenshot(path=f"{SHOTS}/task9-02-closed-banner.png")

        status, err = api("POST", "/api/diner/cart/items", token=d1_token, body={"item_id": m1["id"], "quantity": 3})
        check(
            "a diner cart add is refused 409 stall_closed while the stall is closed",
            status == 409 and err["error"]["code"] == "stall_closed",
            f"{status} {err}",
        )

        # --- 3. the diner sees the closed stall by direct link ----------------
        ui_login(diner, "diner.one@skipq.test", "/diner/stalls")
        diner.goto(f"{BASE}/diner/stalls/{stall1_id}")
        expect(diner.locator(".alert-secondary", has_text="Charcoal Grill is currently closed")).to_be_visible(timeout=5000)
        m1_btn = diner.locator(".list-group-item", has_text="Charcoal Chicken Rice").get_by_role("button")
        expect(m1_btn).to_be_disabled()
        check("the diner's closed-stall view disables every Add control", True)
        diner.screenshot(path=f"{SHOTS}/task9-03-diner-closed-stall.png")

        # --- 4. reopening restores the diner's controls -----------------------
        clear_banners(vendor)
        vendor.locator("#stall-trading-switch").click()
        expect(vendor.get_by_role("heading", name="Charcoal Grill").locator(".badge", has_text="Open")).to_be_visible(timeout=5000)
        expect(m1_btn).to_have_text("Add another (in cart: 2)", timeout=5000)
        check("reopening the stall re-enables the diner's Add control", True)

        # --- 5. the item form rejects a malformed price with the server text -
        vendor.goto(f"{BASE}/vendor/menu/new")
        vendor.get_by_label("Name").fill("Task Nine Tiao")
        vendor.get_by_label("Price").fill("abc")
        vendor.get_by_label("Image URL").fill("https://example.com/images/task-nine-tiao.jpg")
        vendor.get_by_role("button", name="Add item").click()
        expect(
            vendor.locator(".alert-danger", has_text="Price must be a number above 0, below 9999")
        ).to_be_visible(timeout=5000)
        check("the create form shows the backend's own 400 price message", True)
        vendor.screenshot(path=f"{SHOTS}/task9-04-form-rejection.png")

        # --- 6. creating a valid item ------------------------------------------
        clear_banners(vendor)
        vendor.get_by_label("Price").fill("9.99")
        vendor.get_by_label("Description").fill("A noodle dish created by the Task 9 verification run.")
        vendor.get_by_role("button", name="Add item").click()
        expect(vendor).to_have_url(f"{BASE}/vendor/menu", timeout=10000)
        expect(vendor.locator(".alert-success", has_text="Task Nine Tiao was added to your menu.")).to_be_visible()
        new_row = vendor.locator(".list-group-item", has_text="Task Nine Tiao")
        expect(new_row.get_by_text("$9.99")).to_be_visible()
        check("a valid item is created and listed with its price", True)
        vendor.screenshot(path=f"{SHOTS}/task9-05-item-created.png")

        # --- 7. editing the new item -------------------------------------------
        new_row.get_by_role("link", name="Edit").click()
        expect(vendor.get_by_role("heading", name="Edit menu item")).to_be_visible(timeout=5000)
        expect(vendor.get_by_label("Name")).to_have_value("Task Nine Tiao")
        expect(vendor.get_by_label("Price")).to_have_value("9.99")
        vendor.get_by_label("Name").fill("Task Nine Tiao Soup")
        vendor.get_by_label("Price").fill("10.50")
        vendor.get_by_role("button", name="Save item").click()
        expect(vendor).to_have_url(f"{BASE}/vendor/menu", timeout=10000)
        soup_row = vendor.locator(".list-group-item", has_text="Task Nine Tiao Soup")
        expect(soup_row.get_by_text("$10.50")).to_be_visible()
        check("the edit form pre-fills, saves, and the menu shows the new name/price", True)
        vendor.screenshot(path=f"{SHOTS}/task9-06-item-edited.png")

        # --- 8. sold-out toggle on a seeded item --------------------------------
        clear_banners(vendor)
        m2_row = vendor.locator(".list-group-item", has_text="Mango Sago")
        m2_row.get_by_role("button", name="Mark sold out").click()
        expect(m2_row.locator(".badge", has_text="Sold out")).to_be_visible(timeout=5000)
        expect(vendor.locator(".alert-success", has_text="Mango Sago is now marked sold out.")).to_be_visible()
        check("marking a seeded item sold out updates the row and reports it", True)
        vendor.screenshot(path=f"{SHOTS}/task9-07-m2-sold-out.png")
        m2_row.get_by_role("button", name="Restock").click()
        # The badge only — the control's "Mark sold out" label contains the
        # same phrase, so an unscoped text match can never reach zero.
        expect(m2_row.locator(".badge", has_text="Sold out")).to_have_count(0, timeout=5000)
        check("restocking clears the sold-out badge", True)

        # --- 9. removing the run-created item -----------------------------------
        clear_banners(vendor)
        soup_row.get_by_role("button", name="Remove").click()
        expect(vendor.locator(".list-group-item", has_text="Task Nine Tiao")).to_have_count(0, timeout=5000)
        status, menu = api("GET", f"/api/diner/stalls/{stall1_id}/menu", token=d1_token)
        check(
            "removal disappears from the vendor list and the diner's menu",
            status == 200 and all(item["name"] != "Task Nine Tiao Soup" for item in menu["items"]),
            str([item["name"] for item in menu["items"]]),
        )

        # --- 10. paid queue: own-stall only, newest first ------------------------
        vendor.goto(f"{BASE}/vendor/orders")
        queue_rows = vendor.locator(".list-group-item")
        expect(queue_rows).to_have_count(8, timeout=5000)  # 0009 belongs to S2
        expect(vendor.get_by_text("Q-seed-0009")).to_have_count(0)
        expect(queue_rows.first.get_by_text("Q-seed-0003")).to_be_visible()  # newest (-20 min)
        check("the queue lists the stall's 8 paid orders, newest first, no other-stall order", True)
        vendor.screenshot(path=f"{SHOTS}/task9-08-orders-queue.png")

        # --- 11. Pending: only Accept and Reject --------------------------------
        id1 = seed_ids["Q-seed-0001"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id1}")
        expect(vendor.get_by_role("button", name="Accept order")).to_be_visible(timeout=5000)
        expect(vendor.get_by_role("button", name="Reject order")).to_be_visible()
        expect(vendor.get_by_text("Mark ready")).to_have_count(0)
        expect(vendor.get_by_text("Mark collected")).to_have_count(0)
        expect(vendor.get_by_text("Mark no-show")).to_have_count(0)
        check("a Pending order offers only Accept and Reject", True)
        vendor.screenshot(path=f"{SHOTS}/task9-09-pending-controls.png")

        # --- 12. Preparing: only Mark ready (rejection stops once accepted) ------
        # The canonical lifecycle has exactly five edges; Preparing has no
        # Cancelled edge, so a once-accepted order can only move forward.
        id2 = seed_ids["Q-seed-0002"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id2}")
        expect(vendor.get_by_role("button", name="Mark ready")).to_be_visible(timeout=5000)
        expect(vendor.get_by_text("Accept order")).to_have_count(0)
        expect(vendor.get_by_text("Reject order")).to_have_count(0)
        expect(vendor.get_by_text("Mark collected")).to_have_count(0)
        expect(vendor.get_by_text("Mark no-show")).to_have_count(0)
        check("a Preparing order offers only Mark ready — no accept/reject/collected/no-show", True)
        vendor.screenshot(path=f"{SHOTS}/task9-10-preparing-controls.png")

        # --- 13. Ready +5 min: NoShow must NOT appear ----------------------------
        id3 = seed_ids["Q-seed-0003"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id3}")
        expect(vendor.get_by_role("button", name="Mark collected")).to_be_visible(timeout=5000)
        expect(vendor.get_by_text("Mark no-show")).to_have_count(0)
        expect(vendor.get_by_text("Accept order")).to_have_count(0)
        expect(vendor.get_by_text("Reject order")).to_have_count(0)
        check("a Ready order inside the 30-minute window offers only Mark collected", True)
        vendor.screenshot(path=f"{SHOTS}/task9-11-ready-no-noshow.png")

        # --- 14. Ready +35 min: NoShow appears ------------------------------------
        id4 = seed_ids["Q-seed-0004"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id4}")
        expect(vendor.get_by_role("button", name="Mark collected")).to_be_visible(timeout=5000)
        expect(vendor.get_by_role("button", name="Mark no-show")).to_be_visible()
        expect(vendor.get_by_text("Accept order")).to_have_count(0)
        expect(vendor.get_by_text("Reject order")).to_have_count(0)
        check("a Ready order past 30 minutes offers exactly Collected and NoShow", True)
        vendor.screenshot(path=f"{SHOTS}/task9-12-ready-with-noshow.png")

        # --- 15. terminal Cancelled: read-only with the refund ---------------------
        id6 = seed_ids["Q-seed-0006"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id6}")
        clear_banners(vendor)  # queued banner dismiss buttons would inflate the count
        expect(vendor.get_by_text("This order is final; it can no longer be changed.")).to_be_visible(timeout=5000)
        for label in ("Accept order", "Reject order", "Mark ready", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_text(label)).to_have_count(0)
        expect(vendor.locator(".alert-warning", has_text="was refunded")).to_be_visible()
        check("a Cancelled order is read-only and shows the refund", True)
        vendor.screenshot(path=f"{SHOTS}/task9-13-terminal-cancelled.png")

        # --- 16. terminal NoShow: read-only, payment stays paid -------------------
        id7 = seed_ids["Q-seed-0007"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id7}")
        clear_banners(vendor)
        expect(vendor.get_by_text("This order is final; it can no longer be changed.")).to_be_visible(timeout=5000)
        for label in ("Accept order", "Reject order", "Mark ready", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_text(label)).to_have_count(0)
        expect(vendor.locator(".alert-warning", has_text="stays paid")).to_be_visible()
        check("a NoShow order is read-only and keeps its payment paid", True)
        vendor.screenshot(path=f"{SHOTS}/task9-14-terminal-noshow.png")

        # --- 17. terminal Collected: stale purchase snapshot -----------------------
        id5 = seed_ids["Q-seed-0005"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id5}")
        clear_banners(vendor)
        expect(vendor.get_by_text("Grilled Chicken Rice")).to_be_visible(timeout=5000)  # old snapshot name
        expect(vendor.get_by_text("$6.00").first).to_be_visible()  # old snapshot price (also the total)
        for label in ("Accept order", "Reject order", "Mark ready", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_text(label)).to_have_count(0)
        check("a Collected order is read-only and keeps its stale name/price snapshot", True)
        vendor.screenshot(path=f"{SHOTS}/task9-15-terminal-collected-snapshot.png")

        # --- 18. other-stall order is forbidden in the vendor UI --------------------
        id9 = seed_ids["Q-seed-0009"]["id"]
        vendor.goto(f"{BASE}/vendor/orders/{id9}")
        # The screen's own error text (the shared banner repeats it too, so
        # scope to the error screen's paragraph rather than page-wide text).
        expect(
            vendor.locator("p.text-secondary", has_text="You can only manage orders for your own stall.")
        ).to_be_visible(timeout=5000)
        check("another stall's order shows the 403 screen, not its data", True)
        vendor.screenshot(path=f"{SHOTS}/task9-16-forbidden-order.png")

        # --- 19. the 30-minute NoShow guard also refuses at the API ------------------
        status, err = api("PATCH", f"/api/vendor/orders/{id3}/status", token=v1, body={"status": "NoShow"})
        check(
            "NoShow before 30 minutes is refused 409 no_show_too_early",
            status == 409 and err["error"]["code"] == "no_show_too_early",
            f"{status} {err}",
        )

        # --- 20. closure preserves paid-queue access ----------------------------------
        clear_banners(vendor)
        vendor.goto(f"{BASE}/vendor/menu")
        vendor.locator("#stall-trading-switch").click()
        expect(vendor.locator(".alert-secondary", has_text="This stall is closed")).to_be_visible(timeout=5000)
        vendor.goto(f"{BASE}/vendor/orders")
        expect(vendor.locator(".alert-secondary", has_text="closed")).to_be_visible(timeout=5000)
        expect(vendor.locator(".list-group-item")).to_have_count(8, timeout=5000)
        expect(vendor.get_by_role("link", name="Manage").first).to_be_enabled()
        check("a closed stall keeps its whole paid queue accessible", True)
        vendor.screenshot(path=f"{SHOTS}/task9-17-closed-queue-accessible.png")
        clear_banners(vendor)
        vendor.goto(f"{BASE}/vendor/menu")
        vendor.locator("#stall-trading-switch").click()
        expect(vendor.get_by_role("heading", name="Charcoal Grill").locator(".badge", has_text="Open")).to_be_visible(timeout=5000)

        # --- 21. diner places a fresh order through the UI ----------------------------
        diner.goto(f"{BASE}/diner/checkout")
        expect(diner.get_by_role("heading", name="Checkout")).to_be_visible(timeout=5000)
        clear_banners(diner)
        pay_btn = diner.get_by_role("button", name=re.compile(r"Pay \$15\.50"))
        pay_btn.click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        queue_number = (
            diner.locator("p strong", has_text=re.compile(r"Queue number: Q-")).inner_text().split("Queue number: ")[1].strip()
        )
        assert re.match(r"^Q-[0-9a-f]{32}$", queue_number), queue_number
        check("the diner's seeded cart pays out ($15.50) with a fresh queue number", True, queue_number)
        diner.screenshot(path=f"{SHOTS}/task9-18-diner-checkout-success.png")

        status, orders = api("GET", "/api/diner/orders?view=current", token=d1_token)
        new_order = next(o for o in orders["items"] if o["queue_number"] == queue_number)
        created_order_ids.append(new_order["id"])
        check(
            "the new order is Pending, Paid, $15.50, 2x M1 + 1x M2 snapshots",
            new_order["status"] == "Pending"
            and new_order["payment"]["status"] == "Paid"
            and new_order["total_cents"] == 1550
            and {i["name"]: i["quantity"] for i in new_order["items"]}
            == {"Charcoal Chicken Rice": 2, "Mango Sago": 1},
            str(new_order),
        )

        # --- 22. the vendor's queue polls it in; Accept moves it to Preparing -------
        vendor.goto(f"{BASE}/vendor/orders")
        new_link = vendor.get_by_role("link", name=queue_number).first
        expect(new_link).to_be_visible(timeout=10000)  # polling surfaces it within a tick
        new_link.click()
        expect(vendor.get_by_role("button", name="Accept order")).to_be_visible(timeout=5000)
        clear_banners(vendor)
        vendor.get_by_role("button", name="Accept order").click()
        expect(vendor.get_by_role("heading", name=queue_number).locator(".badge", has_text="Preparing")).to_be_visible(timeout=5000)
        check("the vendor's queue surfaces the new order and Accept moves it to Preparing", True)
        vendor.screenshot(path=f"{SHOTS}/task9-19-vendor-accepted.png")

        # --- 23. the diner's tracking shows Preparing without a manual refresh -------
        diner.goto(f"{BASE}/diner/orders/{new_order['id']}")
        expect(diner.locator(".badge", has_text="Preparing")).to_be_visible(timeout=10000)
        check("the diner's tracking observes Preparing via polling", True)
        diner.screenshot(path=f"{SHOTS}/task9-20-diner-preparing.png")

        # --- 24. Mark ready: the diner's Ready banner appears ------------------------
        vendor.get_by_role("button", name="Mark ready").click()
        expect(vendor.locator(".badge", has_text="Ready")).to_be_visible(timeout=5000)
        expect(diner.locator(".alert-success", has_text="Your order is ready.")).to_be_visible(timeout=10000)
        check("Mark ready is mirrored on the diner's tracking screen as the Ready banner", True)
        diner.screenshot(path=f"{SHOTS}/task9-21-diner-ready-banner.png")

        # --- 25. Mark collected: terminal for both personas --------------------------
        vendor.get_by_role("button", name="Mark collected").click()
        expect(vendor.locator(".badge", has_text="Collected")).to_be_visible(timeout=5000)
        expect(vendor.get_by_text("This order is final; it can no longer be changed.")).to_be_visible()
        check("Mark collected ends the order read-only on the vendor side", True)
        vendor.screenshot(path=f"{SHOTS}/task9-22-vendor-collected.png")
        expect(diner.locator(".alert-secondary", has_text="Collected")).to_be_visible(timeout=10000)
        check("the diner's tracking shows the terminal Collected notice", True)
        diner.screenshot(path=f"{SHOTS}/task9-23-diner-collected.png")

        # --- 26. the stored record reflects the finished walk -------------------------
        status, data = api("GET", f"/api/diner/orders/{new_order['id']}", token=d1_token)
        stored = data["order"]
        check(
            "the stored order is Collected with its payment still Paid",
            stored["status"] == "Collected"
            and stored["payment"]["status"] == "Paid"
            and stored["payment"]["amount_cents"] == 1550
            and stored["ready_at"] is not None,
            str(stored["status"]),
        )

        # --- 27. cancellation/refund on a seeded case, diner-visible -------------------
        vendor.goto(f"{BASE}/vendor/orders/{id1}")
        expect(vendor.get_by_role("button", name="Reject order")).to_be_visible(timeout=5000)
        clear_banners(vendor)
        vendor.get_by_role("button", name="Reject order").click()
        expect(vendor.locator(".badge", has_text="Cancelled")).to_be_visible(timeout=5000)
        expect(vendor.locator(".alert-warning", has_text="was refunded")).to_be_visible()
        check("Rejecting a Pending order marks it Cancelled with the refund", True)
        vendor.screenshot(path=f"{SHOTS}/task9-24-cancel-refund.png")

        diner.goto(f"{BASE}/diner/orders/{id1}")
        expect(
            diner.locator(".alert-warning", has_text=re.compile(r"was cancelled and its PayNow payment of \$13\.00 was refunded"))
        ).to_be_visible(timeout=10000)
        check("the diner sees the cancellation with the refunded amount", True)
        diner.screenshot(path=f"{SHOTS}/task9-25-diner-cancelled.png")

        # --- 28. no-show on the +35-minute Ready order, diner-visible ------------------
        vendor.goto(f"{BASE}/vendor/orders/{id4}")
        expect(vendor.get_by_role("button", name="Mark no-show")).to_be_visible(timeout=5000)
        clear_banners(vendor)
        vendor.get_by_role("button", name="Mark no-show").click()
        expect(vendor.locator(".badge", has_text="NoShow")).to_be_visible(timeout=5000)
        expect(vendor.locator(".alert-warning", has_text="stays paid")).to_be_visible()
        check("Mark no-show is accepted past the 30-minute window", True)
        vendor.screenshot(path=f"{SHOTS}/task9-26-vendor-noshow.png")

        diner.goto(f"{BASE}/diner/orders/{id4}")
        expect(diner.locator(".alert-warning", has_text="The payment stays paid.")).to_be_visible(timeout=10000)
        check("the diner sees the no-show notice with the payment staying paid", True)
        diner.screenshot(path=f"{SHOTS}/task9-27-diner-noshow.png")

        # --- 29. a diner account cannot open the vendor area ----------------------------
        diner.goto(f"{BASE}/vendor/menu")
        expect(diner).to_have_url(f"{BASE}/diner/stalls", timeout=5000)
        check("a diner account is routed out of the vendor area to their own home", True)

        vendor_ctx.close()
        diner_ctx.close()
    finally:
        # --- cleanup: delete the run's orders, D1's leftover cart and the
        # run-created menu items, then leave the reseed to the final step.
        try:
            subprocess.run(
                [
                    f"{BACKEND}/.venv/bin/python",
                    "-c",
                    (
                        "from mongoengine import connect; "
                        "connect('skipq_system_test', host='mongodb://127.0.0.1:27017', connect=False); "
                        "from app.models.order import Order; from app.models.cart import Cart; "
                        "from app.models.user import User; from app.models.menu_item import MenuItem; "
                        "d1 = User.objects(email='diner.one@skipq.test').first(); "
                        "orders = Order.objects(queue_number__regex=r'^Q-[0-9a-f]{32}$').delete(); "
                        "carts = Cart.objects(diner=d1).delete(); "
                        "items = MenuItem.objects(name__startswith='Task Nine').delete(); "
                        "print(f'cleaned orders={orders} carts={carts} run_items={items}')"
                    ),
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=BACKEND,
            )
            print("cleanup: OK")
        except Exception as exc:  # noqa: BLE001
            check(f"cleanup ran ({exc})", False)
        browser.close()

# Final re-seed and invariant check (restores the seed orders' statuses, S2
# closed, M1/M2 available, C1 back to 2x M1 + 1x M2).
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
