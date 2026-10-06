"""Menu item document with SkipQ's menu validation rules.

Money is stored as integer cents; the API accepts a decimal price string
and the model converts it, so no binary float ever represents a price.
Removal is soft (``is_active``) so historical purchase snapshots keep a
valid menu reference.
"""

import re
from decimal import Decimal

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
)

from app.errors import Forbidden, ValidationError
from app.models.common import as_utc, document_id, iso_utc, utcnow

NAME_MAX_LENGTH = 80
DESCRIPTION_MAX_LENGTH = 500
PRICE_MAX_CENTS = 999899  # strictly below SGD 9,999.00
_PRICE_PATTERN = re.compile(r"^\d+(\.\d{1,2})?$")
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")


class MenuItem(Document):
    meta = {"collection": "menu_items", "indexes": ["vendor"]}

    vendor = ReferenceField("Vendor", required=True)
    name = StringField(required=True, max_length=NAME_MAX_LENGTH)
    description = StringField(default="")
    image_url = StringField(required=True)
    price_cents = IntField(required=True)
    is_available = BooleanField(default=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)
    seed_key = StringField(default=None)

    # --- validation rules (pure; testable without a database) --------------

    @staticmethod
    def parse_price_cents(raw) -> int:
        """Convert a decimal price string to integer cents.

        Accepts more than zero, less than 9999.00, at most two decimals.
        """
        if not isinstance(raw, str):
            raise ValidationError(
                "Price must be a decimal number, for example '6.50'."
            )
        text = raw.strip()
        if not _PRICE_PATTERN.match(text):
            raise ValidationError(
                "Price must be a number above 0, below 9999, with at most two decimal places."
            )
        cents = int(Decimal(text).scaleb(2).to_integral_value())
        if cents < 1 or cents > PRICE_MAX_CENTS:
            raise ValidationError(
                "Price must be above 0 and below 9999."
            )
        return cents

    @staticmethod
    def validate_name(raw) -> str:
        """Name is required, trimmed, and 1–80 characters."""
        if not isinstance(raw, str):
            raise ValidationError("Item name is required.")
        text = raw.strip()
        if not text or len(text) > NAME_MAX_LENGTH:
            raise ValidationError(
                f"Item name must be between 1 and {NAME_MAX_LENGTH} characters."
            )
        return text

    @staticmethod
    def validate_description(raw) -> str:
        """Description is optional and at most 500 characters."""
        if not isinstance(raw, str):
            raise ValidationError("Item description must be text.")
        if len(raw) > DESCRIPTION_MAX_LENGTH:
            raise ValidationError(
                f"Item description must be at most {DESCRIPTION_MAX_LENGTH} characters."
            )
        return raw

    @staticmethod
    def validate_image_url(raw) -> str:
        """Image must be an http(s) URL whose path identifies JPG/JPEG/PNG."""
        if not isinstance(raw, str) or not raw.strip():
            raise ValidationError("Item image URL is required.")
        from urllib.parse import urlparse

        parsed = urlparse(raw.strip())
        if parsed.scheme not in ("http", "https"):
            raise ValidationError("Item image URL must use http or https.")
        path = parsed.path.lower()
        if not path.endswith(_IMAGE_SUFFIXES):
            raise ValidationError(
                "Item image must be a JPG, JPEG, or PNG file URL."
            )
        return raw

    @staticmethod
    def validate_item_values(values) -> dict:
        """Validate a create/update payload and return cleaned fields."""
        if not isinstance(values, dict):
            raise ValidationError("Item details must be an object.")
        if "name" not in values:
            raise ValidationError("Item name is required.")
        if "price" not in values:
            raise ValidationError("Item price is required.")
        if "image_url" not in values:
            raise ValidationError("Item image URL is required.")
        is_available = values.get("is_available", True)
        if not isinstance(is_available, bool):
            raise ValidationError("Availability must be true or false.")
        return {
            "name": MenuItem.validate_name(values["name"]),
            "description": MenuItem.validate_description(values.get("description", "")),
            "image_url": MenuItem.validate_image_url(values["image_url"]),
            "price_cents": MenuItem.parse_price_cents(values["price"]),
            "is_available": is_available,
        }

    # --- scope checks -------------------------------------------------------

    def authorizes_vendor(self, actor) -> bool:
        """Scope check: does this vendor account manage this item's stall?"""
        if actor is None or actor.role != "vendor":
            return False
        return (
            actor.vendor is not None
            and self.vendor is not None
            and document_id(actor.vendor) == document_id(self.vendor)
        )

    # --- persistence-backed operations --------------------------------------

    @classmethod
    def list_for_vendor(cls, vendor) -> list["MenuItem"]:
        """The stall's published menu: active items, stable name order.

        This is the model query behind the diner menu and vendor menu
        endpoints; the load test times its materialisation.
        """
        return list(cls.objects(vendor=vendor, is_active=True).order_by("name"))

    @classmethod
    def get(cls, item_id):
        """Persistence seam: fetch one item by id."""
        return cls.objects.with_id(item_id).first()

    @classmethod
    def create_for_vendor(cls, actor, values) -> "MenuItem":
        """Create a menu item on the actor's own stall."""
        if actor is None or actor.role != "vendor" or actor.vendor is None:
            raise Forbidden("You can only add items to your own stall.")
        cleaned = MenuItem.validate_item_values(values)
        item = cls(vendor=actor.vendor, **cleaned, created_at=utcnow(), updated_at=utcnow())
        item.save()
        return item

    def update_by_actor(self, actor, values) -> "MenuItem":
        """Edit name/description/image/price/availability on own-stall items."""
        if not self.authorizes_vendor(actor):
            raise Forbidden("You can only edit items on your own stall.")
        if not isinstance(values, dict):
            raise ValidationError("Item updates must be an object.")
        if "name" in values:
            self.name = MenuItem.validate_name(values["name"])
        if "description" in values:
            self.description = MenuItem.validate_description(values["description"])
        if "image_url" in values:
            self.image_url = MenuItem.validate_image_url(values["image_url"])
        if "price" in values:
            self.price_cents = MenuItem.parse_price_cents(values["price"])
        if "is_available" in values:
            if not isinstance(values["is_available"], bool):
                raise ValidationError("Availability must be true or false.")
            self.is_available = values["is_available"]
        self.updated_at = utcnow()
        self.save()
        return self

    def mark_inactive_by_actor(self, actor) -> "MenuItem":
        """Soft delete: historical order snapshots must keep working."""
        if not self.authorizes_vendor(actor):
            raise Forbidden("You can only remove items from your own stall.")
        self.is_active = False
        self.updated_at = utcnow()
        self.save()
        return self

    def to_dict(self) -> dict:
        return {
            "id": document_id(self),
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "price_cents": int(self.price_cents),
            "is_available": bool(self.is_available),
            "is_active": bool(self.is_active),
            "updated_at": iso_utc(self.updated_at),
        }
