"""Vendor document: a food stall and whether it is currently trading.

A stall is the unit of vendor ownership: several vendor accounts may
reference the same stall, and vendor authorisation is always through that
stall relationship, never through one particular account.
"""

from mongoengine import BooleanField, DateTimeField, Document, StringField

from app.errors import Forbidden, ValidationError
from app.models.common import iso_utc, same_document, utcnow


class Vendor(Document):
    meta = {"collection": "vendors"}

    name = StringField(required=True, unique=True)
    is_open = BooleanField(default=False)
    created_at = DateTimeField(default=utcnow)
    seed_key = StringField(default=None)

    @classmethod
    def list_open(cls) -> list["Vendor"]:
        """Open stalls only, for diner discovery; closed stalls stay reachable by direct link."""
        return list(cls.objects(is_open=True).order_by("name"))

    @classmethod
    def get(cls, vendor_id):
        """Persistence seam: fetch one stall by id."""
        return cls.objects.with_id(vendor_id).first()

    def authorizes(self, actor) -> bool:
        """Scope check: does this vendor account manage this stall?"""
        if actor is None or actor.role != "vendor":
            return False
        return actor.vendor is not None and same_document(actor.vendor, self)

    def set_open_by_actor(self, actor, is_open) -> "Vendor":
        """Open or close the stall; only its own vendor accounts may do so."""
        if not self.authorizes(actor):
            raise Forbidden("You can only manage your own stall.")
        if not isinstance(is_open, bool):
            raise ValidationError("Trading status must be true or false.")
        self.is_open = is_open
        self.save()
        return self

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id is not None else None,
            "name": self.name,
            "is_open": bool(self.is_open),
            "created_at": iso_utc(self.created_at),
        }
