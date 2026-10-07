"""Diner cart: one persistent single-stall basket per diner.

The cart holds references to menu items plus integer quantities. Totals
are always integer cents computed on the server; the checkout fingerprint
is a SHA-256 freshness digest the server re-derives at checkout time.
"""

import hashlib
import json

from bson import ObjectId
from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from app.errors import (
    CrossStallCart,
    Forbidden,
    ItemUnavailable,
    StallClosed,
    ValidationError,
)
from app.models.common import document_id, iso_utc, same_document, utcnow


class CartItem(EmbeddedDocument):
    menu_item = ReferenceField("MenuItem", required=True)
    quantity = IntField(required=True, min_value=1)


class Cart(Document):
    meta = {"collection": "carts"}

    diner = ReferenceField("User", required=True, unique=True)
    vendor = ReferenceField("Vendor", default=None)
    items = ListField(EmbeddedDocumentField(CartItem), default=list)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)
    seed_key = StringField(default=None)

    # --- pure rules ----------------------------------------------------------

    @staticmethod
    def parse_quantity(value) -> int:
        """Positive whole quantities; zero is the remove-line signal."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("Quantity must be a whole number of at least 1.")
        if value < 0:
            raise ValidationError("Quantity must be a whole number of at least 1.")
        return value

    @staticmethod
    def total_cents(lines) -> int:
        """Server-side integer-cents total over cart lines."""
        total = 0
        for line in lines:
            menu_item = line.menu_item
            if menu_item is None:
                continue
            total += int(line.quantity) * int(menu_item.price_cents)
        return total

    @staticmethod
    def compute_fingerprint(vendor_id, lines) -> str:
        """SHA-256 of canonically sorted (item, quantity, name, price) lines.

        ``lines`` is an iterable of ``(item_id, quantity, name, price_cents)``
        tuples. Canonical sorting makes the digest independent of the order
        the diner happened to add lines. This is a freshness check, not a
        signature: the server re-derives it from current records.
        """
        canonical = sorted(
            (str(item_id), int(quantity), name, int(price_cents))
            for item_id, quantity, name, price_cents in lines
        )
        payload = json.dumps([vendor_id, canonical], separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def fingerprint(self) -> str | None:
        """Current fingerprint for this cart from its live records, or None when empty."""
        if not self.items:
            return None
        lines = []
        for line in self.items:
            menu_item = line.menu_item
            lines.append(
                (str(menu_item.id), line.quantity, menu_item.name, int(menu_item.price_cents))
            )
        return Cart.compute_fingerprint(document_id(self.vendor), lines)

    # --- persistence-backed cart operations -----------------------------------

    @classmethod
    def get_or_create_for_diner(cls, diner) -> "Cart":
        """Persistence seam: the diner's one cart, created empty if needed."""
        cart = cls.objects(diner=diner).first()
        if cart is None:
            cart = cls(diner=diner, vendor=None, items=[], created_at=utcnow(), updated_at=utcnow())
            cart.save()
        return cart

    @classmethod
    def clear_carts_owned_by_test(cls, diner_ids) -> int:
        """Test maintenance helper: drop carts belonging to listed diners."""
        ids = [ObjectId(str(d)) for d in diner_ids]
        return cls.objects(diner__in=ids).delete()

    def set_item(self, diner, item, quantity) -> "Cart":
        """Add or update a line after re-checking current records.

        Every check reads the current item/stall state, so a cart that was
        loaded earlier still gets a server-side refusal when the world
        changed underneath it.
        """
        if not same_document(self.diner, diner):
            raise Forbidden("This cart belongs to a different diner.")
        parsed = Cart.parse_quantity(quantity)
        if parsed == 0:
            return self.remove_item(diner, str(item.id))

        if not item.is_active or not item.is_available:
            raise ItemUnavailable(
                f"{item.name} is no longer available. Remove it from your cart to check out."
            )
        stall = item.vendor
        if stall is None or not stall.is_open:
            stall_name = stall.name if stall is not None else "This stall"
            raise StallClosed(
                f"{stall_name} is currently closed. Try again once the stall opens."
            )
        if self.vendor is not None and not same_document(self.vendor, stall):
            raise CrossStallCart(
                f"Your cart already has items from {self.vendor.name}. "
                "SkipQ orders are from one stall at a time; clear the cart first."
            )

        existing = next(
            (line for line in self.items if same_document(line.menu_item, item)),
            None,
        )
        if existing is not None:
            existing.quantity = parsed
        else:
            self.items.append(CartItem(menu_item=item, quantity=parsed))
        if self.vendor is None:
            self.vendor = stall
        self.updated_at = utcnow()
        self.save()
        return self

    def remove_item(self, diner, item_id) -> "Cart":
        """Delete one line via the remove control."""
        if not same_document(self.diner, diner):
            raise Forbidden("This cart belongs to a different diner.")
        self.items = [
            line for line in self.items if str(line.menu_item.id) != str(item_id)
        ]
        if not self.items:
            self.vendor = None
        self.updated_at = utcnow()
        self.save()
        return self

    def clear_items(self) -> "Cart":
        """Empty the cart after a paid order is stored."""
        self.items = []
        self.vendor = None
        self.updated_at = utcnow()
        self.save()
        return self

    def to_dict(self) -> dict:
        items = []
        for line in self.items:
            menu_item = line.menu_item
            items.append(
                {
                    "item_id": document_id(menu_item),
                    "name": menu_item.name if menu_item else None,
                    "price_cents": int(menu_item.price_cents) if menu_item else None,
                    "image_url": menu_item.image_url if menu_item else None,
                    "is_available": bool(menu_item.is_active and menu_item.is_available) if menu_item else False,
                    "quantity": int(line.quantity),
                    "line_cents": int(line.quantity) * int(menu_item.price_cents)
                    if menu_item
                    else 0,
                }
            )
        return {
            "vendor": document_id(self.vendor),
            "stall": self.vendor.to_dict() if self.vendor else None,
            "items": items,
            "total_cents": Cart.total_cents(self.items),
            "fingerprint": self.fingerprint(),
            "updated_at": iso_utc(self.updated_at),
        }
