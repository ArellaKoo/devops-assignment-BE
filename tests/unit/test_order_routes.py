"""Offline unit tests for the SkipQ checkout and order-lifecycle routes.

The controllers run for real through the Flask test client with signed
tokens; persistence is supplied by recorders (``Order.objects``,
``Order.save``, ``Order.get``, the cart seams). The shared auth gate,
role gate, JSON error contract, serialisation and the model-owned scope
checks and lifecycle guard all execute. The socket sentinel fails the
suite on any accidental database connection.
"""

from datetime import timedelta

from bson import ObjectId

import pytest

from app.auth import issue_token
from app.models.cart import Cart, CartItem
from app.models.common import same_document, utcnow
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.user import User
from app.models.vendor import Vendor

T0 = utcnow() + timedelta(hours=1)


def make_stall(name="Charcoal Grill", is_open=True):
    return Vendor(id=ObjectId(), name=name, is_open=is_open, created_at=T0)


def make_item(stall, name="Charcoal Chicken Rice", price_cents=650, available=True, active=True):
    return MenuItem(
        id=ObjectId(),
        vendor=stall,
        name=name,
        description="Grilled over charcoal.",
        image_url="http://127.0.0.1:5001/static/images/skipq-m1.png",
        price_cents=price_cents,
        is_available=available,
        is_active=active,
        created_at=T0,
        updated_at=T0,
    )


def make_user(email, role, stall=None):
    return User(id=ObjectId(), email=email, password_hash="unused-hash", role=role, vendor=stall)


def make_order(diner, stall, key, status="Pending", created_at=T0, ready_at=None, fingerprint="fp"):
    m1 = make_item(stall)
    payment = Payment(method="PayNow", status="Paid", amount_cents=1300, paid_at=created_at)
    if status == "Cancelled":
        payment = Payment(
            method="PayNow",
            status="Refunded",
            amount_cents=1300,
            paid_at=created_at,
            refunded_at=created_at,
        )
    return Order(
        id=ObjectId(),
        diner=diner,
        vendor=stall,
        items=[OrderItem(menu_item=m1, name_snapshot=m1.name, price_cents_snapshot=650, quantity=2)],
        payment=payment,
        total_cents=1300,
        queue_number="Q-" + str(ObjectId()),
        status=status,
        created_at=created_at,
        ready_at=ready_at,
        checkout_key=key,
        checkout_fingerprint=fingerprint,
    )


class _Recorder:
    """Supplies Order.objects for the tests: filters, first(), update()."""

    def __init__(self, docs=(), existing=None, update_result=1):
        self.docs = list(docs)
        self.existing = existing
        self.update_result = update_result
        self.filters = []
        self.updates = []

    def manager(self, *args, **kwargs):
        self.filters.append(kwargs)
        if "checkout_key" in kwargs:
            return _FirstOnly(self.existing)
        matched = []
        for doc in self.docs:
            ok = True
            for key, value in kwargs.items():
                if key == "status__in":
                    ok = doc.status in value
                elif key == "id":
                    ok = str(doc.id) == str(value)
                elif hasattr(doc, key):
                    attr = getattr(doc, key)
                    ok = same_document(attr, value) if isinstance(value, (User, Vendor, Order)) else attr == value
                else:
                    ok = False
                if not ok:
                    break
            if ok:
                matched.append(doc)
        return _QuerySet(matched, self)


class _FirstOnly:
    def __init__(self, doc):
        self.doc = doc

    def first(self):
        return self.doc


class _QuerySet:
    def __init__(self, docs, recorder):
        self.docs = docs
        self.recorder = recorder

    def first(self):
        return self.docs[0] if self.docs else None

    def update(self, **kwargs):
        self.recorder.updates.append(kwargs)
        return self.recorder.update_result

    def order_by(self, *args):
        return self

    def __iter__(self):
        return iter(self.docs)


_ORIGINAL_OBJECTS = None


def install_objects(recorder):
    """Swap ``Order.objects`` for the recorder's manager without triggering
    the real manager descriptor (reading ``Order.objects`` would try to
    open a database collection). The autouse fixture restores the
    original after every test."""
    global _ORIGINAL_OBJECTS
    if _ORIGINAL_OBJECTS is None:
        _ORIGINAL_OBJECTS = Order.__dict__["objects"]
    setattr(Order, "objects", recorder.manager)


@pytest.fixture(autouse=True)
def _restore_order_manager():
    yield
    global _ORIGINAL_OBJECTS
    if _ORIGINAL_OBJECTS is not None:
        setattr(Order, "objects", _ORIGINAL_OBJECTS)
        _ORIGINAL_OBJECTS = None


@pytest.fixture
def orders(monkeypatch):
    """Both stalls, both personas, D1's four-order history on S1 and D2's
    pending order on closed S2, plus D1's live cart (2xM1 + 1xM2 = 1550c)."""
    s1 = make_stall("Charcoal Grill", is_open=True)
    s2 = make_stall("Noodle Bar", is_open=False)
    d1 = make_user("diner.one@skipq.test", "diner")
    d2 = make_user("diner.two@skipq.test", "diner")
    d0 = make_user("diner.empty@skipq.test", "diner")
    v1 = make_user("vendor.one@skipq.test", "vendor", s1)
    v1b = make_user("vendor.one.backup@skipq.test", "vendor", s1)
    v2 = make_user("vendor.two@skipq.test", "vendor", s2)
    users = {str(u.id): u for u in (d1, d2, d0, v1, v1b, v2)}
    monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))

    m1 = make_item(s1, "Charcoal Chicken Rice", 650)
    m2 = make_item(s1, "Mango Sago", 250)

    p1 = make_order(d1, s1, "ck-p1", "Pending", created_at=T0, fingerprint="fp-p1")
    r1 = make_order(d1, s1, "ck-r1", "Ready", created_at=T0 - timedelta(hours=4), ready_at=T0 - timedelta(hours=2))
    c1 = make_order(d1, s1, "ck-c1", "Collected", created_at=T0 - timedelta(hours=6))
    x1 = make_order(d1, s1, "ck-x1", "Cancelled", created_at=T0 - timedelta(hours=8))
    p2 = make_order(d2, s2, "ck-p2", "Pending", created_at=T0 - timedelta(hours=1))
    docs = [p1, r1, c1, x1, p2]

    lookup = {str(o.id): o for o in docs}
    monkeypatch.setattr(Order, "get", staticmethod(lambda oid: lookup.get(oid)))
    saved = []
    monkeypatch.setattr(Order, "save", lambda self, *a, **k: (saved.append(self), self)[1])

    cart = Cart(
        id=ObjectId(),
        diner=d1,
        vendor=s1,
        items=[CartItem(menu_item=m1, quantity=2), CartItem(menu_item=m2, quantity=1)],
        created_at=T0,
        updated_at=T0,
    )
    cart_saves = []
    monkeypatch.setattr(Cart, "get_or_create_for_diner", staticmethod(lambda diner: cart))
    monkeypatch.setattr(Cart, "save", lambda self, *a, **k: (cart_saves.append(self), self)[1])

    fingerprint = Cart.compute_fingerprint(str(s1.id), [(str(m1.id), 2, m1.name, 650), (str(m2.id), 1, m2.name, 250)])
    return {
        "s1": s1,
        "s2": s2,
        "d1": d1,
        "d2": d2,
        "d0": d0,
        "v1": v1,
        "v1b": v1b,
        "v2": v2,
        "m1": m1,
        "m2": m2,
        "p1": p1,
        "r1": r1,
        "c1": c1,
        "x1": x1,
        "p2": p2,
        "cart": cart,
        "fingerprint": fingerprint,
        "saved_orders": saved,
        "cart_saves": cart_saves,
        "lookup": lookup,
    }


def bearer(app, user):
    return {"Authorization": "Bearer " + issue_token(user, app.config["TOKEN_SECRET"])}


def code(response):
    return response.get_json()["error"]["code"]


class TestCheckout:
    def test_successful_checkout_creates_pending_paid_order(self, app, orders):
        """GIVEN D1's two-line cart with a matching fingerprint WHEN checkout succeeds on PayNow THEN 201 returns a Pending/Paid order at 1550 cents with a Q- queue number and item snapshots, the cart is cleared, and exactly one order was saved."""
        rec = _Recorder()
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": True,
            "checkout_key": "ck-live-1",
            "expected_fingerprint": orders["fingerprint"],
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 201
        order = response.get_json()["order"]
        assert order["status"] == "Pending"
        assert order["total_cents"] == 1550
        assert order["payment"]["status"] == "Paid"
        assert order["payment"]["amount_cents"] == 1550
        assert order["queue_number"].startswith("Q-")
        assert [(i["name"], i["price_cents"], i["quantity"]) for i in order["items"]] == [
            ("Charcoal Chicken Rice", 650, 2),
            ("Mango Sago", 250, 1),
        ]
        assert len(orders["saved_orders"]) == 1
        assert orders["cart"].items == [] and orders["cart"].vendor is None
        assert len(orders["cart_saves"]) == 1

    def test_matching_replay_returns_stored_order(self, app, orders):
        """GIVEN a stored order for the checkout key and fingerprint WHEN the same checkout is resubmitted THEN 200 returns the stored order and no new order is saved, even though the cart was already cleared."""
        rec = _Recorder(existing=orders["p1"])
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": True,
            "checkout_key": "ck-p1",
            "expected_fingerprint": "fp-p1",
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 200
        assert response.get_json()["order"]["id"] == str(orders["p1"].id)
        assert orders["saved_orders"] == []

    def test_conflicting_key_reuse_is_refused(self, app, orders):
        """GIVEN a stored order for the key with different contents WHEN the key is resubmitted with a new fingerprint THEN 409 checkout_key_conflict refuses it and nothing is saved."""
        rec = _Recorder(existing=orders["p1"])
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": True,
            "checkout_key": "ck-p1",
            "expected_fingerprint": "changed-cart",
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 409
        assert code(response) == "checkout_key_conflict"
        assert orders["saved_orders"] == []

    def test_failed_simulated_payment_keeps_cart(self, app, orders):
        """GIVEN a failed simulated payment WHEN checkout is attempted THEN 409 payment_failed, nothing is saved, and the cart keeps its lines."""
        rec = _Recorder()
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": False,
            "checkout_key": "ck-fail",
            "expected_fingerprint": orders["fingerprint"],
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 409
        assert code(response) == "payment_failed"
        assert orders["saved_orders"] == []
        assert len(orders["cart"].items) == 2

    def test_unknown_payment_method_is_refused(self, app, orders):
        """GIVEN a payment method outside PayNow/Card/Cashless WHEN checkout is attempted THEN 400 validation_error names the allowed methods."""
        rec = _Recorder()
        install_objects(rec)
        body = {
            "payment_method": "Cash",
            "simulate_success": True,
            "checkout_key": "ck-m",
            "expected_fingerprint": orders["fingerprint"],
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_missing_expected_fingerprint_is_refused(self, app, orders):
        """GIVEN a checkout body without the cart's expected fingerprint WHEN checkout is attempted THEN 400 validation_error asks for the checkout fields, since a stale cart must not be charged."""
        rec = _Recorder()
        install_objects(rec)
        body = {"payment_method": "PayNow", "simulate_success": True, "checkout_key": "ck-no-fp"}
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_non_object_body_is_refused(self, app, orders):
        """GIVEN a JSON array checkout body WHEN checkout is attempted THEN 400 validation_error, nothing is saved."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().post("/api/diner/orders", json=[1, 2], headers=bearer(app, orders["d1"]))
        assert response.status_code == 400
        assert code(response) == "validation_error"
        assert orders["saved_orders"] == []

    def test_empty_cart_is_refused(self, app, orders):
        """GIVEN an empty cart WHEN checkout is attempted THEN 409 cart_empty and nothing is saved."""
        orders["cart"].items = []
        rec = _Recorder()
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": True,
            "checkout_key": "ck-e",
            "expected_fingerprint": "fp",
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 409
        assert code(response) == "cart_empty"
        assert orders["saved_orders"] == []

    def test_closed_stall_checkout_is_refused(self, app, orders):
        """GIVEN a cart on a stall the vendor just closed WHEN the diner checks out THEN 409 stall_closed names the stall."""
        orders["s1"].is_open = False
        rec = _Recorder()
        install_objects(rec)
        body = {
            "payment_method": "PayNow",
            "simulate_success": True,
            "checkout_key": "ck-c",
            "expected_fingerprint": orders["fingerprint"],
        }
        response = app.test_client().post("/api/diner/orders", json=body, headers=bearer(app, orders["d1"]))
        assert response.status_code == 409
        assert code(response) == "stall_closed"

    def test_vendor_token_cannot_checkout(self, app, orders):
        """GIVEN a vendor token WHEN a diner checkout route is called THEN 403 forbidden names the diner persona."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().post(
            "/api/diner/orders",
            json={"payment_method": "PayNow", "simulate_success": True, "checkout_key": "k", "expected_fingerprint": "f"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"

    def test_checkout_without_token_is_refused(self, app, orders):
        """GIVEN no Authorization header WHEN checkout is attempted THEN 401 authentication_required."""
        response = app.test_client().post("/api/diner/orders", json={})
        assert response.status_code == 401
        assert code(response) == "authentication_required"


class TestDinerOrderReads:
    def test_diner_lists_all_own_orders(self, app, orders):
        """GIVEN D1's four stored orders and D2's order on another stall WHEN D1 lists orders without a view THEN all four of D1's orders come back, newest first, and D2's order stays out."""
        rec = _Recorder(docs=[orders["p1"], orders["r1"], orders["c1"], orders["x1"], orders["p2"]])
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders", headers=bearer(app, orders["d1"]))
        assert response.status_code == 200
        ids = [o["id"] for o in response.get_json()["items"]]
        assert ids == [str(o.id) for o in (orders["p1"], orders["r1"], orders["c1"], orders["x1"])]

    def test_current_view_lists_only_live_orders(self, app, orders):
        """GIVEN D1's history WHEN the list is filtered to view=current THEN only the Pending and Ready orders remain."""
        rec = _Recorder(docs=[orders["p1"], orders["r1"], orders["c1"], orders["x1"]])
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders?view=current", headers=bearer(app, orders["d1"]))
        ids = [o["id"] for o in response.get_json()["items"]]
        assert ids == [str(orders["p1"].id), str(orders["r1"].id)]

    def test_history_view_lists_only_terminal_orders(self, app, orders):
        """GIVEN D1's history WHEN the list is filtered to view=history THEN only the Collected and Cancelled orders remain."""
        rec = _Recorder(docs=[orders["p1"], orders["r1"], orders["c1"], orders["x1"]])
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders?view=history", headers=bearer(app, orders["d1"]))
        ids = [o["id"] for o in response.get_json()["items"]]
        assert ids == [str(orders["c1"].id), str(orders["x1"].id)]

    def test_invalid_view_is_refused(self, app, orders):
        """GIVEN a view value outside all/current/history WHEN the list is requested THEN 400 validation_error names the allowed views."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders?view=today", headers=bearer(app, orders["d1"]))
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_diner_without_orders_gets_empty_list(self, app, orders):
        """GIVEN a diner with no stored orders WHEN they list orders THEN 200 with an empty items array, not an error."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders", headers=bearer(app, orders["d0"]))
        assert response.status_code == 200
        assert response.get_json()["items"] == []

    def test_diner_reads_own_order(self, app, orders):
        """GIVEN D1's stored order WHEN D1 opens it THEN 200 with the order details and snapshots, and no vendor actions are offered to the diner."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().get(f"/api/diner/orders/{orders['p1'].id}", headers=bearer(app, orders["d1"]))
        assert response.status_code == 200
        body = response.get_json()["order"]
        assert body["id"] == str(orders["p1"].id)
        assert body["total_cents"] == 1300
        assert "allowed_actions" not in body

    def test_diner_cannot_read_another_diners_order(self, app, orders):
        """GIVEN D1's order WHEN D2 requests it by id THEN 403 forbidden keeps the order private."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().get(f"/api/diner/orders/{orders['p1'].id}", headers=bearer(app, orders["d2"]))
        assert response.status_code == 403
        assert code(response) == "forbidden"

    def test_unknown_order_id_is_404(self, app, orders, monkeypatch):
        """GIVEN a well-formed but unknown order id WHEN it is requested THEN 404 not_found."""
        monkeypatch.setattr(Order, "get", staticmethod(lambda oid: None))
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get(
            "/api/diner/orders/" + str(ObjectId()), headers=bearer(app, orders["d1"])
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_malformed_order_id_is_404_not_500(self, app, orders):
        """GIVEN an order id that is not an ObjectId WHEN it is requested THEN 404 not_found, never a 500."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get("/api/diner/orders/not-an-objectid", headers=bearer(app, orders["d1"]))
        assert response.status_code == 404
        assert code(response) == "not_found"


class TestVendorOrders:
    def test_vendor_lists_own_stall_queue_with_actions(self, app, orders):
        """GIVEN S1's four stored orders WHEN V1 lists the order queue THEN only S1's orders come back, each with the vendor's allowed actions (Preparing+Cancelled on the Pending one)."""
        rec = _Recorder(docs=[orders["p1"], orders["r1"], orders["c1"], orders["x1"]])
        install_objects(rec)
        response = app.test_client().get("/api/vendor/orders", headers=bearer(app, orders["v1"]))
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert [o["id"] for o in items] == [str(o.id) for o in (orders["p1"], orders["r1"], orders["c1"], orders["x1"])]
        assert items[0]["allowed_actions"] == ["Preparing", "Cancelled"]
        assert items[1]["allowed_actions"] == ["Collected", "NoShow"]
        assert items[2]["allowed_actions"] == []

    def test_closed_stall_queue_stays_processible(self, app, orders):
        """GIVEN a closed stall with a pending paid order WHEN its vendor lists the queue THEN the order is still there and still actionable, because closing the stall only blocks new checkouts (deferred close-stall item)."""
        assert orders["s2"].is_open is False
        rec = _Recorder(docs=[orders["p2"]])
        install_objects(rec)
        response = app.test_client().get("/api/vendor/orders", headers=bearer(app, orders["v2"]))
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert [o["id"] for o in items] == [str(orders["p2"].id)]
        assert items[0]["allowed_actions"] == ["Preparing", "Cancelled"]

    def test_shared_stall_account_sees_same_queue(self, app, orders):
        """GIVEN the backup vendor account on the same stall WHEN it lists the queue THEN it sees the identical orders, because the account is linked to the stall, not the other way round."""
        rec = _Recorder(docs=[orders["p1"], orders["r1"], orders["c1"], orders["x1"]])
        install_objects(rec)
        response = app.test_client().get("/api/vendor/orders", headers=bearer(app, orders["v1b"]))
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert [o["id"] for o in items] == [str(o.id) for o in (orders["p1"], orders["r1"], orders["c1"], orders["x1"])]

    def test_vendor_reads_own_stall_order(self, app, orders):
        """GIVEN V1's stall order WHEN V1 opens it THEN 200 with the order and the allowed actions for the current state."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().get(f"/api/vendor/orders/{orders['p1'].id}", headers=bearer(app, orders["v1"]))
        assert response.status_code == 200
        body = response.get_json()["order"]
        assert body["id"] == str(orders["p1"].id)
        assert body["allowed_actions"] == ["Preparing", "Cancelled"]

    def test_foreign_stall_order_detail_is_403(self, app, orders):
        """GIVEN V2's pending order on S2 WHEN V1 requests it THEN 403 forbidden keeps stall queues separate."""
        rec = _Recorder(docs=[orders["p2"]])
        install_objects(rec)
        response = app.test_client().get(f"/api/vendor/orders/{orders['p2'].id}", headers=bearer(app, orders["v1"]))
        assert response.status_code == 403
        assert code(response) == "forbidden"

    def test_diner_token_cannot_open_vendor_orders(self, app, orders):
        """GIVEN a diner token WHEN a vendor order route is called THEN 403 forbidden names the vendor persona."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get("/api/vendor/orders", headers=bearer(app, orders["d1"]))
        assert response.status_code == 403
        assert code(response) == "forbidden"

    def test_vendor_unknown_order_is_404(self, app, orders, monkeypatch):
        """GIVEN an unknown order id WHEN the vendor requests it THEN 404 not_found."""
        monkeypatch.setattr(Order, "get", staticmethod(lambda oid: None))
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().get(
            "/api/vendor/orders/" + str(ObjectId()), headers=bearer(app, orders["v1"])
        )
        assert response.status_code == 404
        assert code(response) == "not_found"


class TestVendorTransitions:
    def test_pending_to_preparing_persists(self, app, orders):
        """GIVEN a Pending order on V1's stall WHEN V1 patches it to Preparing THEN 200 returns the new state, and the update was issued against the expected current status with set__status only."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p1'].id}/status",
            json={"status": "Preparing"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 200
        assert response.get_json()["order"]["status"] == "Preparing"
        assert rec.updates == [{"set__status": "Preparing"}]
        assert str(rec.filters[-1].get("status")) == "Pending"
        assert orders["p1"].status == "Preparing"

    def test_preparing_to_ready_records_ready_at(self, app, orders):
        """GIVEN a Preparing order WHEN V1 patches it to Ready THEN 200 and the update carries ready_at set to the transition instant."""
        preparing = make_order(orders["d1"], orders["s1"], "ck-pr", "Preparing", created_at=T0 - timedelta(hours=1))
        orders["lookup"][str(preparing.id)] = preparing
        rec = _Recorder(docs=[preparing])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{preparing.id}/status",
            json={"status": "Ready"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 200
        assert rec.updates[0]["set__ready_at"] is not None
        assert preparing.ready_at is not None

    def test_ready_to_noshow_after_boundary(self, app, orders):
        """GIVEN a Ready order two hours into its boundary WHEN V1 patches it to NoShow THEN 200 records the terminal state."""
        rec = _Recorder(docs=[orders["r1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['r1'].id}/status",
            json={"status": "NoShow"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 200
        assert response.get_json()["order"]["status"] == "NoShow"

    def test_pending_cannot_jump_to_ready(self, app, orders):
        """GIVEN a Pending order WHEN V1 tries to skip straight to Ready THEN 409 invalid_transition and no update is issued."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p1'].id}/status",
            json={"status": "Ready"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 409
        assert code(response) == "invalid_transition"
        assert rec.updates == []
        assert orders["p1"].status == "Pending"

    def test_terminal_order_refuses_changes(self, app, orders):
        """GIVEN a Collected order WHEN V1 tries to move it again THEN 409 invalid_transition says the order is final."""
        rec = _Recorder(docs=[orders["c1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['c1'].id}/status",
            json={"status": "Preparing"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 409
        assert code(response) == "invalid_transition"
        assert rec.updates == []

    def test_noshow_before_boundary_is_refused(self, app, orders):
        """GIVEN a Ready order five minutes into its 30-minute boundary WHEN V1 marks NoShow THEN 409 no_show_too_early and nothing is written."""
        early = make_order(
            orders["d1"],
            orders["s1"],
            "ck-early",
            "Ready",
            created_at=T0 - timedelta(hours=1),
            ready_at=T0 - timedelta(minutes=5),
        )
        orders["lookup"][str(early.id)] = early
        rec = _Recorder(docs=[early])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{early.id}/status",
            json={"status": "NoShow"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 409
        assert code(response) == "no_show_too_early"
        assert rec.updates == []

    def test_unknown_status_is_refused(self, app, orders):
        """GIVEN a stored status outside the canonical six WHEN it is submitted as the target THEN 409 invalid_transition names the allowed values."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p1'].id}/status",
            json={"status": "Done"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 409
        assert code(response) == "invalid_transition"

    def test_missing_status_field_is_400(self, app, orders):
        """GIVEN a transition body without a target status WHEN it is submitted THEN 400 validation_error asks for the status."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p1'].id}/status", json={}, headers=bearer(app, orders["v1"])
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_foreign_stall_vendor_cannot_transition(self, app, orders):
        """GIVEN V2's order on S2 WHEN V1 tries to move it THEN 403 forbidden and no update is issued."""
        rec = _Recorder(docs=[orders["p2"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p2'].id}/status",
            json={"status": "Preparing"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert rec.updates == []

    def test_diner_token_cannot_transition(self, app, orders):
        """GIVEN a diner token WHEN a vendor transition route is called THEN 403 forbidden, no update is issued."""
        rec = _Recorder(docs=[orders["p1"]])
        install_objects(rec)
        response = app.test_client().patch(
            f"/api/vendor/orders/{orders['p1'].id}/status",
            json={"status": "Preparing"},
            headers=bearer(app, orders["d1"]),
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert rec.updates == []

    def test_malformed_order_id_is_404(self, app, orders):
        """GIVEN an order id that is not an ObjectId WHEN a transition is requested THEN 404 not_found, never a 500."""
        rec = _Recorder()
        install_objects(rec)
        response = app.test_client().patch(
            "/api/vendor/orders/not-an-objectid/status",
            json={"status": "Preparing"},
            headers=bearer(app, orders["v1"]),
        )
        assert response.status_code == 404
        assert code(response) == "not_found"
