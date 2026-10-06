"""Paid order with the guarded SkipQ fulfillment lifecycle.

Canonical states: ``Pending → Preparing → Ready → Collected``, with
``Pending → Cancelled`` (simulated refund) and ``Ready → NoShow`` (only at
or after 30 minutes from ``ready_at``). Terminal states refuse further
transitions. The guard lives here, not in routes: every transition goes
through :meth:`Order.transition_to`, which re-checks the actor, the
current state, and the no-show boundary, then persists with an
expected-current-state update.

Purchase lines embed name and unit-price snapshots so historical orders
survive later menu edits and removals. A unique ``(diner, checkout_key)``
pair prevents duplicate paid orders; a matching replay returns the stored
order, a conflicting reuse is refused.
"""

import logging
import uuid
from datetime import timedelta

from bson.errors import InvalidId
from mongoengine import (
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)
from mongoengine import ValidationError as MongoValidationError
from mongoengine.errors import NotUniqueError
from pymongo.errors import DuplicateKeyError

from app.errors import (
    CartEmpty,
    CheckoutKeyConflict,
    Forbidden,
    InvalidTransition,
    ItemUnavailable,
    NoShowTooEarly,
    NotFound,
    PaymentFailed,
    PriceChanged,
    StallClosed,
    ValidationError,
)
from app.models.cart import Cart
from app.models.common import as_utc, iso_utc, same_document, utcnow
from app.models.payment import PAYMENT_METHODS, Payment

logger = logging.getLogger("skipq.orders")

NO_SHOW_LIMIT = timedelta(minutes=30)

CURRENT_STATUSES = ("Pending", "Preparing", "Ready")
TERMINAL_STATUSES = ("Collected", "Cancelled", "NoShow")
STATUS_CHOICES = CURRENT_STATUSES + TERMINAL_STATUSES

ALLOWED_EDGES = {
    ("Pending", "Preparing"),
    ("Pending", "Cancelled"),
    ("Preparing", "Ready"),
    ("Ready", "Collected"),
    ("Ready", "NoShow"),
}


def new_queue_number() -> str:
    """``Q-`` plus full UUID hex; uniqueness is enforced by the database."""
    return "Q-" + uuid.uuid4().hex


class OrderItem(EmbeddedDocument):
    menu_item = ReferenceField("MenuItem")
    name_snapshot = StringField(required=True)
    price_cents_snapshot = IntField(required=True, min_value=1)
    quantity = IntField(required=True, min_value=1)

    def to_dict(self) -> dict:
        return {
            "item_id": str(self.menu_item.id) if self.menu_item is not None else None,
            "name": self.name_snapshot,
            "price_cents": int(self.price_cents_snapshot),
            "quantity": int(self.quantity),
        }


class Order(Document):
    meta = {
        "collection": "orders",
        "indexes": [
            "diner",
            "vendor",
            "created_at",
        ],
    }

    diner = ReferenceField("User", required=True)
    vendor = ReferenceField("Vendor", required=True)
    items = ListField(EmbeddedDocumentField(OrderItem), required=True)
    payment = EmbeddedDocumentField(Payment, required=True)
    total_cents = IntField(required=True, min_value=1)
    queue_number = StringField(required=True, unique=True)
    status = StringField(required=True, default="Pending", choices=STATUS_CHOICES)
    created_at = DateTimeField(default=utcnow)
    ready_at = DateTimeField(default=None)
    # unique_with makes (checkout_key, diner) a database-backed unique
    # composite index: the duplicate-checkout refusal is enforced by
    # MongoDB, not only by the application.
    checkout_key = StringField(required=True, unique_with=["diner"])
    checkout_fingerprint = StringField(required=True)
    seed_key = StringField(default=None)

    # --- lifecycle guard -----------------------------------------------------

    def can_transition(self, target, actor, now):
        """Pure decision: ``(allowed, error)`` for moving to ``target``.

        Checks, in order: actor role and stall scope, terminal-state
        refusal, allowed-edge membership, and the 30-minute no-show
        boundary. No persistence happens here.
        """
        if target not in STATUS_CHOICES:
            return False, InvalidTransition(
                f"Unknown order status '{target}'. Allowed: {', '.join(STATUS_CHOICES)}."
            )
        if actor is None or actor.role != "vendor":
            return False, Forbidden("Only vendors can update order status.")
        if not (
            self.vendor is not None
            and actor.vendor is not None
            and same_document(actor.vendor, self.vendor)
        ):
            return False, Forbidden("You can only manage orders for your own stall.")
        current = self.status
        if current in TERMINAL_STATUSES:
            return False, InvalidTransition(
                f"This order is {current}; it is final and cannot be changed."
            )
        if (current, target) not in ALLOWED_EDGES:
            return False, InvalidTransition(
                f"This order is {current} and cannot move to {target}."
            )
        if target == "NoShow":
            ready_at = as_utc(self.ready_at)
            if ready_at is None or as_utc(now) < ready_at + NO_SHOW_LIMIT:
                return False, NoShowTooEarly(
                    "No-show can only be marked at least 30 minutes after the order was ready."
                )
        return True, None

    def transition_to(self, actor, target, now) -> "Order":
        """Validate and persist one guarded transition.

        Persistence uses an expected-current-state update so two vendors
        racing on one order cannot both apply a transition.
        """
        allowed, error = self.can_transition(target, actor, now)
        if error is not None:
            raise error
        now = as_utc(now)

        updates = {"status": target}
        if target == "Ready":
            updates["ready_at"] = now
        if target == "Cancelled":
            updates["payment.status"] = "Refunded"
            updates["payment.refunded_at"] = now

        kwargs = {f"set__{key.replace('.', '__')}": value for key, value in updates.items()}
        modified = type(self).objects(id=self.id, status=self.status).update(**kwargs)
        if not modified:
            raise InvalidTransition(
                "This order already changed; reload it and try again."
            )

        self.status = target
        if target == "Ready":
            self.ready_at = now
        if target == "Cancelled":
            self.payment.status = "Refunded"
            self.payment.refunded_at = now
        return self

    def allowed_actions(self, actor, now) -> list[str]:
        """Statuses this actor may move this order to right now."""
        actions = []
        for target in ("Preparing", "Cancelled", "Ready", "Collected", "NoShow"):
            allowed, _error = self.can_transition(target, actor, now)
            if allowed:
                actions.append(target)
        return actions

    # --- checkout ------------------------------------------------------------

    @classmethod
    def find_by_checkout_key(cls, diner, checkout_key):
        """Persistence seam: the stored order for one diner's checkout key."""
        return cls.objects(diner=diner, checkout_key=checkout_key).first()

    @classmethod
    def place_from_cart(
        cls,
        diner,
        cart,
        payment_method,
        simulate_success,
        checkout_key,
        expected_fingerprint,
        now,
    ) -> tuple["Order", bool]:
        """Turn the diner's current cart into one paid order, or refuse.

        Returns ``(order, created)``; ``created`` is False when a matching
        replay returned the stored order. The stored-key lookup happens
        before cart validation so a retry still works after the cart was
        cleared. Every cart check re-reads current records.
        """
        now = as_utc(now)
        if payment_method not in PAYMENT_METHODS:
            raise ValidationError(
                f"Payment method must be one of: {', '.join(PAYMENT_METHODS)}."
            )
        if not isinstance(checkout_key, str) or not checkout_key.strip():
            raise ValidationError("A checkout key is required.")
        if not isinstance(simulate_success, bool):
            raise ValidationError("Payment result must be true or false.")

        existing = cls.find_by_checkout_key(diner, checkout_key)
        if existing is not None:
            if existing.checkout_fingerprint == expected_fingerprint:
                return existing, False
            raise CheckoutKeyConflict(
                "This checkout was already used with different cart contents. "
                "Review your cart and start checkout again."
            )

        if cart is None or not cart.items:
            raise CartEmpty("Your cart is empty. Add an item before checking out.")
        stall = cart.vendor
        if stall is None or not stall.is_open:
            stall_name = stall.name if stall is not None else "This stall"
            raise StallClosed(
                f"{stall_name} is currently closed. Try again once the stall opens."
            )

        lines = []
        total = 0
        for line in cart.items:
            item = line.menu_item
            if item is None or not item.is_active or not item.is_available:
                name = item.name if item is not None else "An item"
                raise ItemUnavailable(
                    f"{name} is no longer available. Remove it from your cart to check out."
                )
            lines.append((str(item.id), int(line.quantity), item.name, int(item.price_cents)))
            total += int(line.quantity) * int(item.price_cents)

        fingerprint = Cart.compute_fingerprint(str(stall.id), lines)
        if fingerprint != expected_fingerprint:
            raise PriceChanged(
                "Your cart total changed since it was loaded. Review your cart and try checkout again."
            )

        if not simulate_success:
            raise PaymentFailed(
                "Payment was not completed. Your cart is unchanged; you can try again."
            )

        order = cls(
            diner=diner,
            vendor=stall,
            items=[
                OrderItem(
                    menu_item=line.menu_item,
                    name_snapshot=line.menu_item.name,
                    price_cents_snapshot=int(line.menu_item.price_cents),
                    quantity=int(line.quantity),
                )
                for line in cart.items
            ],
            payment=Payment(
                method=payment_method,
                status="Paid",
                amount_cents=total,
                paid_at=now,
            ),
            total_cents=total,
            queue_number=new_queue_number(),
            status="Pending",
            created_at=now,
            checkout_key=checkout_key,
            checkout_fingerprint=fingerprint,
        )
        try:
            order.save()
        except (DuplicateKeyError, NotUniqueError):
            # A concurrent matching request won the race: return its order
            # instead of leaking the database exception. MongoEngine's
            # save() re-raises the pymongo duplicate-key error as its own
            # NotUniqueError, so both are caught.
            winner = cls.find_by_checkout_key(diner, checkout_key)
            if winner is not None and winner.checkout_fingerprint == expected_fingerprint:
                return winner, False
            raise CheckoutKeyConflict(
                "This checkout was already used with different cart contents. "
                "Review your cart and start checkout again."
            )

        try:
            cart.clear_items()
        except Exception:  # noqa: BLE001 - the paid order must survive a clear failure
            logger.exception(
                "Cart clear failed after order %s was stored", order.id
            )
        return order, True

    # --- scoped reads ---------------------------------------------------------

    @classmethod
    def get(cls, order_id):
        """Persistence seam: fetch one order by id; malformed ids count as missing."""
        try:
            return cls.objects.with_id(order_id)
        except (InvalidId, MongoValidationError, TypeError):
            return None

    @classmethod
    def get_for_diner(cls, diner, order_id) -> "Order":
        """One of the diner's own orders, or 404/403."""
        order = cls.get(order_id)
        if order is None:
            raise NotFound("Order not found.")
        if not same_document(order.diner, diner):
            raise Forbidden("You can only view your own orders.")
        return order

    @classmethod
    def get_for_vendor(cls, actor, order_id) -> "Order":
        """One of the actor's stall orders, or 404/403."""
        order = cls.get(order_id)
        if order is None:
            raise NotFound("Order not found.")
        if not (
            order.vendor is not None
            and actor.vendor is not None
            and actor.role == "vendor"
            and same_document(actor.vendor, order.vendor)
        ):
            raise Forbidden("You can only manage orders for your own stall.")
        return order

    @classmethod
    def list_for_vendor(cls, vendor) -> list["Order"]:
        """The stall's paid queue, newest first (all stored orders are paid)."""
        return list(cls.objects(vendor=vendor).order_by("-created_at", "-_id"))

    @classmethod
    def list_for_diner(cls, diner, view="all") -> list["Order"]:
        """The diner's own orders, filtered by All/Current/Past and newest first.

        ``view`` is ``all`` (default), ``current`` (Pending/Preparing/Ready)
        or ``history`` (Collected/Cancelled/NoShow).
        """
        if view not in ("all", "current", "history"):
            raise ValidationError("view must be one of: all, current, history.")
        if view == "current":
            orders = cls.objects(diner=diner, status__in=CURRENT_STATUSES)
        elif view == "history":
            orders = cls.objects(diner=diner, status__in=TERMINAL_STATUSES)
        else:
            orders = cls.objects(diner=diner)
        return list(orders.order_by("-created_at", "-_id"))

    # --- serialisation ---------------------------------------------------------

    def to_dict(self, actor=None, now=None) -> dict:
        data = {
            "id": str(self.id) if self.id is not None else None,
            "queue_number": self.queue_number,
            "status": self.status,
            "total_cents": int(self.total_cents),
            "created_at": iso_utc(self.created_at),
            "ready_at": iso_utc(self.ready_at),
            "vendor": {
                "id": str(self.vendor.id) if self.vendor is not None else None,
                "name": self.vendor.name if self.vendor is not None else None,
            },
            "items": [item.to_dict() for item in self.items],
            "payment": self.payment.to_dict(),
        }
        if actor is not None:
            data["allowed_actions"] = self.allowed_actions(actor, now or utcnow())
        return data
