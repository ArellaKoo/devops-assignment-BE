"""Vendor persona routes: own-stall trading state and menu management.

The actor always comes from the verified Bearer token; the stall is the
actor's own vendor reference, and every menu operation re-checks the
stall relationship inside the model.
"""

from flask import Blueprint, jsonify, request

from app.auth import current_user, require_role
from app.errors import Forbidden, NotFound, ValidationError
from app.models.menu_item import MenuItem
from app.models.vendor import Vendor

vendor_bp = Blueprint("vendor", __name__, url_prefix="/api/vendor")


def _actor_stall(actor) -> Vendor:
    if actor.vendor is None:
        raise Forbidden("This account is not linked to a stall.")
    return actor.vendor


@vendor_bp.get("/stall")
def get_stall():
    """The vendor's stall and its current trading state."""
    actor = require_role(current_user(), "vendor")
    return jsonify(stall=_actor_stall(actor).to_dict())


@vendor_bp.patch("/stall")
def patch_stall():
    """Open or close the stall: body ``{"is_open": true|false}``."""
    actor = require_role(current_user(), "vendor")
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "is_open" not in data:
        raise ValidationError("Send a JSON body with is_open set to true or false.")
    updated = _actor_stall(actor).set_open_by_actor(actor, data["is_open"])
    return jsonify(stall=updated.to_dict())


@vendor_bp.get("/menu")
def menu():
    """The stall's menu with the stall's trading state for the open/close control."""
    actor = require_role(current_user(), "vendor")
    stall = _actor_stall(actor)
    items = [item.to_dict() for item in MenuItem.list_for_vendor(stall)]
    return jsonify(stall=stall.to_dict(), items=items)


@vendor_bp.post("/menu")
def create_item():
    """Create a menu item on the vendor's own stall."""
    actor = require_role(current_user(), "vendor")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send the item details as a JSON object.")
    item = MenuItem.create_for_vendor(actor, data)
    return jsonify(item=item.to_dict()), 201


@vendor_bp.patch("/menu/<item_id>")
def update_item(item_id):
    """Edit name/description/image/price/availability on own-stall items."""
    actor = require_role(current_user(), "vendor")
    item = MenuItem.get(item_id)
    if item is None:
        raise NotFound("That menu item does not exist. It may have been removed.")
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        raise ValidationError(
            "Send at least one field to change: name, description, image_url, price, or is_available."
        )
    updated = item.update_by_actor(actor, data)
    return jsonify(item=updated.to_dict())


@vendor_bp.delete("/menu/<item_id>")
def delete_item(item_id):
    """Soft-delete an own-stall item so historical order snapshots keep working."""
    actor = require_role(current_user(), "vendor")
    item = MenuItem.get(item_id)
    if item is None:
        raise NotFound("That menu item does not exist. It may have been removed.")
    updated = item.mark_inactive_by_actor(actor)
    return jsonify(item=updated.to_dict())
