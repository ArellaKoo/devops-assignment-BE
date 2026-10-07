"""Q7(a) demo script: executes the screencast's exact steps headlessly.

This is NOT the submission recording — the narrated ≤8-minute 720p MP4 is
recorded by the student following ``script.md``. This script exists to
verify that every step of that script executes against the running app and
produces the expected visible outcome, including both rule violations:

- Phase A: the diner signs in and places one order; the vendor signs in and
  moves *that same order* to Collected (the two-persona lifecycle).
- Phase B (violation 1): the diner adds an available item, the vendor marks
  it sold out, and the diner's checkout is visibly refused with the cart
  retained and no new order stored.
- Phase C (violation 2): the diner adds an available item, the vendor closes
  the stall, and the diner's checkout is visibly refused.

Run from ``backend/`` with the guarded ``skipq_system_test`` database and
both servers running (the API against that database on 127.0.0.1:5001, the
CRA dev server on 127.0.0.1:5173 — see recording-steps.md). The script
verifies the seed state at start, performs the demo through the UI in two
logged-in contexts, verifies each expected visible outcome, captures
per-step screenshots in ``demo-screenshots/``, then deletes only the run's
own order, clears the test diner's cart, restores the two vendor-side
states it changed (item availability, stall trading state), and re-verifies
the seed invariants.

Exit code 0 with ``DEMO SCRIPT: ALL STEPS PASSED`` on success.
"""

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the backend/ root, so `app` imports

from playwright.sync_api import expect, sync_playwright

API_BASE = "http://127.0.0.1:5001"
WEB_BASE = "http://127.0.0.1:5173"
STALL = "Charcoal Grill"
M1 = "Charcoal Chicken Rice"
M2 = "Mango Sago"
DINER = ("diner.one@skipq.test", "SkipQDemo2026!")
VENDOR = ("vendor.one@skipq.test", "SkipQDemo2026!")
QUEUE_RE = re.compile(r"^Q-[0-9a-f]{32}$")
OUT = Path(__file__).resolve().parent / "demo-screenshots"
POLL_TIMEOUT = 15_000  # the UI polls every 3 s; allows two polls plus margin


def shot(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / f"{name}.png"))
    print(f"  [shot] {name}")


def preflight() -> None:
    """Both servers up, the guarded database in seed state."""
    try:
        urllib.request.urlopen(f"{API_BASE}/api/diner/stalls", timeout=5)
        raise AssertionError("API answered 200 without a token — unexpected; is a different app on 5001?")
    except urllib.error.HTTPError as err:
        assert err.code == 401, f"API should refuse with 401, got {err.code}"
    with urllib.request.urlopen(f"{WEB_BASE}/", timeout=5) as resp:
        body = resp.read().decode("utf-8", "replace")
        assert "root" in body, "CRA dev server is not serving the React app at :5173"

    db = os.environ.get("MONGODB_DB", "skipq_system_test")
    assert re.fullmatch(r"skipq_system_test(_[a-z0-9]+)?", db), (
        "demo script refuses to run against anything but the guarded system-test database name"
    )

    import mongoengine
    from app.models.order import Order
    from app.models.user import User

    mongoengine.connect(db=db, host=os.environ.get("MONGODB_HOST", "mongodb://127.0.0.1:27017"),
                        alias="default", connect=False, uuidRepresentation="standard")
    assert User.objects(email=DINER[0]).first(), "seed diner missing — run the seed first"
    assert User.objects(email=VENDOR[0]).first(), "seed vendor missing — run the seed first"
    seeds = Order.objects(queue_number__regex=r"^Q-seed-").count()
    assert seeds == 9, f"expected 9 seed orders, found {seeds} — run the seed first"
    leftover = Order.objects(queue_number__regex=r"^Q-[0-9a-f]{32}$").count()
    assert leftover == 0, f"a previous run left {leftover} run orders — clean up before recording"
    print("preflight: servers up, seed state verified (9 seed orders, 0 run orders)")


def ui_login(page, email: str, home: str) -> None:
    page.goto(f"{WEB_BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill("SkipQDemo2026!")
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(re.compile(re.escape(home)), timeout=15_000)


def stall_menu_link(diner) -> None:
    diner.locator(".list-group-item").filter(has_text=STALL).get_by_role("link", name="View menu").click()
    expect(diner).to_have_url(re.compile(r"/diner/stalls/[0-9a-f]{24}"), timeout=15_000)


def clear_cart(diner) -> None:
    """Remove every seeded cart line so the demo starts from an empty cart."""
    diner.goto(f"{WEB_BASE}/diner/cart")
    expect(diner.get_by_text("Loading your cart…")).to_be_hidden(timeout=15_000)
    lines = diner.locator(".list-group-item")
    remaining = lines.count()
    while remaining:
        lines.first.locator(".btn-outline-danger").click()
        expect(lines).to_have_count(remaining - 1, timeout=15_000)
        remaining -= 1
    expect(diner.get_by_text("Your cart is empty.")).to_be_visible(timeout=15_000)


def main() -> None:
    preflight()
    import requests

    token = requests.post(f"{API_BASE}/api/user/gettoken",
                          json={"email": VENDOR[0], "password": VENDOR[1]}, timeout=10).json()["token"]

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        diner_ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        vendor_ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        diner = diner_ctx.new_page()
        vendor = vendor_ctx.new_page()
        diner.set_default_timeout(15_000)
        vendor.set_default_timeout(15_000)

        # ---------------- Phase A: the same order through both personas ----
        print("Phase A: diner places an order, vendor moves it to Collected")
        ui_login(diner, DINER[0], f"{WEB_BASE}/diner/stalls")
        clear_cart(diner)
        shot(diner, "demo-01-diner-empty-cart")
        diner.goto(f"{WEB_BASE}/diner/stalls")
        expect(diner.locator(".list-group-item").filter(has_text=STALL).locator(".badge", has_text="Open")).to_be_visible()
        shot(diner, "demo-02-diner-stalls")
        stall_menu_link(diner)
        shot(diner, "demo-03-diner-menu")

        m1_row = diner.locator(".list-group-item").filter(has_text=M1)
        m1_row.get_by_role("button", name=re.compile(r"^Add")).click()
        expect(m1_row.get_by_role("button", name=re.compile(r"^Add another \(in cart: 1\)"))).to_be_visible()
        shot(diner, "demo-04-diner-added-m1")
        diner.get_by_role("link", name="Review your cart").click()
        expect(diner).to_have_url(f"{WEB_BASE}/diner/cart")
        expect(diner.locator(".list-group-item").filter(has_text=M1)).to_contain_text("$6.50")
        shot(diner, "demo-05-diner-cart")
        diner.get_by_role("link", name="Continue to checkout").click()
        expect(diner).to_have_url(f"{WEB_BASE}/diner/checkout")
        expect(diner.locator("#simulate-failure")).not_to_be_checked()
        diner.get_by_role("button", name="Pay $6.50").click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=15_000)
        queue_text = diner.locator("strong", has_text=re.compile(r"^Queue number: Q-[0-9a-f]{32}$")).inner_text()
        queue_number = queue_text.split(" ")[2]
        assert QUEUE_RE.fullmatch(queue_number), queue_text
        shot(diner, "demo-06-diner-paid")
        print(f"  paid: {queue_number}")
        diner.get_by_role("link", name="Track your order").click()
        expect(diner.locator("h2").filter(has_text=queue_number)).to_be_visible()
        expect(diner.locator("h2 .badge", has_text="Pending")).to_be_visible()
        shot(diner, "demo-07-diner-tracking-pending")

        ui_login(vendor, VENDOR[0], f"{WEB_BASE}/vendor/menu")
        vendor.goto(f"{WEB_BASE}/vendor/orders")
        row = vendor.locator(".list-group-item").filter(has_text=queue_number)
        expect(row, "the vendor's polling queue surfaces the diner's exact queue number").to_be_visible(timeout=POLL_TIMEOUT)
        expect(row.locator(".badge", has_text="Pending")).to_be_visible()
        shot(vendor, "demo-08-vendor-queue-pending")
        row.get_by_role("link", name="Manage").click()
        expect(vendor.locator("h2").filter(has_text=queue_number)).to_be_visible()
        vendor.get_by_role("button", name="Accept order").click()
        expect(vendor.locator("h2 .badge", has_text="Preparing")).to_be_visible(timeout=15_000)
        shot(vendor, "demo-09-vendor-preparing")
        expect(diner.locator("h2 .badge", has_text="Preparing"),
               "the diner's tracking screen observes Preparing by its own polling").to_be_visible(timeout=POLL_TIMEOUT)
        shot(diner, "demo-10-diner-preparing")
        vendor.get_by_role("button", name="Mark ready").click()
        expect(vendor.locator("h2 .badge", has_text="Ready")).to_be_visible(timeout=15_000)
        shot(vendor, "demo-11-vendor-ready")
        expect(diner.get_by_text("Collect it at the counter."),
               "the diner's Ready-for-collection banner appears by polling").to_be_visible(timeout=POLL_TIMEOUT)
        shot(diner, "demo-12-diner-ready-banner")
        vendor.get_by_role("button", name="Mark collected").click()
        expect(vendor.locator("h2 .badge", has_text="Collected")).to_be_visible(timeout=15_000)
        shot(vendor, "demo-13-vendor-collected")
        expect(diner.locator("h2 .badge", has_text="Collected")).to_be_visible(timeout=POLL_TIMEOUT)
        expect(diner.get_by_text(re.compile(r"thanks for ordering", re.I))).to_be_visible()
        shot(diner, "demo-14-diner-collected")

        diner.goto(f"{WEB_BASE}/diner/orders")
        diner.get_by_role("button", name="Past").click()
        past = diner.locator(".list-group-item").filter(has_text=queue_number)
        expect(past, "US10: the finished order appears in the Past filter").to_be_visible(timeout=POLL_TIMEOUT)
        expect(past.locator(".badge", has_text="Collected")).to_be_visible()
        shot(diner, "demo-15-diner-past-filter")

        # ---------------- Phase B: violation 1 — sold out -----------------
        print("Phase B: sold-out line is refused at checkout, cart retained")
        diner.goto(f"{WEB_BASE}/diner/stalls")
        stall_menu_link(diner)
        m2_row = diner.locator(".list-group-item").filter(has_text=M2)
        m2_row.get_by_role("button", name=re.compile(r"^Add")).click()
        shot(diner, "demo-16-diner-added-mango-sago")
        diner.get_by_role("link", name="Review your cart").click()
        expect(diner.locator(".list-group-item").filter(has_text=M2)).to_be_visible()
        shot(diner, "demo-17-diner-cart-mango-sago")
        # (narration point: the expected refusal is stated on screen before this)
        vendor.goto(f"{WEB_BASE}/vendor/menu")
        m2v = vendor.locator(".list-group-item").filter(has_text=M2)
        m2v.get_by_role("button", name="Mark sold out").click()
        expect(m2v.locator(".badge", has_text="Sold out")).to_be_visible(timeout=15_000)
        shot(vendor, "demo-18-vendor-marked-sold-out")
        diner.goto(f"{WEB_BASE}/diner/checkout")
        expect(diner.get_by_role("heading", name="Checkout")).to_be_visible(timeout=15_000)
        shot(diner, "demo-19-diner-checkout-before-pay")
        diner.get_by_role("button", name="Pay $2.50").click()
        expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible(timeout=15_000)
        expect(diner.locator(".alert-warning")).to_contain_text(M2)
        shot(diner, "demo-20-diner-checkout-refused-sold-out")
        diner.get_by_role("link", name="Review your cart").click()
        expect(diner.locator(".list-group-item").filter(has_text=M2)).to_be_visible()
        shot(diner, "demo-21-diner-cart-retained")

        orders = requests.get(f"{API_BASE}/api/vendor/orders",
                              headers={"Authorization": f"Bearer {token}"}, timeout=10).json()["items"]
        assert sum(1 for o in orders if QUEUE_RE.fullmatch(o["queue_number"])) == 1, \
            "the refused checkout must not have stored a second order"
        print("  refused checkout stored no order (run orders: exactly the phase-A one)")

        # ---------------- Phase C: violation 2 — stall closed -------------
        print("Phase C: closed stall is refused at checkout, cart retained")
        diner.goto(f"{WEB_BASE}/diner/stalls")
        stall_menu_link(diner)
        m1_row = diner.locator(".list-group-item").filter(has_text=M1)
        m1_row.get_by_role("button", name=re.compile(r"^Add")).click()
        shot(diner, "demo-22-diner-added-again")
        diner.get_by_role("link", name="Review your cart").click()
        expect(diner.locator(".list-group-item").filter(has_text=M1)).to_be_visible()
        shot(diner, "demo-23-diner-cart-two-lines")
        # (narration point: the expected refusal is stated on screen before this)
        vendor.goto(f"{WEB_BASE}/vendor/menu")
        vendor.get_by_label(re.compile(r"Trading state")).click()  # the switch has role="switch"
        expect(vendor.locator(".badge", has_text="Closed")).to_be_visible(timeout=15_000)
        expect(vendor.get_by_text("This stall is closed, so new orders are refused at checkout.")).to_be_visible()
        shot(vendor, "demo-24-vendor-stall-closed")
        diner.goto(f"{WEB_BASE}/diner/checkout")
        expect(diner.get_by_role("heading", name="Checkout")).to_be_visible(timeout=15_000)
        shot(diner, "demo-25-diner-checkout-before-pay-closed")
        diner.get_by_role("button", name="Pay $9.00").click()
        expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible(timeout=15_000)
        expect(diner.locator(".alert-warning")).to_contain_text(re.compile(r"closed", re.I))
        shot(diner, "demo-26-diner-checkout-refused-closed")

        diner_ctx.close()
        vendor_ctx.close()
        browser.close()

    # ---------------- cleanup: the run's own order + the two states -------
    print("cleanup")
    import mongoengine
    from app.models.cart import Cart
    from app.models.menu_item import MenuItem
    from app.models.order import Order
    from app.models.user import User
    from app.models.vendor import Vendor

    diner_u = User.objects(email=DINER[0]).first()
    removed = Order.objects(queue_number__regex=r"^Q-[0-9a-f]{32}$").delete()
    assert removed == 1, f"expected exactly one run-owned order, deleted {removed}"
    Cart.objects(diner=diner_u).delete()
    MenuItem.objects(name=M2).update(is_available=True)
    Vendor.objects(name=STALL).update(is_open=True)

    # re-verify the seed invariants while the connection is still open
    assert User.objects(email=DINER[0]).first() is not None
    assert Order.objects(queue_number__regex=r"^Q-seed-").count() == 9, "seed orders damaged"
    assert Order.objects().count() == 9, "run order not cleaned up"
    mongoengine.disconnect(alias="default")
    print("DEMO SCRIPT: ALL STEPS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print("DEMO SCRIPT: FAILED — see traceback; partial state may remain (the run's order, if any)")
        sys.exit(1)
