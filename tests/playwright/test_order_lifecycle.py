"""Q6(a): the full order lifecycle driven through two browser personas.

The diner signs in through the UI in one isolated context, clears any
leftover cart lines through the cart screen, adds one item, and checks out
with the checkout key the checkout screen mints itself. The vendor signs in
through the UI in a second isolated context and finds **that** queue number
in the paid queue (the queue is not assumed to be "first order"). Every
vendor move — Accept, Mark ready, Mark collected — is asserted on the
vendor's screen and re-observed on the diner's tracking screen, which polls
the API on its own timer. All waiting is done through Playwright ``expect``
condition waits on accessible role/label locators: no ``sleep``, no fixed
timeouts standing in for conditions, no token injection, no mocked API.

Fixture/model infrastructure (outside the persona steps) seeds and verifies
the ``skipq_system_test`` database, proves the run left exactly one new
order among the untouched seed records, and deletes the run's order and the
test diner's cart lines on teardown — so the suite runs twice against the
same seeded database with no manual reset between runs. Per-state
screenshots land in ``docs/evidence/screenshots/`` as ``task11-*``.
"""

import re
from pathlib import Path

from playwright.sync_api import expect

from app.models.order import Order

BASE = "http://127.0.0.1:5173"
PASSWORD = "SkipQDemo2026!"
SHOTS = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "screenshots"
POLLING_TIMEOUT = 15000  # both screens poll every 3 s; leave headroom


def ui_login(page, email, home):
    """Sign in through the login screen; the session lives in that context's sessionStorage."""
    page.goto(f"{BASE}/login")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    expect(page).to_have_url(f"{BASE}{home}", timeout=10000)


def shot(page, name):
    page.screenshot(path=str(SHOTS / name))


def test_order_lifecycle_through_both_browser_personas(playwright, system_database):
    browser = playwright.chromium.launch(headless=True)
    diner_ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    vendor_ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    diner = diner_ctx.new_page()
    vendor = vendor_ctx.new_page()

    try:
        # --- diner signs in through the UI -------------------------------------
        ui_login(diner, "diner.one@skipq.test", "/diner/stalls")
        stalls = diner.locator(".list-group-item")
        expect(stalls).to_have_count(1, timeout=10000)  # only the open stall
        charcoal = stalls.first
        expect(charcoal.locator(".badge", has_text="Open")).to_be_visible()

        # --- clear any leftover cart lines through the UI ----------------------
        diner.goto(f"{BASE}/diner/cart")
        expect(diner.get_by_text("Loading your cart…")).to_be_hidden(timeout=10000)
        lines = diner.locator(".list-group-item")
        remaining = lines.count()
        while remaining:
            lines.first.locator(".btn-outline-danger").click()
            expect(lines).to_have_count(remaining - 1, timeout=10000)
            remaining -= 1
        expect(diner.get_by_text("Your cart is empty.")).to_be_visible()

        # --- add one item from the open stall's menu ---------------------------
        diner.get_by_role("link", name="Browse open stalls").click()
        expect(diner).to_have_url(f"{BASE}/diner/stalls", timeout=10000)
        charcoal = diner.locator(".list-group-item", has_text="Charcoal Grill")
        charcoal.get_by_role("link", name="View menu").click()
        expect(diner.get_by_role("heading", name="Charcoal Grill")).to_be_visible(timeout=10000)
        m1 = diner.locator(".list-group-item", has_text="Charcoal Chicken Rice")
        add = m1.get_by_role("button", name="Add")
        expect(add).to_be_enabled()
        add.click()
        expect(diner.get_by_text("Charcoal Chicken Rice added").first).to_be_visible(timeout=10000)
        expect(diner.get_by_role("link", name="Review your cart")).to_be_visible()

        # --- review the single line and go to checkout -------------------------
        diner.get_by_role("link", name="Review your cart").click()
        expect(diner).to_have_url(f"{BASE}/diner/cart", timeout=10000)
        expect(lines).to_have_count(1, timeout=10000)
        expect(lines.first.get_by_text("$6.50 each")).to_be_visible()
        expect(lines.first.get_by_role("button", name=re.compile(r"^Remove .* from the cart$"))).to_be_visible()
        diner.get_by_role("link", name="Continue to checkout").click()
        expect(diner.get_by_role("heading", name="Checkout")).to_be_visible(timeout=10000)
        expect(diner.get_by_text("1 × Charcoal Chicken Rice", exact=True)).to_be_visible()
        expect(diner.get_by_role("button", name="Pay $6.50", exact=True)).to_be_enabled()
        expect(diner.get_by_label("PayNow")).to_be_checked()
        expect(diner.locator("#simulate-failure")).not_to_be_checked()

        # --- pay; the screen mints its own checkout key ------------------------
        diner.get_by_role("button", name="Pay $6.50").click()
        expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible(timeout=10000)
        queue = re.fullmatch(r"Queue number: (Q-[0-9a-f]{32})",
                             diner.locator("p strong", has_text="Queue number:").inner_text()).group(1)
        expect(diner.get_by_text(re.compile(r"Paid with PayNow \(Paid\), \$6\.50")).first).to_be_visible()
        shot(diner, "task11-01-diner-payment-success-pending.png")

        # --- diner's tracking screen shows Pending/Paid ------------------------
        diner.get_by_role("link", name="Track your order").click()
        expect(diner).to_have_url(re.compile(r"/diner/orders/"), timeout=10000)
        expect(diner.get_by_role("heading", level=2)).to_have_text(re.compile(queue), timeout=10000)
        expect(diner.locator("h2 .badge", has_text="Pending")).to_be_visible()
        expect(diner.get_by_text("1 × Charcoal Chicken Rice").first).to_be_visible()
        expect(diner.get_by_text("Payment: PayNow · Paid").first).to_be_visible()
        expect(diner.locator("p", has_text="updates automatically every few seconds")).to_have_count(1)
        shot(diner, "task11-02-diner-pending.png")

        # --- vendor signs in and finds THIS queue number in the paid queue -----
        ui_login(vendor, "vendor.one@skipq.test", "/vendor/menu")
        vendor.goto(f"{BASE}/vendor/orders")
        expect(vendor.get_by_role("heading", name="Orders")).to_be_visible(timeout=10000)
        expect(vendor.locator(".list-group-item")).to_have_count(9, timeout=POLLING_TIMEOUT)  # 8 seed + new
        row = vendor.locator(".list-group-item", has_text=queue)
        expect(row).to_be_visible(timeout=POLLING_TIMEOUT)  # surfaced by the queue's 3 s polling
        expect(row.locator(".badge", has_text="Pending")).to_be_visible()
        shot(vendor, "task11-03-vendor-queue-with-new-pending-order.png")
        row.get_by_role("link", name="Manage").click()
        expect(vendor).to_have_url(re.compile(r"/vendor/orders/"), timeout=10000)
        expect(vendor.get_by_role("heading", level=2)).to_have_text(re.compile(queue), timeout=10000)
        expect(vendor.locator("h2 .badge", has_text="Pending")).to_be_visible()
        expect(vendor.get_by_text("1 × Charcoal Chicken Rice").first).to_be_visible()
        expect(vendor.get_by_text("Payment: PayNow · Paid").first).to_be_visible()
        expect(vendor.get_by_role("button", name="Accept order")).to_be_visible()
        expect(vendor.get_by_role("button", name="Reject order")).to_be_visible()
        for label in ("Mark ready", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_role("button", name=label)).to_have_count(0)
        shot(vendor, "task11-04-vendor-pending.png")

        # --- Accept order: Preparing on both screens ---------------------------
        vendor.get_by_role("button", name="Accept order").click()
        expect(vendor.locator("h2 .badge", has_text="Preparing")).to_be_visible(timeout=10000)
        expect(vendor.get_by_role("button", name="Mark ready")).to_be_visible()
        for label in ("Accept order", "Reject order", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_role("button", name=label)).to_have_count(0)
        shot(vendor, "task11-05-vendor-preparing.png")
        expect(diner.locator("h2 .badge", has_text="Preparing")).to_be_visible(timeout=POLLING_TIMEOUT)
        shot(diner, "task11-06-diner-preparing.png")

        # --- Mark ready: Ready on both screens, Ready banner for the diner -----
        vendor.get_by_role("button", name="Mark ready").click()
        expect(vendor.locator("h2 .badge", has_text="Ready")).to_be_visible(timeout=10000)
        expect(vendor.get_by_role("button", name="Mark collected")).to_be_visible()
        for label in ("Accept order", "Reject order", "Mark ready", "Mark no-show"):
            expect(vendor.get_by_role("button", name=label)).to_have_count(0)
        shot(vendor, "task11-07-vendor-ready.png")
        expect(diner.locator("h2 .badge", has_text="Ready")).to_be_visible(timeout=POLLING_TIMEOUT)
        expect(diner.get_by_text("Your order is ready. Collect it at the counter.").first).to_be_visible()
        shot(diner, "task11-08-diner-ready.png")

        # --- Mark collected: terminal on both screens --------------------------
        vendor.get_by_role("button", name="Mark collected").click()
        expect(vendor.locator("h2 .badge", has_text="Collected")).to_be_visible(timeout=10000)
        expect(vendor.get_by_text("This order is final").first).to_be_visible()
        for label in ("Accept order", "Reject order", "Mark ready", "Mark collected", "Mark no-show"):
            expect(vendor.get_by_role("button", name=label)).to_have_count(0)
        shot(vendor, "task11-09-vendor-collected.png")
        expect(diner.locator("h2 .badge", has_text="Collected")).to_be_visible(timeout=POLLING_TIMEOUT)
        expect(diner.get_by_text("thanks for ordering from Charcoal Grill").first).to_be_visible()
        expect(diner.locator("p", has_text="updates automatically every few seconds")).to_have_count(0)
        shot(diner, "task11-10-diner-collected.png")

        # --- US10: the finished order moves from Current to Past ---------------
        diner.goto(f"{BASE}/diner/orders")
        expect(diner.get_by_role("heading", name="My orders")).to_be_visible(timeout=10000)
        expect(lines).to_have_count(9, timeout=10000)  # 8 seed orders + this run's order
        diner.get_by_role("button", name="Past", exact=True).click()
        expect(lines).to_have_count(4, timeout=POLLING_TIMEOUT)  # 3 seed terminal + this order
        expect(lines.first.get_by_text(queue)).to_be_visible()
        expect(lines.first.locator(".badge", has_text="Collected")).to_be_visible()
        shot(diner, "task11-11-diner-past-list.png")
        diner.get_by_role("button", name="Current").click()
        expect(lines).to_have_count(5, timeout=POLLING_TIMEOUT)
        expect(diner.locator(".list-group-item", has_text=queue)).to_have_count(0)

        # --- model-level proof (infrastructure, outside the persona steps) ------
        order = Order.objects(queue_number=queue).first()
        assert order is not None
        assert order.status == "Collected"
        assert order.payment.status == "Paid"
        assert order.payment.method == "PayNow"
        assert order.payment.amount_cents == 650
        assert order.total_cents == 650
        assert order.ready_at is not None
        assert [(i.name_snapshot, i.price_cents_snapshot, i.quantity) for i in order.items] == [
            ("Charcoal Chicken Rice", 650, 1)
        ]
        # The UI minted a UUID checkout key; the run stored exactly one order,
        # the nine seed orders are untouched — run after run on one database.
        assert re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", order.checkout_key)
        assert Order.objects().count() == 10
        assert Order.objects(queue_number__regex=r"^Q-[0-9a-f]{32}$").count() == 1
        assert Order.objects(queue_number__regex=r"^Q-seed-").count() == 9
    finally:
        diner_ctx.close()
        vendor_ctx.close()
        browser.close()
