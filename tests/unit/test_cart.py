"""Offline unit tests for SkipQ cart rules and cents arithmetic (Q4(a)).

The cart decision logic runs for real on in-memory records; only the
persistence boundary (``save``) is mocked. No MongoDB connection is made:
the shared unit fixture sentinel would fail on any accidental socket use.
"""

from bson import ObjectId

import pytest

from app.errors import DomainError
from app.models.cart import Cart, CartItem
from app.models.menu_item import MenuItem
from app.models.user import User
from app.models.vendor import Vendor


def _code(excinfo):
    return excinfo.value.code


def make_diner(email="diner.one@skipq.test"):
    return User(id=ObjectId(), email=email, password_hash="unused-hash", role="diner")


def make_vendor(name="Charcoal Grill", is_open=True):
    return Vendor(id=ObjectId(), name=name, is_open=is_open)


def make_item(vendor, name="Charcoal Chicken Rice", price_cents=650, available=True, active=True):
    return MenuItem(
        id=ObjectId(),
        vendor=vendor,
        name=name,
        description="Grilled over charcoal.",
        image_url="http://127.0.0.1:5001/static/images/skipq-m1.png",
        price_cents=price_cents,
        is_available=available,
        is_active=active,
    )


def make_cart(diner, vendor=None, items=None):
    return Cart(id=ObjectId(), diner=diner, vendor=vendor, items=items or [])


@pytest.fixture(autouse=True)
def no_persistence(monkeypatch):
    """Mock the persistence boundary so cart rules run without MongoDB."""
    calls = []
    monkeypatch.setattr(Cart, "save", lambda self, *args, **kwargs: (calls.append(self), self)[1])
    return calls


class TestQuantityRule:
    @pytest.mark.parametrize("value", [1, 2, 10])
    def test_accepts_positive_integer_quantity(self, value):
        """GIVEN a positive whole quantity WHEN it is parsed THEN the same integer is returned."""
        assert Cart.parse_quantity(value) == value

    def test_accepts_zero_quantity_as_remove_signal(self):
        """GIVEN the quantity zero WHEN it is parsed THEN it is accepted so the caller can remove the line."""
        assert Cart.parse_quantity(0) == 0

    @pytest.mark.parametrize("value", [-1, 0.5, "2", True, False, None, 2.0])
    def test_refuses_negative_fraction_string_boolean_or_none_quantity(self, value):
        """GIVEN a negative, fractional, string, boolean, or missing quantity WHEN it is parsed THEN a validation error is raised."""
        with pytest.raises(DomainError) as excinfo:
            Cart.parse_quantity(value)
        assert _code(excinfo) == "validation_error"


class TestTotalCents:
    def test_two_lines_350_by_2_plus_275_by_1_is_975_cents(self):
        """GIVEN two cart lines priced 350 and 275 cents with quantities two and one WHEN the total is calculated THEN it is 975 integer cents."""
        vendor = make_vendor()
        item_a = make_item(vendor, "A", 350)
        item_b = make_item(vendor, "B", 275)
        total = Cart.total_cents([CartItem(menu_item=item_a, quantity=2), CartItem(menu_item=item_b, quantity=1)])
        assert total == 975

    def test_empty_cart_totals_zero(self):
        """GIVEN an empty cart WHEN the total is calculated THEN it is zero cents."""
        assert Cart.total_cents([]) == 0

    def test_total_never_uses_float_money(self):
        """GIVEN lines whose cent totals would drift under binary floats WHEN the total is calculated THEN the integer sum is exact."""
        vendor = make_vendor()
        item = make_item(vendor, "Repeat", 199)
        total = Cart.total_cents([CartItem(menu_item=item, quantity=3)])
        assert total == 597


class TestFingerprint:
    def test_fingerprint_stable_for_same_lines_regardless_of_order(self):
        """GIVEN the same cart lines in a different order WHEN the fingerprint is computed THEN the same digest is produced."""
        vendor = make_vendor()
        a = make_item(vendor, "A", 350)
        b = make_item(vendor, "B", 275)
        lines_ab = [(str(a.id), 2, "A", 350), (str(b.id), 1, "B", 275)]
        lines_ba = [(str(b.id), 1, "B", 275), (str(a.id), 2, "A", 350)]
        assert Cart.compute_fingerprint(str(vendor.id), lines_ab) == Cart.compute_fingerprint(str(vendor.id), lines_ba)
        assert len(Cart.compute_fingerprint(str(vendor.id), lines_ab)) == 64

    def test_fingerprint_changes_when_price_or_quantity_changes(self):
        """GIVEN a cart line whose current price or quantity changed WHEN the fingerprint is computed THEN a different digest is produced."""
        vendor = make_vendor()
        a = make_item(vendor, "A", 350)
        base = [(str(a.id), 2, "A", 350)]
        repriced = [(str(a.id), 2, "A", 400)]
        requantied = [(str(a.id), 3, "A", 350)]
        assert Cart.compute_fingerprint(str(vendor.id), base) != Cart.compute_fingerprint(str(vendor.id), repriced)
        assert Cart.compute_fingerprint(str(vendor.id), base) != Cart.compute_fingerprint(str(vendor.id), requantied)

    def test_fingerprint_changes_between_stalls(self):
        """GIVEN identical lines on two different stalls WHEN the fingerprints are computed THEN they differ."""
        s1, s2 = make_vendor("S1"), make_vendor("S2")
        item = make_item(s1, "A", 350)
        lines = [(str(item.id), 1, "A", 350)]
        assert Cart.compute_fingerprint(str(s1.id), lines) != Cart.compute_fingerprint(str(s2.id), lines)


class TestSetItemDecisions:
    def test_adds_available_item_to_open_stall_cart(self, no_persistence):
        """GIVEN a diner, an open stall and an available item WHEN the item is added with quantity two THEN the cart holds the line, the stall, and a 1300 cent total."""
        diner = make_diner()
        vendor = make_vendor(is_open=True)
        item = make_item(vendor, available=True)
        cart = make_cart(diner)
        result = cart.set_item(diner, item, 2)
        assert result.items[0].menu_item == item
        assert result.items[0].quantity == 2
        assert result.vendor == vendor
        assert Cart.total_cents(result.items) == 1300

    def test_increase_quantity_updates_existing_line(self):
        """GIVEN a cart that already holds two of an item WHEN the quantity is changed to three THEN one line of three exists and the total uses the new quantity."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor, price_cents=700)
        cart = make_cart(diner, vendor, [CartItem(menu_item=item, quantity=2)])
        result = cart.set_item(diner, item, 3)
        assert len(result.items) == 1
        assert result.items[0].quantity == 3
        assert Cart.total_cents(result.items) == 2100

    def test_zero_quantity_removes_the_line(self):
        """GIVEN a cart holding one line WHEN the quantity is set to zero THEN the line is removed and an empty total results."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor)
        cart = make_cart(diner, vendor, [CartItem(menu_item=item, quantity=2)])
        result = cart.set_item(diner, item, 0)
        assert result.items == []
        assert Cart.total_cents(result.items) == 0

    def test_removes_line_with_delete_control(self):
        """GIVEN a cart holding one line WHEN the delete control removes it THEN the cart no longer references the item."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor)
        cart = make_cart(diner, vendor, [CartItem(menu_item=item, quantity=1)])
        result = cart.remove_item(diner, str(item.id))
        assert result.items == []

    def test_refuses_sold_out_item_with_actionable_message(self):
        """GIVEN an item the vendor marked sold out WHEN the diner adds it THEN an item_unavailable conflict names the item and no line is saved."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor, "Pineapple Tart", available=False)
        cart = make_cart(diner)
        with pytest.raises(DomainError) as excinfo:
            cart.set_item(diner, item, 1)
        assert _code(excinfo) == "item_unavailable"
        assert "Pineapple Tart" in excinfo.value.message
        assert cart.items == []

    def test_refuses_soft_deleted_item(self):
        """GIVEN a menu item that was removed (soft-deleted) WHEN the diner adds it THEN an item_unavailable conflict is raised."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor, active=False)
        with pytest.raises(DomainError) as excinfo:
            make_cart(diner).set_item(diner, item, 1)
        assert _code(excinfo) == "item_unavailable"

    def test_refuses_closed_stall_with_actionable_message(self):
        """GIVEN a stall that is closed WHEN the diner adds one of its items THEN a stall_closed conflict names the stall and no line is saved."""
        diner = make_diner()
        vendor = make_vendor("Noodle Bar", is_open=False)
        item = make_item(vendor, "Hokkien Mee")
        cart = make_cart(diner)
        with pytest.raises(DomainError) as excinfo:
            cart.set_item(diner, item, 1)
        assert _code(excinfo) == "stall_closed"
        assert "Noodle Bar" in excinfo.value.message
        assert cart.items == []

    def test_refuses_second_stall_in_same_cart(self):
        """GIVEN a cart that already holds items from one stall WHEN the diner adds an item from another stall THEN a cross_stall_cart conflict keeps the original lines."""
        diner = make_diner()
        s1, s2 = make_vendor("S1"), make_vendor("S2")
        item1 = make_item(s1, "A", 350)
        item2 = make_item(s2, "B", 250)
        cart = make_cart(diner, s1, [CartItem(menu_item=item1, quantity=1)])
        with pytest.raises(DomainError) as excinfo:
            cart.set_item(diner, item2, 1)
        assert _code(excinfo) == "cross_stall_cart"
        assert len(cart.items) == 1

    def test_refuses_foreign_diners_cart(self):
        """GIVEN a cart that belongs to another diner WHEN a diner attempts to modify it THEN a forbidden refusal is raised and the cart is unchanged."""
        owner, stranger = make_diner("owner@skipq.test"), make_diner("stranger@skipq.test")
        vendor = make_vendor()
        item = make_item(vendor)
        cart = make_cart(owner)
        with pytest.raises(DomainError) as excinfo:
            cart.set_item(stranger, item, 1)
        assert _code(excinfo) == "forbidden"
        assert cart.items == []
        assert cart.diner == owner

    def test_refuses_invalid_quantity_without_saving_line(self):
        """GIVEN a valid cart WHEN an item is added with a fractional quantity THEN a validation error is raised and no line is added."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor)
        cart = make_cart(diner)
        with pytest.raises(DomainError) as excinfo:
            cart.set_item(diner, item, 1.5)
        assert _code(excinfo) == "validation_error"
        assert cart.items == []


class TestClearForCheckout:
    def test_clear_removes_all_lines_and_stall(self):
        """GIVEN a populated cart WHEN checkout clears it THEN no lines or stall reference remain, so a replay cannot re-charge stale contents."""
        diner = make_diner()
        vendor = make_vendor()
        item = make_item(vendor)
        cart = make_cart(diner, vendor, [CartItem(menu_item=item, quantity=2)])
        result = cart.clear_items()
        assert result.items == []
        assert result.vendor is None


@pytest.mark.parametrize('available,active,expected', [
    (True, True, True), (False, True, False),
    (True, False, False), (False, False, False),
])
def test_cart_read_exposes_only_published_available_lines(available, active, expected):
    """GIVEN a live or removed menu line WHEN cart JSON is read THEN an inactive item is unavailable before the diner acts."""
    diner = make_diner()
    vendor = make_vendor()
    item = make_item(vendor, available=available, active=active)
    cart = make_cart(diner, vendor, [CartItem(menu_item=item, quantity=1)])
    assert cart.to_dict()['items'][0]['is_available'] is expected


@pytest.mark.parametrize('is_open', [True, False])
def test_cart_read_exposes_current_stall_trading_state(is_open):
    """GIVEN a cart at an open or closed stall WHEN its JSON is read THEN the diner can see trading state before changing or paying."""
    diner = make_diner()
    vendor = make_vendor(is_open=is_open)
    cart = make_cart(diner, vendor, [CartItem(menu_item=make_item(vendor), quantity=1)])
    assert cart.to_dict()['stall']['id'] == str(vendor.id)
    assert cart.to_dict()['stall']['is_open'] is is_open


def test_empty_cart_has_no_stall_state():
    """GIVEN an empty cart WHEN JSON is read THEN no previous stall state is offered."""
    assert make_cart(make_diner()).to_dict()['stall'] is None
