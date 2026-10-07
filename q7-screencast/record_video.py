"""Record real UI actions continuously; run with backend's Playwright environment.

Uses the guarded, canonical system-test DB only. Voice generation and encoding
are separate (video_tools.py). Frames/timelines stay outside Git. No API mocks,
token injection, altered clocks, or screenshot slides replace application UI.
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import requests
from playwright.async_api import async_playwright, expect
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

WEB = "http://127.0.0.1:5173"
API = "http://127.0.0.1:5001"
WORK = ROOT / ".local/demo-video"
SOURCE = Path(__file__).parent
M1, M2 = "Charcoal Chicken Rice", "Mango Sago"


class Recorder:
    def __init__(self):
        self.page = None
        self.role = "Diner"
        self.start = None
        self.done = False
        self.frames = []
        self.scenes = []
        self.cues = {c["id"]: c for c in json.loads((WORK / "audio.json").read_text())}

    async def capture(self):
        folder = WORK / "frames"
        folder.mkdir(exist_ok=True)
        while not self.done:
            start = time.monotonic()
            if self.page is not None:
                filename = folder / f"{len(self.frames):06d}.jpg"
                # Timestamp the frame actually captured, preserving elapsed waits.
                await self.page.screenshot(path=str(filename), type="jpeg", quality=88,
                                           timeout=15000, animations="allow")
                now = time.monotonic()
                if self.start is None:
                    self.start = now
                self.frames.append({"file": str(filename), "at": now - self.start})
            await asyncio.sleep(max(0, 0.125 - (time.monotonic() - start)))

    async def beat(self, name, page, role, action=None):
        self.page, self.role = page, role
        await page.bring_to_front()
        while self.start is None:
            await asyncio.sleep(0.05)
        cue = dict(self.cues[name])
        cue.update(start=time.monotonic() - self.start, role=role)
        self.scenes.append(cue)
        print(f"{cue['start']:7.2f}s  {role}: {name}", flush=True)
        if action:
            await action()
        remaining = cue["duration"] + 0.75 - (time.monotonic() - self.start - cue["start"])
        if remaining > 0:
            # Narration pacing only. Assertions below wait on real UI conditions.
            await asyncio.sleep(remaining)
        cue["end"] = time.monotonic() - self.start


async def login(page, role):
    await page.goto(WEB + "/login")
    await page.get_by_label("Email").fill(f"{role}.one@skipq.test")
    await page.get_by_label("Password").fill("SkipQDemo2026!")
    await page.get_by_role("button", name="Sign in", exact=True).click()
    await expect(page).to_have_url(re.compile(f"/{role}/"), timeout=15000)


async def menu(diner):
    await diner.goto(WEB + "/diner/stalls")
    await diner.locator(".list-group-item").filter(has_text="Charcoal Grill").get_by_role("link", name="View menu").click()
    await expect(diner.locator(".list-group-item").filter(has_text=M1)).to_be_visible()


async def add(diner, name):
    row = diner.locator(".list-group-item").filter(has_text=name)
    await row.get_by_role("button", name=re.compile("^Add")).click()
    await expect(row.get_by_role("button", name=re.compile("in cart: 1"))).to_be_visible()
    await diner.get_by_role("link", name="Review your cart").click()
    await expect(diner.locator(".list-group-item").filter(has_text=name)).to_be_visible()


async def checkout(diner, price):
    await diner.get_by_role("link", name="Continue to checkout").click()
    await expect(diner.get_by_role("button", name=f"Pay ${price}")).to_be_enabled()


async def status(page, target):
    await expect(page.locator("h2 .badge", has_text=target)).to_be_visible(timeout=15000)


async def main():
    WORK.mkdir(exist_ok=True)
    client = MongoClient("mongodb://127.0.0.1:27017")
    db = client["skipq_system_test"]
    before = {name: list(db[name].find()) for name in ["vendors", "users", "menu_items", "carts", "orders"]}
    assert len(before["orders"]) == 9 and all(o["queue_number"].startswith("Q-seed-") for o in before["orders"])
    stall = next(s for s in before["vendors"] if s["name"] == "Charcoal Grill")
    assert stall["is_open"]
    diner_id = next(u["_id"] for u in before["users"] if u["email"] == "diner.one@skipq.test")
    owned_ids = {
        "vendors": {stall["_id"]},
        "menu_items": {m["_id"] for m in before["menu_items"] if m["name"] == M2},
        "carts": {c["_id"] for c in before["carts"] if c["diner"] == diner_id},
        "orders": {o["_id"] for o in before["orders"] if o["queue_number"] in ["Q-seed-0001", "Q-seed-0004"]},
    }
    response = requests.post(API + "/api/user/gettoken", json={"email":"vendor.one@skipq.test", "password":"SkipQDemo2026!"}, timeout=10)
    response.raise_for_status()
    token = response.json()["token"]
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(API + "/api/vendor/stall", headers=headers, timeout=10)
    response.raise_for_status()
    assert response.json()["stall"]["id"] == str(stall["_id"]), "API must use the guarded test DB"
    print("PREFLIGHT: 9 seed orders; running API matches guarded database", flush=True)
    recorder = Recorder()
    queue = None
    failure = None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            diner_ctx = await browser.new_context(viewport={"width":1280,"height":620})
            vendor_ctx = await browser.new_context(viewport={"width":1280,"height":620})
            diner, vendor = await diner_ctx.new_page(), await vendor_ctx.new_page()
            for page in [diner, vendor]:
                page.set_default_timeout(15000)
                page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            await diner.goto(WEB + "/login")
            recorder.page = diner
            capture = asyncio.create_task(recorder.capture())
            try:
                await recorder.beat("intro", diner, "Diner")
                await recorder.beat("signin", diner, "Diner", lambda: login(diner, "diner"))

                async def empty():
                    await diner.get_by_role("link", name="Cart", exact=True).click()
                    await expect(diner.get_by_text("Loading your cart…")).to_be_hidden()
                    lines = diner.locator(".list-group-item")
                    while await lines.count():
                        count = await lines.count()
                        await lines.first.locator(".btn-outline-danger").click()
                        await expect(lines).to_have_count(count - 1)
                    await expect(diner.get_by_text("Your cart is empty.", exact=True)).to_be_visible()
                await recorder.beat("empty", diner, "Diner", empty)
                await recorder.beat("menu", diner, "Diner", lambda: menu(diner))
                await expect(diner.locator(".list-group-item").filter(has_text="Pineapple Tart").get_by_role("button", name=re.compile("Sold out"))).to_be_disabled()
                await recorder.beat("cart", diner, "Diner", lambda: add(diner, M1))

                async def paymentfail():
                    await checkout(diner, "6.50")
                    await diner.locator("#simulate-failure").check()
                    await diner.get_by_role("button", name="Pay $6.50").click()
                    await expect(diner.locator(".alert-danger")).to_contain_text("retry")
                    assert db.orders.count_documents({}) == 9
                await recorder.beat("paymentfail", diner, "Diner", paymentfail)

                async def paid():
                    nonlocal queue
                    await diner.locator("#simulate-failure").uncheck()
                    await diner.get_by_role("button", name="Pay $6.50").click()
                    await expect(diner.get_by_role("heading", name="Payment successful")).to_be_visible()
                    text = await diner.locator("strong", has_text="Queue number:").inner_text()
                    queue = text.split("Queue number: ")[1]
                    assert re.fullmatch(r"Q-[0-9a-f]{32}", queue)
                    assert db.orders.count_documents({}) == 10
                    print("SAME ORDER:", queue, flush=True)
                await recorder.beat("paid", diner, "Diner", paid)

                async def tracking():
                    await diner.get_by_role("link", name="Track your order").click()
                    await status(diner, "Pending")
                await recorder.beat("pending", diner, "Diner", tracking)

                async def vendorlogin():
                    await login(vendor, "vendor")
                    await vendor.get_by_role("link", name="Orders", exact=True).click()
                    row = vendor.locator(".list-group-item").filter(has_text=queue)
                    await expect(row).to_be_visible()
                    await row.scroll_into_view_if_needed()
                await recorder.beat("vendorlogin", vendor, "Vendor", vendorlogin)

                async def accept():
                    await vendor.locator(".list-group-item").filter(has_text=queue).get_by_role("link", name="Manage").click()
                    await vendor.get_by_role("button", name="Accept order").click()
                    await status(vendor, "Preparing")
                await recorder.beat("accept", vendor, "Vendor", accept)
                await recorder.beat("preparing", diner, "Diner", lambda: status(diner, "Preparing"))

                async def ready():
                    await vendor.get_by_role("button", name="Mark ready").click()
                    await status(vendor, "Ready")
                    await expect(vendor.get_by_role("button", name="Mark no-show")).to_have_count(0)
                await recorder.beat("ready", vendor, "Vendor", ready)
                await recorder.beat("readydiner", diner, "Diner", lambda: expect(diner.get_by_text("Collect it at the counter.")).to_be_visible(timeout=15000))

                async def collect():
                    await vendor.get_by_role("button", name="Mark collected").click()
                    await status(vendor, "Collected")
                await recorder.beat("collect", vendor, "Vendor", collect)
                recorder.page = diner
                await diner.bring_to_front()
                await status(diner, "Collected")
                await asyncio.sleep(2)

                async def history():
                    await diner.get_by_role("link", name="My orders").click()
                    await diner.get_by_role("button", name="Current", exact=True).click()
                    await asyncio.sleep(1)
                    await diner.get_by_role("button", name="Past", exact=True).click()
                    await expect(diner.locator(".list-group-item").filter(has_text=queue)).to_be_visible()
                    await asyncio.sleep(2)
                    await diner.locator(".list-group-item").filter(has_text="Q-seed-0005").get_by_role("link", name="Details").click()
                    await expect(diner.get_by_text("1 × Grilled Chicken Rice")).to_be_visible()
                    await expect(diner.get_by_text("$6.00", exact=True).first).to_be_visible()
                await recorder.beat("history", diner, "Diner", history)

                async def soldsetup():
                    await menu(diner)
                    await add(diner, M2)
                    await checkout(diner, "2.50")
                await recorder.beat("soldsetup", diner, "Diner", soldsetup)
                await recorder.beat("soldexpect", diner, "Diner")

                async def soldtoggle():
                    await vendor.get_by_role("link", name="Menu", exact=True).click()
                    row = vendor.locator(".list-group-item").filter(has_text=M2)
                    await row.get_by_role("button", name="Mark sold out").click()
                    await expect(row.locator(".badge", has_text="Sold out")).to_be_visible()
                await recorder.beat("soldtoggle", vendor, "Vendor", soldtoggle)

                async def soldrefuse():
                    await diner.get_by_role("button", name="Pay $2.50").click()
                    await expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible()
                    await expect(diner.locator(".alert-warning")).to_contain_text(M2)
                    assert db.orders.count_documents({}) == 10
                    print("SOLD-OUT REFUSAL: cart retained, 10 total orders (9 seeds + 1 demo)", flush=True)
                await recorder.beat("soldrefuse", diner, "Diner", soldrefuse)
                await recorder.beat("retained", diner, "Diner", lambda: diner.get_by_role("link", name="Review your cart").click())
                await expect(diner.locator(".list-group-item").filter(has_text=M2)).to_contain_text("Sold out")

                async def closedsetup():
                    await diner.get_by_role("button", name=f"Remove {M2} from the cart").click()
                    await expect(diner.get_by_text("Your cart is empty.", exact=True)).to_be_visible()
                    await menu(diner)
                    await add(diner, M1)
                    await checkout(diner, "6.50")
                await recorder.beat("closedsetup", diner, "Diner", closedsetup)
                await recorder.beat("closedexpect", diner, "Diner")

                async def closedtoggle():
                    await vendor.get_by_label(re.compile("Trading state")).click()
                    await expect(vendor.locator(".badge", has_text="Closed")).to_be_visible()
                await recorder.beat("closedtoggle", vendor, "Vendor", closedtoggle)

                async def closedrefuse():
                    await diner.get_by_role("button", name="Pay $6.50").click()
                    await expect(diner.get_by_role("heading", name="Checkout refused")).to_be_visible()
                    await expect(diner.locator(".alert-warning")).to_contain_text("closed")
                    assert db.orders.count_documents({}) == 10
                    print("CLOSED-STALL REFUSAL: cart retained, no additional order", flush=True)
                    await asyncio.sleep(2)
                    await diner.get_by_role("link", name="Review your cart").click()
                    await expect(diner.locator(".list-group-item").filter(has_text=M1)).to_be_visible()
                await recorder.beat("closedrefuse", diner, "Diner", closedrefuse)

                async def crud():
                    await vendor.get_by_label(re.compile("Trading state")).click()
                    await vendor.locator(".list-group-item").filter(has_text=M2).get_by_role("button", name="Restock").click()
                    await vendor.get_by_role("link", name="Add menu item").click()
                    await vendor.get_by_label("Name", exact=True).fill("Video Demo Toast")
                    await vendor.get_by_label("Price", exact=True).fill("3.50")
                    await vendor.get_by_label("Description", exact=True).fill("Temporary item created through the live vendor form.")
                    await vendor.get_by_label("Image URL", exact=True).fill(API + "/static/images/skipq-m1.png")
                    await vendor.get_by_role("button", name="Add item", exact=True).scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await vendor.get_by_role("button", name="Add item", exact=True).click()
                    row = vendor.locator(".list-group-item").filter(has_text="Video Demo Toast")
                    await expect(row).to_be_visible()
                    await asyncio.sleep(1)
                    await row.get_by_role("link", name="Edit", exact=True).click()
                    await expect(vendor.get_by_label("Price", exact=True)).to_have_value("3.50")
                    await vendor.get_by_label("Price", exact=True).fill("3.75")
                    await vendor.get_by_role("button", name="Save item").click()
                    await expect(row).to_contain_text("$3.75")
                    await asyncio.sleep(1)
                    await row.get_by_role("button", name="Remove", exact=True).click()
                    await expect(row).to_have_count(0)
                await recorder.beat("crud", vendor, "Vendor", crud)

                async def refund():
                    order = db.orders.find_one({"queue_number":"Q-seed-0001"})
                    await vendor.goto(WEB + "/vendor/orders/" + str(order["_id"]))
                    await status(vendor, "Pending")
                    await vendor.get_by_role("button", name="Reject order").click()
                    await status(vendor, "Cancelled")
                    await expect(vendor.get_by_text(re.compile("Payment:.*Refunded"))).to_be_visible()
                await recorder.beat("refund", vendor, "Vendor", refund)

                async def noshow():
                    order = db.orders.find_one({"queue_number":"Q-seed-0004"})
                    await vendor.goto(WEB + "/vendor/orders/" + str(order["_id"]))
                    await status(vendor, "Ready")
                    await vendor.get_by_role("button", name="Mark no-show").click()
                    await status(vendor, "NoShow")
                    await expect(vendor.get_by_text(re.compile("Payment:.*Paid"))).to_be_visible()
                await recorder.beat("noshow", vendor, "Vendor", noshow)

                evidence = await diner_ctx.new_page()
                unit = (ROOT / "backend/docs/evidence/frontend-quality/unit.log").read_text()
                assert "313 passed" in unit
                analysis = json.loads((ROOT / "backend/q6-performance/reconciled-analysis.json").read_text())
                assert analysis["menu_requests"] == 395 and analysis["failures"] == 0
                await evidence.set_content("""<html><body style='font-family:Arial;margin:60px;background:#f6f8fb;color:#172033'>
                <h1>SkipQ — retained project evidence</h1><p>Summary slide · existing 7 October 2026 records · not a live test run</p>
                <h2>React frontend → Flask API → MongoDB</h2>
                <ul style='font-size:24px;line-height:1.8'><li>313 unit tests passed</li><li>10 real-DB functional tests passed, twice</li><li>Assessed browser lifecycle passed, twice</li><li>Production build compiled successfully</li><li>30 layout captures: no overflow or uncaught page errors</li></ul>
                <p>Sources: docs/evidence/frontend-quality/ · docs/assessment/frontend-quality-review.md</p></body></html>""")
                await recorder.beat("evidence", evidence, "Evidence")
                await evidence.set_content("""<html><body style='font-family:Arial;margin:60px;background:#f6f8fb;color:#172033'>
                <h1>Measured local performance</h1><p>Summary slide · retained Locust CSV and query-timing records</p>
                <h2>10 users · 2 users/second ramp · 120 seconds</h2>
                <ul style='font-size:25px;line-height:1.8'><li>395 menu requests · 0 failures</li><li>Menu client response p95: 20 ms</li><li>Sum of three driver command durations p95: 3.163 ms</li></ul>
                <p style='font-size:22px'>Small seeded dataset · local Flask development server.<br>No production capacity or isolated DB execution claim.</p>
                <p>Sources: q6-performance/menu_stats.csv · reconciled-analysis.json · run-metadata.md</p></body></html>""")
                await recorder.beat("performance", evidence, "Evidence")
                await recorder.beat("close", diner, "Diner")
                print("RECORDING: ALL LIVE UI CHECKS PASSED", flush=True)
            except BaseException as exc:
                failure = repr(exc)
                print("RECORDING FAILURE (retained):", failure, flush=True)
                await asyncio.sleep(3)
                raise
            finally:
                recorder.done = True
                await capture
                (WORK / "timeline.json").write_text(json.dumps({"scenes":recorder.scenes,"frames":recorder.frames,"duration":time.monotonic()-recorder.start,"queue":queue,"failure":failure}, indent=2))
                await browser.close()
    finally:
        # Restore only this take's guarded fixtures and new documents; never drop
        # a database. Detect unrelated newly created documents before cleanup.
        for collection in ["vendors", "menu_items", "carts", "orders"]:
            originals = {d["_id"]: d for d in before[collection]}
            for doc in db[collection].find():
                if doc["_id"] in originals:
                    if doc["_id"] in owned_ids[collection]:
                        db[collection].replace_one({"_id":doc["_id"]}, originals[doc["_id"]])
                else:
                    owned = (collection == "orders" and doc.get("queue_number") == queue) or (collection == "menu_items" and doc.get("name") == "Video Demo Toast")
                    assert owned, f"Unrelated new {collection} document detected; not deleting"
                    db[collection].delete_one({"_id":doc["_id"]})
            for oid, doc in originals.items():
                if oid in owned_ids[collection]:
                    db[collection].replace_one({"_id":oid}, doc, upsert=True)
            assert list(db[collection].find().sort("_id", 1)) == sorted(before[collection], key=lambda d:d["_id"])
        client.close()
        print("CLEANUP: original guarded fixtures restored exactly; development DB untouched", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
