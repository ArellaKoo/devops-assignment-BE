"""Offline unit tests for the diner and vendor API routes (Task 4).

The controllers run for real through the Flask test client with signed
tokens; only the persistence seams (``find_by_id``, record lookups,
``save``) are supplied by the tests, so the shared auth gate, role gate,
serialisation and the model-owned scope checks all execute. The socket
sentinel fails the suite on any accidental database connection.
"""

from bson import ObjectId

import pytest

from app.auth import issue_token
from app.models.cart import Cart, CartItem
from app.models.common import utcnow
from app.models.menu_item import MenuItem
from app.models.user import User
from app.models.vendor import Vendor

_KNOWN = []


def make_stall(name="Charcoal Grill", is_open=True):
    return Vendor(id=ObjectId(), name=name, is_open=is_open, created_at=utcnow())


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
        created_at=utcnow(),
        updated_at=utcnow(),
    )


def make_diner(email="diner.one@skipq.test"):
    return User(id=ObjectId(), email=email, password_hash="unused-hash", role="diner")


def make_vendor_user(email="vendor.one@skipq.test", stall=None):
    return User(
        id=ObjectId(),
        email=email,
        password_hash="unused-hash",
        role="vendor",
        vendor=stall,
    )


def make_cart(diner, vendor=None, lines=None):
    return Cart(
        id=ObjectId(),
        diner=diner,
        vendor=vendor,
        items=lines or [],
        created_at=utcnow(),
        updated_at=utcnow(),
    )


def item_lookup(monkeypatch, extra=()):
    """Patch MenuItem.get over every known item; tests add their own records."""
    monkeypatch.setattr(
        MenuItem,
        "get",
        staticmethod(lambda iid: next((i for i in _KNOWN + list(extra) if str(i.id) == iid), None)),
    )


@pytest.fixture
def dine(monkeypatch):
    """A diner and a vendor on an open stall, with their record access supplied."""
    stall = make_stall()
    closed = make_stall("Noodle Bar", is_open=False)
    diner = make_diner()
    vendor_user = make_vendor_user(stall=stall)
    users = {str(user.id): user for user in (diner, vendor_user)}
    monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))
    items = [
        make_item(stall, "Charcoal Chicken Rice", 650),
        make_item(stall, "Mango Sago", 250),
    ]
    foreign_item = make_item(closed, "Hokkien Mee", 550)
    _KNOWN[:] = items + [foreign_item]
    saved = {"vendor": [], "item": [], "cart": []}
    monkeypatch.setattr(Vendor, "list_open", staticmethod(lambda: [stall]))
    monkeypatch.setattr(
        Vendor,
        "get",
        staticmethod(lambda vid: next((s for s in (stall, closed) if str(s.id) == vid), None)),
    )
    monkeypatch.setattr(
        Vendor, "save", lambda self, *a, **k: (saved["vendor"].append(self), self)[1]
    )
    monkeypatch.setattr(
        MenuItem,
        "list_for_vendor",
        staticmethod(
            lambda vendor: sorted((i for i in _KNOWN if i.vendor is vendor), key=lambda i: i.name)
        ),
    )
    item_lookup(monkeypatch)
    monkeypatch.setattr(
        MenuItem, "save", lambda self, *a, **k: (saved["item"].append(self), self)[1]
    )
    return {
        "stall": stall,
        "closed": closed,
        "diner": diner,
        "vendor_user": vendor_user,
        "items": items,
        "foreign_item": foreign_item,
        "saved": saved,
    }


@pytest.fixture
def carts(monkeypatch, dine):
    """Supply the diner's cart and record its saves."""
    cart = make_cart(
        dine["diner"],
        vendor=dine["stall"],
        lines=[CartItem(menu_item=dine["items"][0], quantity=2)],
    )
    monkeypatch.setattr(Cart, "get_or_create_for_diner", staticmethod(lambda diner: cart))
    monkeypatch.setattr(
        Cart, "save", lambda self, *a, **k: (dine["saved"]["cart"].append(self), self)[1]
    )
    return cart


def bearer(app, user):
    return {"Authorization": "Bearer " + issue_token(user, app.config["TOKEN_SECRET"])}


def code(response):
    return response.get_json()["error"]["code"]


class TestPersonaGates:
    def test_diner_route_without_token_returns_401(self, app):
        """GIVEN no Authorization header WHEN a diner route is called THEN 401 authentication_required is returned."""
        response = app.test_client().get("/api/diner/stalls")
        assert response.status_code == 401
        assert code(response) == "authentication_required"

    def test_garbage_token_on_protected_route_returns_401(self, app, dine):
        """GIVEN a Bearer token that does not verify WHEN a protected route is called THEN 401 authentication_required is returned."""
        response = app.test_client().get(
            "/api/diner/stalls", headers={"Authorization": "Bearer garbage.token"}
        )
        assert response.status_code == 401
        assert code(response) == "authentication_required"

    def test_vendor_token_on_diner_route_returns_403(self, app, dine):
        """GIVEN a valid vendor token WHEN a diner route is called THEN 403 forbidden names the persona the route needs."""
        response = app.test_client().get("/api/diner/stalls", headers=bearer(app, dine["vendor_user"]))
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert "diner" in response.get_json()["error"]["message"]

    def test_diner_token_on_vendor_route_returns_403(self, app, dine):
        """GIVEN a valid diner token WHEN a vendor route is called THEN 403 forbidden is returned before any stall data is read."""
        response = app.test_client().get("/api/vendor/stall", headers=bearer(app, dine["diner"]))
        assert response.status_code == 403
        assert code(response) == "forbidden"


class TestDinerStalls:
    def test_open_stall_discovery_lists_only_open_stalls(self, app, dine):
        """GIVEN one open and one closed stall WHEN the diner lists stalls THEN only the open stall appears, with id, name and open state."""
        response = app.test_client().get("/api/diner/stalls", headers=bearer(app, dine["diner"]))
        assert response.status_code == 200
        items = response.get_json()["items"]
        assert [s["name"] for s in items] == ["Charcoal Grill"]
        assert items[0]["is_open"] is True
        assert items[0]["id"] == str(dine["stall"].id)

    def test_menu_for_malformed_stall_id_returns_404(self, app, dine, monkeypatch):
        """GIVEN a stall id that is not a valid id WHEN the diner requests its menu THEN 404 not_found is returned, not a 500."""
        monkeypatch.setattr(Vendor, "get", staticmethod(lambda vid: None))
        response = app.test_client().get(
            "/api/diner/stalls/not-an-objectid/menu", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_menu_for_unknown_stall_id_returns_404(self, app, dine, monkeypatch):
        """GIVEN a well-formed but unknown stall id WHEN the diner requests its menu THEN 404 not_found is returned."""
        monkeypatch.setattr(Vendor, "get", staticmethod(lambda vid: None))
        response = app.test_client().get(
            "/api/diner/stalls/aaaaaaaaaaaaaaaaaaaaaaaa/menu", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 404

    def test_direct_link_to_closed_still_serves_its_menu(self, app, dine):
        """GIVEN a closed stall WHEN the diner opens its menu through the direct link THEN 200 carries the closed state and the stall's published items."""
        closed = dine["closed"]
        response = app.test_client().get(
            f"/api/diner/stalls/{closed.id}/menu", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["stall"]["is_open"] is False
        assert [i["name"] for i in body["items"]] == ["Hokkien Mee"]

    def test_menu_lists_only_active_items_with_cents_and_availability(self, app, dine, monkeypatch):
        """GIVEN a stall whose menu hides a soft-deleted item WHEN the diner requests the menu THEN only the active item appears, priced in integer cents with its availability flag."""
        monkeypatch.setattr(
            MenuItem, "list_for_vendor", staticmethod(lambda vendor: [dine["items"][0]])
        )
        response = app.test_client().get(
            f"/api/diner/stalls/{dine['stall'].id}/menu", headers=bearer(app, dine["diner"])
        )
        body = response.get_json()
        assert [i["id"] for i in body["items"]] == [str(dine["items"][0].id)]
        assert body["items"][0]["price_cents"] == 650
        assert body["items"][0]["is_available"] is True
        assert body["stall"]["is_open"] is True


class TestDinerCart:
    def test_cart_for_diner_without_cart_returns_empty_cart(self, app, dine, carts, monkeypatch):
        """GIVEN a diner with no stored cart WHEN they read their cart THEN 200 carries an empty cart with zero total and no fingerprint."""
        empty = make_cart(dine["diner"])
        monkeypatch.setattr(Cart, "get_or_create_for_diner", staticmethod(lambda diner: empty))
        response = app.test_client().get("/api/diner/cart", headers=bearer(app, dine["diner"]))
        assert response.status_code == 200
        cart = response.get_json()["cart"]
        assert cart["items"] == []
        assert cart["total_cents"] == 0
        assert cart["fingerprint"] is None
        assert cart["vendor"] is None

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"item_id": None, "quantity": 1},
            {"quantity": 1},
            {"item_id": "abc", "quantity": "two"},
        ],
    )
    def test_add_item_with_malformed_body_returns_400(self, app, dine, carts, payload):
        """GIVEN a cart add without a string item id or a whole-number quantity WHEN it is POSTed THEN 400 validation_error says what to fix."""
        response = app.test_client().post(
            "/api/diner/cart/items", json=payload, headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_add_item_with_zero_quantity_returns_400(self, app, dine, carts):
        """GIVEN a cart add with quantity zero WHEN it is POSTed THEN 400 explains that adding needs at least one."""
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": str(dine["items"][0].id), "quantity": 0},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_add_unknown_item_returns_404(self, app, dine, carts, monkeypatch):
        """GIVEN an item id that matches no menu record WHEN a cart line is added THEN 404 not_found is returned and the cart is untouched."""
        monkeypatch.setattr(MenuItem, "get", staticmethod(lambda iid: None))
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": "aaaaaaaaaaaaaaaaaaaaaaaa", "quantity": 1},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_add_available_item_returns_201_with_server_total(self, app, dine, carts):
        """GIVEN an open stall and an available item WHEN the diner adds one of it to a cart holding two lines of 650 cents THEN 201 returns the cart with the new line and the server-computed total of 1550 cents."""
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": str(dine["items"][1].id), "quantity": 1},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 201
        cart = response.get_json()["cart"]
        assert cart["total_cents"] == 2 * 650 + 250
        assert cart["vendor"] == str(dine["stall"].id)
        assert {line["item_id"] for line in cart["items"]} == {
            str(dine["items"][0].id),
            str(dine["items"][1].id),
        }
        assert cart["fingerprint"] is not None

    def test_add_sold_out_item_returns_409(self, app, dine, carts, monkeypatch):
        """GIVEN a sold-out item WHEN the diner tries to add it to the cart THEN 409 item_unavailable names the item and the cart is unchanged."""
        sold_out = make_item(dine["stall"], "Pineapple Tart", 400, available=False)
        item_lookup(monkeypatch, extra=[sold_out])
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": str(sold_out.id), "quantity": 1},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 409
        assert code(response) == "item_unavailable"

    def test_add_item_from_closed_stall_returns_409(self, app, dine, carts):
        """GIVEN an item on a closed stall WHEN the diner tries to add it THEN 409 stall_closed is returned with the stall's name."""
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": str(dine["foreign_item"].id), "quantity": 1},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 409
        assert code(response) == "stall_closed"

    def test_add_second_stall_item_returns_409_cross_stall(self, app, dine, carts, monkeypatch):
        """GIVEN a cart that already holds a line from one stall WHEN a line from another open stall is added THEN 409 cross_stall_cart says the cart is one-stall and to clear it."""
        other_stall = make_stall("Dim Sum Corner")
        other_item = make_item(other_stall, "Har Gow", 350)
        item_lookup(monkeypatch, extra=[other_item])
        response = app.test_client().post(
            "/api/diner/cart/items",
            json={"item_id": str(other_item.id), "quantity": 1},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 409
        assert code(response) == "cross_stall_cart"

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"quantity": "3"},
            {"quantity": -2},
        ],
    )
    def test_patch_line_with_malformed_quantity_returns_400(self, app, dine, carts, payload):
        """GIVEN a line update with a missing, string, or negative quantity WHEN it is PATCHed THEN 400 validation_error is returned."""
        response = app.test_client().patch(
            f"/api/diner/cart/items/{dine['items'][0].id}",
            json=payload,
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"

    def test_patch_line_not_in_cart_returns_404(self, app, dine, carts):
        """GIVEN a cart without a line for an item WHEN the diner patches its quantity THEN 404 not_found says the item is not in the cart."""
        response = app.test_client().patch(
            f"/api/diner/cart/items/{dine['items'][1].id}",
            json={"quantity": 2},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_patch_line_quantity_updates_server_total(self, app, dine, carts):
        """GIVEN a cart with two lines of 650 cents WHEN the diner changes the quantity to three THEN 200 returns the updated cart totalling 1950 cents."""
        response = app.test_client().patch(
            f"/api/diner/cart/items/{dine['items'][0].id}",
            json={"quantity": 3},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 200
        assert response.get_json()["cart"]["total_cents"] == 3 * 650

    def test_patch_line_to_zero_removes_it(self, app, dine, carts):
        """GIVEN a single-line cart WHEN the diner patches the quantity to zero THEN 200 returns an empty cart with no vendor and no fingerprint."""
        response = app.test_client().patch(
            f"/api/diner/cart/items/{dine['items'][0].id}",
            json={"quantity": 0},
            headers=bearer(app, dine["diner"]),
        )
        assert response.status_code == 200
        cart = response.get_json()["cart"]
        assert cart["items"] == []
        assert cart["vendor"] is None
        assert cart["fingerprint"] is None

    def test_delete_line_removes_it(self, app, dine, carts):
        """GIVEN a single-line cart WHEN the diner deletes the line THEN 200 returns the empty cart."""
        response = app.test_client().delete(
            f"/api/diner/cart/items/{dine['items'][0].id}", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 200
        assert response.get_json()["cart"]["items"] == []

    def test_delete_line_not_in_cart_returns_404(self, app, dine, carts):
        """GIVEN a cart without a line for an item WHEN the diner deletes it THEN 404 not_found is returned."""
        response = app.test_client().delete(
            f"/api/diner/cart/items/{dine['items'][1].id}", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_malformed_line_id_returns_404_not_500(self, app, dine, carts):
        """GIVEN a cart line id that is not a valid id WHEN the diner deletes it THEN 404 not_found is returned instead of a 500."""
        response = app.test_client().delete(
            "/api/diner/cart/items/not-an-objectid", headers=bearer(app, dine["diner"])
        )
        assert response.status_code == 404
        assert code(response) == "not_found"


class TestVendorStall:
    def test_get_own_stall(self, app, dine):
        """GIVEN a vendor account WHEN they read their stall THEN 200 carries the stall's name and trading state."""
        response = app.test_client().get("/api/vendor/stall", headers=bearer(app, dine["vendor_user"]))
        assert response.status_code == 200
        body = response.get_json()["stall"]
        assert body["name"] == "Charcoal Grill"
        assert body["is_open"] is True

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"is_open": "yes"},
            {"is_open": 1},
        ],
    )
    def test_patch_stall_with_non_boolean_returns_400(self, app, dine, payload):
        """GIVEN a trading update that is missing is_open or not true/false WHEN it is PATCHed THEN 400 validation_error is returned and the stall state is unchanged."""
        before = dine["stall"].is_open
        response = app.test_client().patch(
            "/api/vendor/stall", json=payload, headers=bearer(app, dine["vendor_user"])
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"
        assert dine["stall"].is_open is before
        assert dine["saved"]["vendor"] == []

    def test_close_own_stall(self, app, dine):
        """GIVEN an open stall WHEN its vendor closes it THEN 200 returns the closed state and the change is persisted."""
        response = app.test_client().patch(
            "/api/vendor/stall", json={"is_open": False}, headers=bearer(app, dine["vendor_user"])
        )
        assert response.status_code == 200
        assert response.get_json()["stall"]["is_open"] is False
        assert dine["stall"].is_open is False
        assert len(dine["saved"]["vendor"]) == 1

    def test_vendor_toggle_only_affects_own_stall(self, app, dine, monkeypatch):
        """GIVEN a second vendor account on a different stall WHEN it toggles its trading state THEN the toggle applies only to its own stall and the first stall is untouched."""
        other_stall = make_stall("Noodle Bar")
        other_user = make_vendor_user("vendor.two@skipq.test", stall=other_stall)
        users = {str(u.id): u for u in (dine["diner"], dine["vendor_user"], other_user)}
        monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))
        response = app.test_client().patch(
            "/api/vendor/stall", json={"is_open": False}, headers=bearer(app, other_user)
        )
        assert response.status_code == 200
        assert response.get_json()["stall"]["name"] == "Noodle Bar"
        assert other_stall.is_open is False
        assert dine["stall"].is_open is True
        assert all(not saved is dine["stall"] for saved in dine["saved"]["vendor"])


class TestVendorMenu:
    def test_get_own_menu_includes_stall_state(self, app, dine):
        """GIVEN a vendor with two active items WHEN they list their menu THEN 200 returns the stall state plus both items in name order with cents prices."""
        response = app.test_client().get("/api/vendor/menu", headers=bearer(app, dine["vendor_user"]))
        assert response.status_code == 200
        body = response.get_json()
        assert body["stall"]["id"] == str(dine["stall"].id)
        assert [i["name"] for i in body["items"]] == ["Charcoal Chicken Rice", "Mango Sago"]

    @pytest.mark.parametrize(
        "values",
        [
            {"price": "6.50"},  # missing name
            {"name": "Rice", "image_url": "http://x/a.png"},  # missing price
            {"name": "Rice", "price": "6.50"},  # missing image
            {"name": "Rice", "price": "0"},  # not above zero
            {"name": "Rice", "price": "9999.00"},  # not below 9999
            {"name": "Rice", "price": "6.500"},  # three decimals
            {"name": "Rice", "price": "6.50", "image_url": "http://x/a.gif"},  # not an image
            {"name": "x" * 81, "price": "6.50", "image_url": "http://x/a.png"},  # too long
        ],
    )
    def test_create_item_with_invalid_values_returns_400_and_saves_nothing(self, app, dine, values):
        """GIVEN a new menu item payload that breaks a rule WHEN the vendor POSTs it THEN 400 validation_error names the rule and no item is saved."""
        response = app.test_client().post(
            "/api/vendor/menu", json=values, headers=bearer(app, dine["vendor_user"])
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"
        assert dine["saved"]["item"] == []

    def test_create_valid_item_returns_201_with_cleaned_fields(self, app, dine):
        """GIVEN a complete valid payload WHEN the vendor creates the item THEN 201 returns the stored item with the price converted to 650 cents."""
        response = app.test_client().post(
            "/api/vendor/menu",
            json={
                "name": "  Special Kaya Toast ",
                "description": "Toasted with kaya.",
                "price": "6.50",
                "image_url": "http://127.0.0.1:5001/static/images/skipq-m4.png",
                "is_available": False,
            },
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 201
        item = response.get_json()["item"]
        assert item["name"] == "Special Kaya Toast"
        assert item["price_cents"] == 650
        assert item["is_available"] is False
        assert "vendor" not in item
        assert len(dine["saved"]["item"]) == 1

    def test_vendor_without_stall_cannot_create_item(self, app, dine, monkeypatch):
        """GIVEN a vendor-role account with no stall link WHEN they create a menu item THEN 403 forbidden is returned and nothing is saved."""
        homeless = make_vendor_user("vendor.none@skipq.test", stall=None)
        users = {str(u.id): u for u in (dine["diner"], dine["vendor_user"], homeless)}
        monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))
        response = app.test_client().post(
            "/api/vendor/menu",
            json={"name": "Rice", "price": "6.50", "image_url": "http://x/a.png"},
            headers=bearer(app, homeless),
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert dine["saved"]["item"] == []

    def test_patch_malformed_item_id_returns_404(self, app, dine):
        """GIVEN an item id that is not a valid id WHEN the vendor patches it THEN 404 not_found is returned, not a 500."""
        response = app.test_client().patch(
            "/api/vendor/menu/not-an-objectid",
            json={"name": "New name"},
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 404
        assert code(response) == "not_found"

    def test_patch_unknown_item_returns_404(self, app, dine, monkeypatch):
        """GIVEN a well-formed id that matches no item WHEN the vendor patches it THEN 404 not_found is returned."""
        monkeypatch.setattr(MenuItem, "get", staticmethod(lambda iid: None))
        response = app.test_client().patch(
            "/api/vendor/menu/aaaaaaaaaaaaaaaaaaaaaaaa",
            json={"name": "New name"},
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 404

    def test_foreign_vendor_cannot_patch_item(self, app, dine, monkeypatch):
        """GIVEN an item on another vendor's stall WHEN they PATCH its fields THEN 403 forbidden is returned and the saved item is unchanged."""
        target = dine["items"][0]
        other_stall = make_stall("Noodle Bar")
        other_user = make_vendor_user("vendor.two@skipq.test", stall=other_stall)
        users = {str(u.id): u for u in (dine["diner"], dine["vendor_user"], other_user)}
        monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))
        response = app.test_client().patch(
            f"/api/vendor/menu/{target.id}",
            json={"price": "1.00"},
            headers=bearer(app, other_user),
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert target.price_cents == 650
        assert dine["saved"]["item"] == []

    def test_patch_own_item_price_updates_cents(self, app, dine):
        """GIVEN the vendor's own item priced at 650 cents WHEN they patch the price to 7.25 THEN 200 returns the item at 725 cents."""
        response = app.test_client().patch(
            f"/api/vendor/menu/{dine['items'][0].id}",
            json={"price": "7.25"},
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 200
        assert response.get_json()["item"]["price_cents"] == 725
        assert len(dine["saved"]["item"]) == 1

    def test_patch_own_item_to_sold_out(self, app, dine):
        """GIVEN an available item on the vendor's stall WHEN they set is_available to false THEN 200 returns the sold-out state."""
        response = app.test_client().patch(
            f"/api/vendor/menu/{dine['items'][0].id}",
            json={"is_available": False},
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 200
        assert response.get_json()["item"]["is_available"] is False

    def test_patch_item_with_invalid_price_keeps_saved_values(self, app, dine):
        """GIVEN a valid saved item WHEN the vendor patches its price to an invalid string THEN 400 is returned and the previous price is kept."""
        response = app.test_client().patch(
            f"/api/vendor/menu/{dine['items'][0].id}",
            json={"price": "free"},
            headers=bearer(app, dine["vendor_user"]),
        )
        assert response.status_code == 400
        assert code(response) == "validation_error"
        assert dine["items"][0].price_cents == 650

    def test_delete_item_soft_deletes(self, app, dine):
        """GIVEN a vendor's item WHEN they remove it THEN 200 marks it inactive so historical snapshots keep working."""
        response = app.test_client().delete(
            f"/api/vendor/menu/{dine['items'][0].id}", headers=bearer(app, dine["vendor_user"])
        )
        assert response.status_code == 200
        assert response.get_json()["item"]["is_active"] is False
        assert dine["items"][0].is_active is False

    def test_delete_foreign_item_returns_403(self, app, dine, monkeypatch):
        """GIVEN an item on another stall WHEN its foreign vendor deletes it THEN 403 forbidden is returned and the item stays active."""
        target = dine["items"][0]
        other_stall = make_stall("Noodle Bar")
        other_user = make_vendor_user("vendor.two@skipq.test", stall=other_stall)
        users = {str(u.id): u for u in (dine["diner"], dine["vendor_user"], other_user)}
        monkeypatch.setattr(User, "find_by_id", staticmethod(lambda uid: users.get(uid)))
        response = app.test_client().delete(
            f"/api/vendor/menu/{target.id}", headers=bearer(app, other_user)
        )
        assert response.status_code == 403
        assert code(response) == "forbidden"
        assert target.is_active is True
