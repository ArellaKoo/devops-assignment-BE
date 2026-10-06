"""Simulated payment receipt, embedded in the paid order it belongs to.

Payment is separate from fulfillment status: a rejected order becomes
``Cancelled`` with its payment ``Refunded``, while a no-show stays paid.
No gateway, card, or bank details are stored.
"""

from mongoengine import DateTimeField, EmbeddedDocument, IntField, StringField

from app.models.common import iso_utc

PAYMENT_METHODS = ("PayNow", "Card", "Cashless")
PAYMENT_STATUSES = ("Paid", "Refunded")


class Payment(EmbeddedDocument):
    method = StringField(required=True, choices=PAYMENT_METHODS)
    status = StringField(default="Paid", choices=PAYMENT_STATUSES)
    amount_cents = IntField(required=True, min_value=1)
    paid_at = DateTimeField(required=True)
    refunded_at = DateTimeField(default=None)

    def mark_refunded(self, now):
        from app.models.common import utcnow

        self.status = "Refunded"
        self.refunded_at = now or utcnow()

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "status": self.status,
            "amount_cents": int(self.amount_cents),
            "paid_at": iso_utc(self.paid_at),
            "refunded_at": iso_utc(self.refunded_at),
        }
