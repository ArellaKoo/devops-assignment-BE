"""Real-database order lifecycle through the API (Task 6, Q4(b) evidence).

The whole diner-to-vendor flow runs against the guarded ``skipq_test``
database with real MongoEngine queries, real token verification, and real
unique-index behaviour — nothing about the persistence boundary is
mocked. Every document the tests create is registered in
``fixture_records`` and removed on teardown, so the suite can run twice
against the same database with no manual reset.
"""

from app.models.order import Order

PASSWORD = "FunTest2026!"
DINER_EMAIL = "diner.lifecycle@skipq.test"
VENDOR_EMAIL = "vendor.lifecycle@skipq.test"


def login(client, email):
    response = client.post("/api/user/gettoken", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.get_json()
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def code(response):
    return response.get_json()["error"]["code"]


def _build_cast(fixture_records, item_name="Lifecycle Rice", price_cents=650):
    from app.models.menu_item import MenuItem
    from app.models.user import User
    from app.models.vendor import Vendor

    stall = Vendor(name="Functional Grill", is_open=True)
    stall.save()
    fixture_records["vendors"].append(stall)
    vendor_user = User.create(VENDOR_EMAIL, PASSWORD, "vendor", vendor=stall)
    diner = User.create(DINER_EMAIL, PASSWORD, "diner")
    fixture_records["users"].extend([vendor_user, diner])
    item = MenuItem(
        vendor=stall,
        name=item_name,
        description="Created by the functional suite.",
        image_url="http://127.0.0.1:5001/static/images/skipq-m1.png",
        price_cents=price_cents,
    )
    item.save()
    fixture_records["items"].append(item)
    return {"stall": stall, "vendor": vendor_user, "diner": diner, "item": item}


def _add_line(client, diner_headers, item_id, quantity=2):
    response = client.post(
        "/api/diner/cart/items", json={"item_id": item_id, "quantity": quantity}, headers=diner_headers
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["cart"]


def _checkout(client, diner_headers, key, fingerprint, method="PayNow", simulate=True):
    return client.post(
        "/api/diner/orders",
        json={
            "payment_method": method,
            "simulate_success": simulate,
            "checkout_key": key,
            "expected_fingerprint": fingerprint,
        },
        headers=diner_headers,
    )


def test_diner_and_vendor_complete_order(functional_app, fixture_records):
    """GIVEN a diner and the vendor of an open stall stored in the real test database WHEN the diner checks out a two-line-for-one-item cart and the vendor walks the order to collection THEN each HTTP step returns the expected code and state, the diner sees every status change, and the terminal order refuses further moves."""
    cast = _build_cast(fixture_records)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)
    vendor_headers = login(client, VENDOR_EMAIL)

    cart = _add_line(client, diner_headers, str(cast["item"].id), quantity=2)
    assert cart["total_cents"] == 1300

    created = _checkout(client, diner_headers, "fn-lifecycle-1", cart["fingerprint"])
    assert created.status_code == 201, created.get_json()
    order = created.get_json()["order"]
    fixture_records["orders"].append(Order.get(order["id"]))
    assert order["status"] == "Pending"
    assert order["payment"]["status"] == "Paid"
    assert order["payment"]["method"] == "PayNow"
    assert order["total_cents"] == 1300
    assert order["queue_number"].startswith("Q-")
    assert [i["name"] for i in order["items"]] == ["Lifecycle Rice"]
    assert order["items"][0]["price_cents"] == 650 and order["items"][0]["quantity"] == 2

    queue = client.get("/api/vendor/orders", headers=vendor_headers)
    assert queue.status_code == 200
    queue_items = queue.get_json()["items"]
    assert [o["id"] for o in queue_items] == [order["id"]]
    assert queue_items[0]["allowed_actions"] == ["Preparing", "Cancelled"]

    preparing = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=vendor_headers
    )
    assert preparing.status_code == 200
    assert preparing.get_json()["order"]["status"] == "Preparing"
    assert preparing.get_json()["order"]["allowed_actions"] == ["Ready"]
    seen = client.get(f"/api/diner/orders/{order['id']}", headers=diner_headers)
    assert seen.status_code == 200 and seen.get_json()["order"]["status"] == "Preparing"

    ready = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Ready"}, headers=vendor_headers
    )
    assert ready.status_code == 200
    assert ready.get_json()["order"]["status"] == "Ready"
    assert ready.get_json()["order"]["ready_at"] is not None
    seen = client.get(f"/api/diner/orders/{order['id']}", headers=diner_headers)
    assert seen.get_json()["order"]["status"] == "Ready"

    collected = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Collected"}, headers=vendor_headers
    )
    assert collected.status_code == 200
    assert collected.get_json()["order"]["status"] == "Collected"
    assert collected.get_json()["order"]["allowed_actions"] == []

    current = client.get("/api/diner/orders?view=current", headers=diner_headers)
    assert [o["id"] for o in current.get_json()["items"]] == []
    history = client.get("/api/diner/orders?view=history", headers=diner_headers)
    history_orders = history.get_json()["items"]
    assert [o["id"] for o in history_orders] == [order["id"]]
    assert history_orders[0]["status"] == "Collected"

    again = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=vendor_headers
    )
    assert again.status_code == 409
    assert code(again) == "invalid_transition"

    stored = Order.get(order["id"])
    assert stored.status == "Collected" and stored.payment.status == "Paid"


def test_cancellation_refunds_the_simulated_payment(functional_app, fixture_records):
    """GIVEN a freshly paid Pending order WHEN its stall vendor cancels it THEN 200 marks the order Cancelled and the embedded payment Refunded with a refund timestamp, which the diner's detail screen shows."""
    cast = _build_cast(fixture_records, item_name="Lifecycle Noodles", price_cents=300)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)
    vendor_headers = login(client, VENDOR_EMAIL)

    cart = _add_line(client, diner_headers, str(cast["item"].id), quantity=1)
    created = _checkout(client, diner_headers, "fn-cancel-1", cart["fingerprint"])
    assert created.status_code == 201
    order = created.get_json()["order"]
    fixture_records["orders"].append(Order.get(order["id"]))

    cancelled = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Cancelled"}, headers=vendor_headers
    )
    assert cancelled.status_code == 200
    body = cancelled.get_json()["order"]
    assert body["status"] == "Cancelled"
    assert body["payment"]["status"] == "Refunded"
    assert body["payment"]["refunded_at"] is not None

    stored = Order.get(order["id"])
    assert stored.status == "Cancelled"
    assert stored.payment.status == "Refunded"
    assert stored.payment.refunded_at is not None


def test_noshow_only_at_the_inclusive_boundary(functional_app, fixture_records):
    """GIVEN a Ready order in the real database WHEN the vendor marks NoShow before and after the 30-minute boundary (the clock moved by rewriting ``ready_at`` between attempts) THEN the early attempt is 409 no_show_too_early and the boundary-reaching attempt is 200 with the terminal state persisted."""
    from datetime import timedelta

    from app.models.common import utcnow

    cast = _build_cast(fixture_records, item_name="Boundary Rice", price_cents=400)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)
    vendor_headers = login(client, VENDOR_EMAIL)

    cart = _add_line(client, diner_headers, str(cast["item"].id), quantity=1)
    created = _checkout(client, diner_headers, "fn-noshow-1", cart["fingerprint"])
    assert created.status_code == 201
    order = created.get_json()["order"]
    fixture_records["orders"].append(Order.get(order["id"]))
    client.patch(f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=vendor_headers)
    client.patch(f"/api/vendor/orders/{order['id']}/status", json={"status": "Ready"}, headers=vendor_headers)

    early = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "NoShow"}, headers=vendor_headers
    )
    assert early.status_code == 409
    assert code(early) == "no_show_too_early"

    stored = Order.get(order["id"])
    stored.ready_at = utcnow() - timedelta(minutes=30, seconds=1)
    stored.save()
    on_time = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "NoShow"}, headers=vendor_headers
    )
    assert on_time.status_code == 200
    assert on_time.get_json()["order"]["status"] == "NoShow"
    assert on_time.get_json()["order"]["payment"]["status"] == "Paid", "a no-show stays paid"
    assert Order.get(order["id"]).status == "NoShow"
