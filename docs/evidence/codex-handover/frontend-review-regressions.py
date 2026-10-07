"""Diagnostic browser regressions for the final frontend review.

These are supplementary transport/UI checks, not the assessed Q6 lifecycle
suite. Login and cart requests use the real API. Checkout POSTs are faulted
deliberately, and cart mutations are held to observe the actual controls.
No orders are created. The guarded seed diner's original cart is restored.
"""

import argparse
import json
import os
import re
import sys

import requests
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient

API = "http://127.0.0.1:5001"
WEB = "http://127.0.0.1:5173"
EMAIL = "diner.one@skipq.test"
PASSWORD = "SkipQDemo2026!"
ITEM = "Charcoal Chicken Rice"


def login(page):
    page.goto(f"{WEB}/login")
    page.get_by_label("Email").fill(EMAIL)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page).to_have_url(f"{WEB}/diner/stalls", timeout=15000)


def checkout_failure(page, fault):
    """An unavailable API or server500 must give visible retry feedback."""
    page.goto(f"{WEB}/diner/checkout")
    pay = page.get_by_role("button", name="Pay $6.50", exact=True)
    expect(pay).to_be_visible()

    def fault_route(route):
        if route.request.method != "POST":
            return route.continue_()
        if fault == "network":
            return route.abort("connectionfailed")
        return route.fulfill(status=500, content_type="application/json",
                             headers={"Access-Control-Allow-Origin": WEB}, body=json.dumps({
            "error": {"code": "internal_error", "message": "The request could not be completed. Please try again."}
        }))

    page.route("**/api/diner/orders", fault_route)
    pay.click()
    alert = page.locator('[role="alert"]')
    expect(alert).to_be_visible(timeout=3000)
    expected_message = "could not be reached" if fault == "network" else "could not be completed"
    expect(alert).to_contain_text(expected_message)
    expect(pay).to_be_enabled()
    assert page.get_by_role("heading", name="Payment successful").count() == 0


def pending_cart_mutation(page, view, stall_id):
    """Pending mutations disable controls and refuse a synchronous second click."""
    held = []

    def hold(route):
        if route.request.method in ("POST", "PATCH", "DELETE"):
            held.append(route)
        else:
            route.continue_()

    if view == "menu":
        page.goto(f"{WEB}/diner/stalls/{stall_id}")
        row = page.locator(".list-group-item").filter(has_text=ITEM)
        button = row.get_by_role("button")
        expect(button).to_be_visible()
        expect(button).to_have_text("Add another (in cart: 1)")
    else:
        page.goto(f"{WEB}/diner/cart")
        button = page.get_by_role("button", name=f"Increase quantity of {ITEM}", exact=True)
        expect(button).to_be_visible()

    page.route("**/api/diner/cart/items**", hold)
    # Two native DOM clicks in one task exercise the synchronous re-entry
    # guard rather than relying only on React's later disabled rerender.
    button.evaluate("button => { button.click(); button.click(); }")
    expect(button).to_be_disabled(timeout=3000)
    if view == "cart":
        expect(page.get_by_role("button", name=f"Decrease quantity of {ITEM}", exact=True)).to_be_disabled()
        expect(page.get_by_role("button", name=f"Remove {ITEM} from the cart", exact=True)).to_be_disabled()
    # This short diagnostic wait lets intercepted requests reach Python;
    # it is not an application-polling or assessed lifecycle assertion.
    page.wait_for_timeout(100)
    assert len(held) == 1, f"{view}: expected one mutation while busy, received {len(held)}"
    held.pop().continue_()
    expect(button).to_be_enabled(timeout=10000)
    if view == "menu":
        expect(row.get_by_role("button", name="Add another (in cart: 2)", exact=True)).to_be_visible()
    else:
        expect(page.locator('.btn-group .disabled')).to_have_text("2")
        expect(page.get_by_text("$13.00", exact=True).first).to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=("network", "server500", "menu", "cart"))
    args = parser.parse_args()
    database = os.environ.get("SKIPQ_SYSTEM_DB", "skipq_system_test")
    assert re.fullmatch(r"skipq_system_test(?:_[a-z0-9]+)?", database), "Guarded system-test DB required"
    db_client = MongoClient(os.environ.get("MONGODB_HOST", "mongodb://127.0.0.1:27017"))
    db = db_client[database]
    user = db.users.find_one({"email": EMAIL})
    assert user is not None, "Seed diner is missing"
    stall = db.vendors.find_one({"name": "Charcoal Grill"})
    assert stall is not None and stall["is_open"], "Seed stall must be open"
    item = db.menu_items.find_one({"name": ITEM, "vendor": stall["_id"]})
    assert item is not None and item["is_available"] and item["is_active"], "Seed item must be available"
    before_cart = db.carts.find_one({"diner": user["_id"]})
    before_orders = db.orders.count_documents({})
    login_response = requests.post(f"{API}/api/user/gettoken", json={"email": EMAIL, "password": PASSWORD}, timeout=10)
    login_response.raise_for_status()
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                for name in ("network", "server500", "menu", "cart"):
                    if args.only and name != args.only:
                        continue
                    # Reset only this actor's cart so each check begins with
                    # one known line. Original BSON document is restored below.
                    db.carts.delete_many({"diner": user["_id"]})
                    response = requests.post(f"{API}/api/diner/cart/items", headers=headers,
                                             json={"item_id": str(item["_id"]), "quantity": 1}, timeout=10)
                    assert response.status_code == 201, response.text
                    assert db.carts.find_one({"diner": user["_id"]})["items"][0]["quantity"] == 1, "API must use the guarded database"
                    context = browser.new_context(viewport={"width": 1280, "height": 720})
                    page = context.new_page()
                    page.set_default_timeout(10000)
                    try:
                        login(page)
                        if name in ("network", "server500"):
                            checkout_failure(page, name)
                        else:
                            pending_cart_mutation(page, name, str(stall["_id"]))
                        results.append({"check": name, "result": "PASS"})
                        print(f"PASS {name}", flush=True)
                    except Exception as error:
                        results.append({"check": name, "result": "FAIL", "detail": str(error)})
                        print(f"FAIL {name}: {error}", flush=True)
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        db.carts.delete_many({"diner": user["_id"]})
        if before_cart is not None:
            db.carts.insert_one(before_cart)
        after_cart = db.carts.find_one({"diner": user["_id"]})
        assert after_cart == before_cart, "Original diner cart was not restored"
        assert db.orders.count_documents({}) == before_orders, "Diagnostic regressions changed orders"
        db_client.close()
        print("CLEANUP PASS: original diner cart restored; order count unchanged", flush=True)
    print(json.dumps(results, indent=2))
    return int(any(result["result"] != "PASS" for result in results))


if __name__ == "__main__":
    sys.exit(main())
