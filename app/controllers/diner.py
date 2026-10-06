"""Diner persona routes: stall discovery, stall menus, and the persistent cart.

Every route resolves the actor from the verified Bearer token, enforces the
diner role, and then delegates to model-owned queries and rules; ids in the
URL or body are looked up through the model, never trusted as ownership.
"""

from flask import Blueprint, jsonify, request

from app.auth import current_user, require_role
from app.errors import NotFound, ValidationError
from app.models.cart import Cart
from app.models.common import same_document
from app.models.menu_item import MenuItem
from app.models.vendor import Vendor

diner_bp = Blueprint("diner", __name__, url_prefix="/api/diner")


@diner_bp.get("/stalls")
def open_stalls():
    """Open stalls only; closed stalls stay reachable through their direct menu link."""
    require_role(current_user(), "diner")
    return jsonify(items=[stall.to_dict() for stall in Vendor.list_open()])


@diner_bp.get("/stalls/<stall_id>/menu")
def stall_menu(stall_id):
    """One stall's published menu, including its current trading state."""
    require_role(current_user(), "diner")
    stall = Vendor.get(stall_id)
    if stall is None:
        raise NotFound("This stall does not exist. Pick one from the stall list.")
    items = [item.to_dict() for item in MenuItem.list_for_vendor(stall)]
    return jsonify(stall=stall.to_dict(), items=items)


@diner_bp.get("/cart")
def get_cart():
    """The diner's persistent cart with the server-computed total and freshness fingerprint."""
    diner = require_role(current_user(), "diner")
    cart = Cart.get_or_create_for_diner(diner)
    return jsonify(cart=cart.to_dict())


def _lookup_item(item_id):
    item = MenuItem.get(item_id) if isinstance(item_id, str) else None
    if item is None:
        raise NotFound("That menu item does not exist. It may have been removed.")
    return item


def _line_for(cart, item):
    return next((line for line in cart.items if same_document(line.menu_item, item)), None)


@diner_bp.post("/cart/items")
def add_cart_item():
    """Add a line: body ``{"item_id", "quantity"}`` with quantity at least 1."""
    diner = require_role(current_user(), "diner")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send a JSON body with item_id and quantity.")
    item_id = data.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        raise ValidationError("item_id must be the id of a menu item.")
    quantity = Cart.parse_quantity(data.get("quantity"))
    if quantity == 0:
        raise ValidationError("Quantity must be at least 1 to add a line.")
    item = _lookup_item(item_id)
    cart = Cart.get_or_create_for_diner(diner)
    updated = cart.set_item(diner, item, quantity)
    return jsonify(cart=updated.to_dict()), 201


@diner_bp.patch("/cart/items/<item_id>")
def update_cart_line(item_id):
    """Change a line's quantity; quantity 0 removes the line."""
    diner = require_role(current_user(), "diner")
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "quantity" not in data:
        raise ValidationError("Send a JSON body with the new quantity (0 removes the line).")
    quantity = Cart.parse_quantity(data["quantity"])
    item = _lookup_item(item_id)
    cart = Cart.get_or_create_for_diner(diner)
    if _line_for(cart, item) is None:
        raise NotFound("That item is not in your cart.")
    if quantity == 0:
        updated = cart.remove_item(diner, item_id)
    else:
        updated = cart.set_item(diner, item, quantity)
    return jsonify(cart=updated.to_dict())


@diner_bp.delete("/cart/items/<item_id>")
def delete_cart_line(item_id):
    """Remove a line from the cart."""
    diner = require_role(current_user(), "diner")
    item = _lookup_item(item_id)
    cart = Cart.get_or_create_for_diner(diner)
    if _line_for(cart, item) is None:
        raise NotFound("That item is not in your cart.")
    updated = cart.remove_item(diner, item_id)
    return jsonify(cart=updated.to_dict())
