"""Order routes: diner checkout and order reads; vendor queue and guarded transitions.

Checkout is the only route that creates orders: it hands the diner's live
cart to ``Order.place_from_cart``, which owns every allow/refuse rule
(stored-key replay, closed stall, stale price, simulated payment, the
database-enforced checkout-key uniqueness). The vendor routes expose the
stall's paid queue and move orders only through
``Order.transition_to``/``get_for_vendor``, so the lifecycle guard and
stall scope cannot be bypassed at the edge.
"""

from flask import Blueprint, jsonify, request

from app.auth import current_user, require_role
from app.errors import Forbidden, ValidationError
from app.models.cart import Cart
from app.models.common import utcnow
from app.models.order import Order

diner_orders_bp = Blueprint("diner_orders", __name__, url_prefix="/api/diner")
vendor_orders_bp = Blueprint("vendor_orders", __name__, url_prefix="/api/vendor")


# --- diner ------------------------------------------------------------------


@diner_orders_bp.post("/orders")
def create_order():
    """POST /api/diner/orders — pay for the current cart as one order.

    Body: ``{"payment_method", "simulate_success", "checkout_key",
    "expected_fingerprint"}``. 201 when a new order was stored, 200 when a
    matching replay returned the stored order; every refusal carries the
    stable domain code.
    """
    diner = require_role(current_user(), "diner")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError(
            "Send a JSON body with payment_method, simulate_success, checkout_key, and expected_fingerprint."
        )
    expected_fingerprint = data.get("expected_fingerprint")
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint.strip():
        raise ValidationError(
            "Send the cart's expected_fingerprint so a stale cart is not charged."
        )
    cart = Cart.get_or_create_for_diner(diner)
    order, created = Order.place_from_cart(
        diner,
        cart,
        data.get("payment_method"),
        data.get("simulate_success"),
        data.get("checkout_key"),
        expected_fingerprint,
        utcnow(),
    )
    return jsonify(order=order.to_dict()), (201 if created else 200)


@diner_orders_bp.get("/orders")
def list_orders():
    """GET /api/diner/orders?view=all|current|history — the diner's own orders."""
    diner = require_role(current_user(), "diner")
    view = request.args.get("view", "all")
    orders = Order.list_for_diner(diner, view)
    return jsonify(items=[order.to_dict() for order in orders])


@diner_orders_bp.get("/orders/<order_id>")
def read_order(order_id):
    """One of the diner's own orders, 404/403 for everything else."""
    diner = require_role(current_user(), "diner")
    order = Order.get_for_diner(diner, order_id)
    return jsonify(order=order.to_dict())


# --- vendor -----------------------------------------------------------------


def _actor_vendor():
    vendor_user = require_role(current_user(), "vendor")
    if vendor_user.vendor is None:
        raise Forbidden("This account is not linked to a stall.")
    return vendor_user


@vendor_orders_bp.get("/orders")
def list_vendor_orders():
    """The actor's stall paid queue, newest first, with allowed actions per order."""
    vendor_user = _actor_vendor()
    orders = Order.list_for_vendor(vendor_user.vendor)
    now = utcnow()
    return jsonify(
        items=[order.to_dict(actor=vendor_user, now=now) for order in orders]
    )


@vendor_orders_bp.get("/orders/<order_id>")
def read_vendor_order(order_id):
    """One of the actor's stall orders, 404/403 for everything else."""
    vendor_user = _actor_vendor()
    order = Order.get_for_vendor(vendor_user, order_id)
    return jsonify(order=order.to_dict(actor=vendor_user, now=utcnow()))


@vendor_orders_bp.patch("/orders/<order_id>/status")
def transition_vendor_order(order_id):
    """PATCH body ``{"status": target}`` — one guarded lifecycle move.

    The target is validated and persisted by ``Order.transition_to`` with
    the expected-current-state guard; terminal orders and out-of-scope
    actors are refused without touching the record.
    """
    vendor_user = _actor_vendor()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send a JSON object with the target status.")
    target = data.get("status")
    if not isinstance(target, str) or not target.strip():
        raise ValidationError("Send the target order status in the JSON body.")
    order = Order.get_for_vendor(vendor_user, order_id)
    updated = order.transition_to(vendor_user, target, utcnow())
    return jsonify(order=updated.to_dict(actor=vendor_user, now=utcnow()))
