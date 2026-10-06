"""Offline unit tests for the SkipQ order lifecycle guard and checkout rules.

``can_transition``/``transition_to``/``place_from_cart`` run for real on
in-memory records; only the persistence boundary (``Order.objects`` query
entry point, ``Order.save``) is supplied by the tests, and the no-show
clock is injected. The socket sentinel fails the suite on any accidental
database connection.
"""

from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError
import pytest

from app.errors import DomainError
from app.models.cart import Cart, CartItem
from app.models.common import same_document, utcnow
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.user import User
from app.models.vendor import Vendor

T0 = utcnow() + timedelta(hours=1)
READY_BASE = T0 - timedelta(minutes=31)  # comfortably past the 30-minute boundary


def _code(excinfo):
    """Stable error code from a raised exception or a pytest ExceptionInfo."""
    return getattr(excinfo, "code", None) or excinfo.value.code


def make_stall(name="Charcoal Grill", is_open=True):
    return Vendor(id=ObjectId(), name=name, is_open=is_open)


def make_vendor(stall, email="vendor.one@skipq.test"):
    return User(id=ObjectId(), email=email, password_hash="unused-hash", role="vendor", vendor=stall)


def make_diner(email="diner.one@skipq.test"):
    return User(id=ObjectId(), email=email, password_hash="unused-hash", role="diner")


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
    )


def make_cart(diner, stall, m1, m2=None):
    lines = [CartItem(menu_item=m1, quantity=2)]
    if m2 is not None:
        lines.append(CartItem(menu_item=m2, quantity=1))
    return Cart(id=ObjectId(), diner=diner, vendor=stall, items=lines, created_at=T0, updated_at=T0)


def fingerprint_for(stall, m1, m2=None):
    lines = [(str(m1.id), 2, m1.name, 650)]
    if m2 is not None:
        lines.append((str(m2.id), 1, m2.name, 250))
    return Cart.compute_fingerprint(str(stall.id), lines)


def make_order(diner, stall, status="Pending", created_at=T0, ready_at=None, key="ck-1", fingerprint="fp"):
    m1 = make_item(stall)
    return Order(
        id=ObjectId(),
        diner=diner,
        vendor=stall,
        items=[OrderItem(menu_item=m1, name_snapshot=m1.name, price_cents_snapshot=650, quantity=2)],
        payment=Payment(method="PayNow", status="Paid", amount_cents=1300, paid_at=created_at),
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
        self.existing = existing  # returned by find_by_checkout_key
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
    """Swap ``Order.objects`` for the recorder's manager without triggering the
    real manager descriptor (reading ``Order.objects`` would try to open a
    database collection). The autouse fixture restores the original after
    every test."""
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
def diner_cart(monkeypatch):
    """D1's cart on an open stall: 2xM1 (650c) + 1xM2 (250c) = 1550c."""
    stall = make_stall()
    diner = make_diner()
    vendor_user = make_vendor(stall)
    m1 = make_item(stall, "Charcoal Chicken Rice", 650)
    m2 = make_item(stall, "Mango Sago", 250)
    cart = make_cart(diner, stall, m1, m2)
    saves = []
    monkeypatch.setattr(Cart, "save", lambda self, *a, **k: (saves.append(self), self)[1])
    return {
        "stall": stall,
        "diner": diner,
        "vendor_user": vendor_user,
        "foreign_vendor": make_vendor(make_stall("Noodle Bar"), "vendor.two@skipq.test"),
        "m1": m1,
        "m2": m2,
        "cart": cart,
        "fingerprint": fingerprint_for(stall, m1, m2),
        "saves": saves,
    }


class TestTransitionMatrix:
    @pytest.mark.parametrize("current", ["Pending", "Preparing", "Ready", "Collected", "Cancelled", "NoShow"])
    @pytest.mark.parametrize("target", ["Pending", "Preparing", "Ready", "Collected", "Cancelled", "NoShow", "Bogus"])
    def test_state_pairs(self, diner_cart, current, target):
        """GIVEN an order in ``current`` state and the 30-minute no-show boundary already passed WHEN the guard evaluates the move to ``target`` THEN exactly the five canonical edges are allowed and every other pair is refused with a stable code."""
        from app.models.order import ALLOWED_EDGES, TERMINAL_STATUSES

        stall = diner_cart["stall"]
        order = make_order(diner_cart["diner"], stall, status=current, ready_at=READY_BASE)
        allowed, error = order.can_transition(target, diner_cart["vendor_user"], T0)
        expected_allowed = (current, target) in ALLOWED_EDGES
        if expected_allowed:
            assert error is None
        else:
            assert not allowed
            assert _code(error) == "invalid_transition"
            if current in TERMINAL_STATUSES:
                assert "final" in error.message or target not in ("Pending", "Preparing", "Ready", "Collected", "Cancelled", "NoShow")

    def test_repeat_transition_is_refused(self, diner_cart):
        """GIVEN a Pending order WHEN Pending->Pending is proposed THEN it is refused (the four allowed edges are only forward moves and the refund/NoShow exceptions)."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        allowed, error = order.can_transition("Pending", diner_cart["vendor_user"], T0)
        assert not allowed and _code(error) == "invalid_transition"


class TestNoShowBoundary:
    @pytest.mark.parametrize("seconds, allowed", [(1799, False), (1800, True), (1801, True)])
    def test_29m59_30m00_30m01(self, diner_cart, seconds, allowed):
        """GIVEN an order ready exactly at T0 WHEN NoShow is proposed 29:59, 30:00, or 30:01 later THEN only the boundary-inclusive 30:00 and beyond are allowed."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Ready", ready_at=T0)
        now = T0 + timedelta(seconds=seconds)
        result, error = order.can_transition("NoShow", diner_cart["vendor_user"], now)
        assert result is allowed
        if not allowed:
            assert _code(error) == "no_show_too_early"

    def test_ready_without_ready_at_is_refused(self, diner_cart):
        """GIVEN a Ready order with no ready_at timestamp WHEN NoShow is proposed THEN the boundary cannot be evaluated and the move is refused no_show_too_early."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Ready", ready_at=None)
        result, error = order.can_transition("NoShow", diner_cart["vendor_user"], T0 + timedelta(hours=1))
        assert not result and _code(error) == "no_show_too_early"


class TestActorScope:
    def test_diner_cannot_transition(self, diner_cart):
        """GIVEN a diner account WHEN they attempt any status change THEN 403 forbidden, even for their own order."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        result, error = order.can_transition("Preparing", diner_cart["diner"], T0)
        assert not result and _code(error) == "forbidden"

    def test_foreign_stall_vendor_cannot_transition(self, diner_cart):
        """GIVEN a vendor on another stall WHEN they attempt a change on this order THEN 403 forbidden."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        result, error = order.can_transition("Preparing", diner_cart["foreign_vendor"], T0)
        assert not result and _code(error) == "forbidden"

    def test_vendor_without_stall_cannot_transition(self, diner_cart):
        """GIVEN a vendor-role account with no stall link WHEN they attempt a change THEN 403 forbidden."""
        homeless = User(id=ObjectId(), email="vendor.none@skipq.test", password_hash="x", role="vendor")
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        result, error = order.can_transition("Preparing", homeless, T0)
        assert not result and _code(error) == "forbidden"


class TestTransitionPersistence:
    def test_allowed_transition_updates_expected_status(self, diner_cart, monkeypatch):
        """GIVEN a Pending order WHEN the stall vendor transitions it to Preparing THEN exactly one update is issued filtered on the expected current status, and the in-memory order reflects it."""
        rec = _Recorder()
        install_objects(rec)
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        result = order.transition_to(diner_cart["vendor_user"], "Preparing", T0)
        assert result is order
        assert order.status == "Preparing"
        assert rec.updates == [{"set__status": "Preparing"}]
        assert rec.filters and str(rec.filters[0].get("status")) == "Pending" and str(rec.filters[0].get("id")) == str(order.id)

    def test_refused_transition_writes_nothing(self, diner_cart, monkeypatch):
        """GIVEN a Preparing order WHEN the illegal move to Cancelled is attempted THEN the error is raised, no update is issued, and the status is unchanged."""
        rec = _Recorder()
        install_objects(rec)
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Preparing")
        with pytest.raises(DomainError) as excinfo:
            order.transition_to(diner_cart["vendor_user"], "Cancelled", T0)
        assert _code(excinfo) == "invalid_transition"
        assert rec.updates == []
        assert order.status == "Preparing"

    def test_ready_transition_records_ready_at(self, diner_cart, monkeypatch):
        """GIVEN a Preparing order WHEN it moves to Ready THEN the update carries ready_at set to the transition instant."""
        rec = _Recorder()
        install_objects(rec)
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Preparing")
        order.transition_to(diner_cart["vendor_user"], "Ready", T0)
        assert rec.updates[0]["set__ready_at"] == T0
        assert order.ready_at == T0

    def test_cancellation_refunds_the_payment(self, diner_cart, monkeypatch):
        """GIVEN a Pending order WHEN it is cancelled THEN the update marks the embedded payment Refunded with the refund instant and the order state is Cancelled."""
        rec = _Recorder()
        install_objects(rec)
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        order.transition_to(diner_cart["vendor_user"], "Cancelled", T0)
        assert rec.updates[0]["set__payment__status"] == "Refunded"
        assert rec.updates[0]["set__payment__refunded_at"] == T0
        assert order.status == "Cancelled"
        assert order.payment.status == "Refunded"

    def test_concurrent_change_wins_the_race(self, diner_cart, monkeypatch):
        """GIVEN a stale in-memory order WHEN the expected-status update matches nothing (0 modified) THEN invalid_transition is raised and the local document is not moved."""
        rec = _Recorder(update_result=0)
        install_objects(rec)
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        with pytest.raises(DomainError) as excinfo:
            order.transition_to(diner_cart["vendor_user"], "Preparing", T0)
        assert _code(excinfo) == "invalid_transition"
        assert order.status == "Pending"


class TestAllowedActions:
    def test_pending_order_offers_prepare_and_cancel(self, diner_cart):
        """GIVEN a Pending order WHEN the stall vendor's allowed actions are computed THEN exactly Preparing and Cancelled are offered."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        assert order.allowed_actions(diner_cart["vendor_user"], T0) == ["Preparing", "Cancelled"]

    def test_ready_order_past_boundary_offers_collect_and_noshow(self, diner_cart):
        """GIVEN a Ready order past the 30-minute boundary WHEN the vendor's allowed actions are computed THEN Collected and NoShow are offered."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Ready", ready_at=READY_BASE)
        assert order.allowed_actions(diner_cart["vendor_user"], T0) == ["Collected", "NoShow"]

    def test_ready_order_before_boundary_offers_only_collect(self, diner_cart):
        """GIVEN a Ready order five minutes into its boundary WHEN the vendor's allowed actions are computed THEN NoShow is not offered yet."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Ready", ready_at=T0 - timedelta(minutes=5))
        assert order.allowed_actions(diner_cart["vendor_user"], T0) == ["Collected"]

    def test_terminal_and_foreign_actors_offer_nothing(self, diner_cart):
        """GIVEN a Collected order, a diner actor, and a foreign-stall vendor WHEN allowed actions are computed THEN none of them gets any action on it."""
        order = make_order(diner_cart["diner"], diner_cart["stall"], status="Collected")
        assert order.allowed_actions(diner_cart["vendor_user"], T0) == []
        pending = make_order(diner_cart["diner"], diner_cart["stall"], status="Pending")
        assert pending.allowed_actions(diner_cart["diner"], T0) == []
        assert pending.allowed_actions(diner_cart["foreign_vendor"], T0) == []


class TestPlaceFromCart:
    def test_successful_checkout_creates_pending_paid_order(self, diner_cart, monkeypatch):
        """GIVEN a two-line cart on an open stall with a matching fingerprint WHEN checkout succeeds on PayNow THEN the order is Pending/Paid at 1550 cents with a Q- queue number, name/price snapshots, and the cart cleared."""
        rec = _Recorder()
        saved = []
        install_objects(rec)
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: (saved.append(self), self)[1])
        order, created = Order.place_from_cart(
            diner_cart["diner"],
            diner_cart["cart"],
            "PayNow",
            True,
            "ck-live-1",
            diner_cart["fingerprint"],
            T0,
        )
        assert created is True
        assert order.status == "Pending"
        assert order.payment.status == "Paid"
        assert order.total_cents == 1550
        assert order.payment.amount_cents == 1550
        assert order.queue_number.startswith("Q-")
        assert [(i.name_snapshot, i.price_cents_snapshot, i.quantity) for i in order.items] == [
            ("Charcoal Chicken Rice", 650, 2),
            ("Mango Sago", 250, 1),
        ]
        assert order.checkout_key == "ck-live-1"
        assert saved and saved[0] is order
        assert diner_cart["cart"].items == [] and diner_cart["cart"].vendor is None

    def test_snapshots_survive_later_menu_edits(self, diner_cart, monkeypatch):
        """GIVEN a paid order with name/price snapshots WHEN the menu item is later renamed and re-priced THEN the order's line still shows what was purchased."""
        rec = _Recorder()
        install_objects(rec)
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: self)
        order, _created = Order.place_from_cart(
            diner_cart["diner"], diner_cart["cart"], "Card", True, "ck-live-2",
            diner_cart["fingerprint"], T0,
        )
        diner_cart["m1"].name = "Grilled Chicken Rice (old menu)"
        diner_cart["m1"].price_cents = 999
        assert order.items[0].name_snapshot == "Charcoal Chicken Rice"
        assert order.items[0].price_cents_snapshot == 650
        assert order.to_dict()["items"][0]["name"] == "Charcoal Chicken Rice"

    def test_matching_replay_returns_stored_order_even_with_empty_cart(self, diner_cart, monkeypatch):
        """GIVEN a stored order for a checkout key WHEN the same key and fingerprint are resubmitted after the cart was cleared THEN the stored order is returned as a replay, not a new order and not an error."""
        stored = make_order(
            diner_cart["diner"], diner_cart["stall"], key="ck-replay", fingerprint=diner_cart["fingerprint"]
        )
        rec = _Recorder(existing=stored)
        install_objects(rec)
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: pytest.fail("a replay must not save a new order"))
        diner_cart["cart"].items = []
        order, created = Order.place_from_cart(
            diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-replay",
            diner_cart["fingerprint"], T0,
        )
        assert order is stored and created is False

    def test_conflicting_key_reuse_is_refused(self, diner_cart, monkeypatch):
        """GIVEN a stored order for a checkout key WHEN the key is resubmitted with a different fingerprint THEN 409 checkout_key_conflict refuses it, even with an empty cart."""
        stored = make_order(diner_cart["diner"], diner_cart["stall"], key="ck-x", fingerprint="something-else")
        rec = _Recorder(existing=stored)
        install_objects(rec)
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: pytest.fail("a conflict must not save a new order"))
        diner_cart["cart"].items = []
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-x", "new-fingerprint", T0)
        assert _code(excinfo) == "checkout_key_conflict"

    @pytest.mark.parametrize(
        "method, key, simulate, fingerprint, expected",
        [
            ("Banc", "ck", True, "fp", "validation_error"),
            ("PayNow", "", True, "fp", "validation_error"),
            ("PayNow", None, True, "fp", "validation_error"),
            ("PayNow", "ck", "yes", "fp", "validation_error"),
            ("PayNow", "ck", None, "fp", "validation_error"),
        ],
    )
    def test_malformed_checkout_fields(self, diner_cart, monkeypatch, method, key, simulate, fingerprint, expected):
        """GIVEN a checkout request with an invalid method, missing key, or non-boolean simulation result WHEN it is processed THEN 400 validation_error names the problem before any lookup or save."""
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], method, simulate, key, fingerprint, T0)
        assert _code(excinfo) == expected

    def test_empty_cart_is_refused(self, diner_cart, monkeypatch):
        """GIVEN an empty cart with no stored key WHEN checkout is attempted THEN 409 cart_empty is raised and nothing is saved."""
        rec = _Recorder()
        install_objects(rec)
        saved = []
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: (saved.append(self), self)[1])
        diner_cart["cart"].items = []
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-e", "fp", T0)
        assert _code(excinfo) == "cart_empty"
        assert saved == []

    def test_closed_stall_is_refused(self, diner_cart, monkeypatch):
        """GIVEN a non-empty cart on a closed stall WHEN checkout is attempted THEN 409 stall_closed names the stall."""
        diner_cart["stall"].is_open = False
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-c", diner_cart["fingerprint"], T0)
        assert _code(excinfo) == "stall_closed"

    def test_sold_out_line_is_refused(self, diner_cart, monkeypatch):
        """GIVEN a cart whose item is marked sold out after it was added WHEN checkout is attempted THEN 409 item_unavailable names the item."""
        diner_cart["m1"].is_available = False
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-s", "fp", T0)
        assert _code(excinfo) == "item_unavailable"

    def test_soft_deleted_line_is_refused(self, diner_cart, monkeypatch):
        """GIVEN a cart whose item was soft-deleted after it was added WHEN checkout is attempted THEN 409 item_unavailable refuses it."""
        diner_cart["m2"].is_active = False
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-d", "fp", T0)
        assert _code(excinfo) == "item_unavailable"

    def test_stale_fingerprint_is_refused(self, diner_cart, monkeypatch):
        """GIVEN a cart whose prices changed since the fingerprint was computed WHEN checkout is attempted THEN 409 price_changed asks the diner to review the cart, and nothing is saved."""
        saved = []
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: (saved.append(self), self)[1])
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-p", "stale-fingerprint", T0)
        assert _code(excinfo) == "price_changed"
        assert saved == []

    def test_failed_payment_saves_nothing_and_keeps_cart(self, diner_cart, monkeypatch):
        """GIVEN a failed simulated payment WHEN checkout is attempted THEN 409 payment_failed is raised, no order is saved, and the cart keeps its lines."""
        saved = []
        monkeypatch.setattr(Order, "save", lambda self, *a, **k: (saved.append(self), self)[1])
        rec = _Recorder()
        install_objects(rec)
        with pytest.raises(DomainError) as excinfo:
            Order.place_from_cart(diner_cart["diner"], diner_cart["cart"], "PayNow", False, "ck-f", diner_cart["fingerprint"], T0)
        assert _code(excinfo) == "payment_failed"
        assert saved == []
        assert len(diner_cart["cart"].items) == 2

    def test_concurrent_matching_request_returns_winner(self, diner_cart, monkeypatch):
        """GIVEN a lost (diner, checkout_key) uniqueness race WHEN the save raises the duplicate-key error with the winner retrievable and matching THEN the winner is returned as a replay instead of an error."""
        winner = make_order(diner_cart["diner"], diner_cart["stall"], key="ck-race", fingerprint=diner_cart["fingerprint"])
        rec = _Recorder(existing=winner)
        install_objects(rec)

        def racing_save(self, *a, **k):
            raise DuplicateKeyError("E11000 duplicate key")

        monkeypatch.setattr(Order, "save", racing_save)
        order, created = Order.place_from_cart(
            diner_cart["diner"], diner_cart["cart"], "PayNow", True, "ck-race",
            diner_cart["fingerprint"], T0,
        )
        assert order is winner and created is False
