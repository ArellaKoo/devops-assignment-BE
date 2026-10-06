"""Real-database access, stale-checkout, duplicate-checkout and snapshot tests (Task 6).

Every case runs the real application against the guarded ``skipq_test``
database: 401/403 scope boundaries, the stale-cart refusals that must
persist no order, the sequential replay/conflict pair, the
thread-concurrent same-key checkout that must persist exactly one order
through the real unique index, and the purchased name/price snapshots
read back from the database after the menu moved on.
"""

import threading

from app.models.order import Order

PASSWORD = "FunTest2026!"
DINER_EMAIL = "diner.access@skipq.test"
VENDOR_EMAIL = "vendor.access@skipq.test"
FOREIGN_DINER_EMAIL = "diner.foreign@skipq.test"
FOREIGN_VENDOR_EMAIL = "vendor.foreign@skipq.test"


def login(client, email):
    response = client.post("/api/user/gettoken", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.get_json()
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


def code(response):
    return response.get_json()["error"]["code"]


def _diner_and_vendor(fixture_records, stall_name="Access Grill"):
    from app.models.menu_item import MenuItem
    from app.models.user import User
    from app.models.vendor import Vendor

    stall = Vendor(name=stall_name, is_open=True)
    stall.save()
    fixture_records["vendors"].append(stall)
    vendor_user = User.create(VENDOR_EMAIL, PASSWORD, "vendor", vendor=stall)
    diner = User.create(DINER_EMAIL, PASSWORD, "diner")
    fixture_records["users"].extend([vendor_user, diner])
    item = MenuItem(
        vendor=stall,
        name="Access Curry",
        description="Created by the functional suite.",
        image_url="http://127.0.0.1:5001/static/images/skipq-m1.png",
        price_cents=550,
    )
    item.save()
    fixture_records["items"].append(item)
    return {"stall": stall, "vendor": vendor_user, "diner": diner, "item": item}


def _checkout(client, headers, key, fingerprint, simulate=True):
    return client.post(
        "/api/diner/orders",
        json={
            "payment_method": "PayNow",
            "simulate_success": simulate,
            "checkout_key": key,
            "expected_fingerprint": fingerprint,
        },
        headers=headers,
    )


def test_missing_token_and_wrong_role_are_refused(functional_app, fixture_records):
    """GIVEN a protected order route WHEN it is called without a token, with a diner token on the vendor queue, and with a vendor token on diner checkout THEN 401/403 refuse each one before any record is read."""
    _diner_and_vendor(fixture_records)
    client = functional_app.test_client()

    missing = client.get("/api/diner/orders")
    assert missing.status_code == 401 and code(missing) == "authentication_required"

    diner_headers = login(client, DINER_EMAIL)
    vendor_headers = login(client, VENDOR_EMAIL)
    wrong_role = client.get("/api/vendor/orders", headers=diner_headers)
    assert wrong_role.status_code == 403 and code(wrong_role) == "forbidden"
    wrong_way = client.post(
        "/api/diner/orders",
        json={"payment_method": "PayNow", "simulate_success": True, "checkout_key": "x", "expected_fingerprint": "y"},
        headers=vendor_headers,
    )
    assert wrong_way.status_code == 403 and code(wrong_way) == "forbidden"


def test_foreign_records_stay_private(functional_app, fixture_records):
    """GIVEN two diners and a second stall with its own vendor in the real database WHEN each tries to read or move another account's records THEN 403 refuses every cross-account access and cross-stall move while the owners see their own data."""
    primary = _diner_and_vendor(fixture_records)
    from app.models.user import User

    foreign_diner = User.create(FOREIGN_DINER_EMAIL, PASSWORD, "diner")
    fixture_records["users"].append(foreign_diner)

    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)
    foreign_headers = login(client, FOREIGN_DINER_EMAIL)

    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(primary["item"].id), "quantity": 1}, headers=diner_headers
    ).get_json()["cart"]
    created = _checkout(client, diner_headers, "fn-access-1", cart["fingerprint"])
    assert created.status_code == 201
    order = created.get_json()["order"]
    fixture_records["orders"].append(Order.get(order["id"]))

    foreign_read = client.get(f"/api/diner/orders/{order['id']}", headers=foreign_headers)
    assert foreign_read.status_code == 403 and code(foreign_read) == "forbidden"
    foreign_list = client.get("/api/diner/orders", headers=foreign_headers)
    assert foreign_list.status_code == 200 and foreign_list.get_json()["items"] == []

    vendor_headers = login(client, VENDOR_EMAIL)
    foreign_move = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=foreign_headers
    )
    assert foreign_move.status_code == 403 and code(foreign_move) == "forbidden"

    foreign_vendor = User.create(FOREIGN_VENDOR_EMAIL, PASSWORD, "vendor")
    fixture_records["users"].append(foreign_vendor)
    foreign_vendor_headers = login(client, FOREIGN_VENDOR_EMAIL)
    no_stall_move = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=foreign_vendor_headers
    )
    assert no_stall_move.status_code == 403 and code(no_stall_move) == "forbidden"

    owner_read = client.get(f"/api/diner/orders/{order['id']}", headers=diner_headers)
    assert owner_read.status_code == 200
    owner_move = client.patch(
        f"/api/vendor/orders/{order['id']}/status", json={"status": "Preparing"}, headers=vendor_headers
    )
    assert owner_move.status_code == 200


def test_stale_checkouts_are_refused_without_persisting_orders(functional_app, fixture_records):
    """GIVEN a cart whose item is sold out, then whose stall closes, then whose price changes WHEN checkout is attempted each time with the stale fingerprint THEN 409 item_unavailable / stall_closed / price_changed refuse it and the database holds zero orders for those keys while the cart keeps its line."""
    cast = _diner_and_vendor(fixture_records)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)
    vendor_headers = login(client, VENDOR_EMAIL)

    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(cast["item"].id), "quantity": 1}, headers=diner_headers
    ).get_json()["cart"]
    fingerprint = cart["fingerprint"]

    cast["item"].is_available = False
    cast["item"].save()
    sold_out = _checkout(client, diner_headers, "fn-stale-sold", fingerprint)
    assert sold_out.status_code == 409 and code(sold_out) == "item_unavailable"

    cast["item"].is_available = True
    cast["item"].save()
    cast["stall"].is_open = False
    cast["stall"].save()
    closed = _checkout(client, diner_headers, "fn-stale-closed", fingerprint)
    assert closed.status_code == 409 and code(closed) == "stall_closed"

    cast["stall"].is_open = True
    cast["stall"].save()
    cast["item"].price_cents = 725
    cast["item"].save()
    stale_price = _checkout(client, diner_headers, "fn-stale-price", fingerprint)
    assert stale_price.status_code == 409 and code(stale_price) == "price_changed"

    assert Order.objects(checkout_key__in=["fn-stale-sold", "fn-stale-closed", "fn-stale-price"]).count() == 0
    current = client.get("/api/diner/cart", headers=diner_headers).get_json()["cart"]
    assert len(current["items"]) == 1 and current["total_cents"] == 725


def test_failed_payment_persists_nothing(functional_app, fixture_records):
    """GIVEN a non-empty cart WHEN checkout is attempted with a failed simulated payment THEN 409 payment_failed, the database holds no order for the key, and the cart is unchanged."""
    cast = _diner_and_vendor(fixture_records)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)

    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(cast["item"].id), "quantity": 2}, headers=diner_headers
    ).get_json()["cart"]
    failed = _checkout(client, diner_headers, "fn-failed", cart["fingerprint"], simulate=False)
    assert failed.status_code == 409 and code(failed) == "payment_failed"
    assert Order.objects(checkout_key="fn-failed").count() == 0
    intact = client.get("/api/diner/cart", headers=diner_headers).get_json()["cart"]
    assert len(intact["items"]) == 1 and intact["total_cents"] == 1100


def test_sequential_replay_and_conflicting_reuse(functional_app, fixture_records):
    """GIVEN a successful checkout under a key WHEN the same key and fingerprint are resubmitted and later the same key is resubmitted with different cart contents THEN the matching replay returns 200 with the stored order while the conflicting reuse is 409, and exactly one order exists for the key in the database."""
    cast = _diner_and_vendor(fixture_records)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)

    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(cast["item"].id), "quantity": 1}, headers=diner_headers
    ).get_json()["cart"]
    created = _checkout(client, diner_headers, "fn-replay", cart["fingerprint"])
    assert created.status_code == 201
    order = created.get_json()["order"]
    fixture_records["orders"].append(Order.get(order["id"]))

    replay = _checkout(client, diner_headers, "fn-replay", cart["fingerprint"])
    assert replay.status_code == 200
    assert replay.get_json()["order"]["id"] == order["id"]

    # the paid checkout cleared the cart; two lines now differ from the paid one line
    client.post(
        "/api/diner/cart/items", json={"item_id": str(cast["item"].id), "quantity": 2}, headers=diner_headers
    )
    changed = client.get("/api/diner/cart", headers=diner_headers).get_json()["cart"]
    assert changed["total_cents"] == 1100, "the rebuilt cart must differ from the paid one"
    conflict = _checkout(client, diner_headers, "fn-replay", changed["fingerprint"])
    assert conflict.status_code == 409 and code(conflict) == "checkout_key_conflict"

    assert Order.objects(checkout_key="fn-replay").count() == 1


def test_concurrent_matching_checkout_persists_exactly_one_order(functional_app, fixture_records):
    """GIVEN two threads checking out the same diner cart with the same key and fingerprint against the real unique index WHEN they race to the same endpoint THEN one request creates the order (201), the other returns the stored order as a replay (200), and the database holds exactly one order for that key."""
    from app.models.user import User
    from app.models.vendor import Vendor

    stall = Vendor(name="Race Grill", is_open=True)
    stall.save()
    fixture_records["vendors"].append(stall)
    racer = User.create("diner.race@skipq.test", PASSWORD, "diner")
    fixture_records["users"].append(racer)
    from app.models.menu_item import MenuItem

    item = MenuItem(
        vendor=stall,
        name="Race Rice",
        description="Created by the functional suite.",
        image_url="http://127.0.0.1:5001/static/images/skipq-m1.png",
        price_cents=320,
    )
    item.save()
    fixture_records["items"].append(item)

    client = functional_app.test_client()
    headers = login(client, "diner.race@skipq.test")
    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(item.id), "quantity": 1}, headers=headers
    ).get_json()["cart"]
    body = {
        "payment_method": "Card",
        "simulate_success": True,
        "checkout_key": "fn-race",
        "expected_fingerprint": cart["fingerprint"],
    }

    outcomes = {}
    errors = {}

    def worker(name):
        try:
            thread_client = functional_app.test_client()
            response = thread_client.post("/api/diner/orders", json=body, headers=headers)
            outcomes[name] = (response.status_code, response.get_json()["order"]["id"])
        except Exception as exc:  # noqa: BLE001 - surfaced in the assertion
            errors[name] = exc

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # register whatever the race stored before any assertion can fail, so
    # the fixture teardown removes this test's residue even on a red run
    fixture_records["orders"].extend(Order.objects(checkout_key="fn-race"))
    assert not errors, errors

    statuses = sorted(status for status, _ in outcomes.values())
    assert statuses == [200, 201], outcomes
    ids = {order_id for _, order_id in outcomes.values()}
    assert len(ids) == 1, "both responses must name the same stored order"

    stored = Order.objects(checkout_key="fn-race")
    assert stored.count() == 1
    assert stored.first().total_cents == 320 and stored.first().status == "Pending"


def test_purchased_snapshots_survive_menu_edits_in_the_database(functional_app, fixture_records):
    """GIVEN a paid order whose lines snapshot the item name and unit price WHEN the menu item is renamed and re-priced and the order is read back from the database THEN the order still carries the purchased name, price and total, and its serialised items do too."""
    cast = _diner_and_vendor(fixture_records)
    client = functional_app.test_client()
    diner_headers = login(client, DINER_EMAIL)

    cart = client.post(
        "/api/diner/cart/items", json={"item_id": str(cast["item"].id), "quantity": 2}, headers=diner_headers
    ).get_json()["cart"]
    created = _checkout(client, diner_headers, "fn-snapshot", cart["fingerprint"])
    assert created.status_code == 201
    order_id = created.get_json()["order"]["id"]
    fixture_records["orders"].append(Order.get(order_id))

    cast["item"].name = "Renamed Curry (new menu)"
    cast["item"].price_cents = 999
    cast["item"].save()

    reloaded = Order.get(order_id)
    line = reloaded.items[0]
    assert line.name_snapshot == "Access Curry"
    assert line.price_cents_snapshot == 550
    assert reloaded.total_cents == 1100
    assert reloaded.to_dict()["items"][0]["name"] == "Access Curry"
    assert reloaded.to_dict()["items"][0]["price_cents"] == 550
