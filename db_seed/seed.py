"""Idempotent SkipQ demo seed (run with ``python -m db_seed.seed``).

Targets the configured database (``MONGODB_DB`` in ``.env``, default
``skipq_dev``). Re-running the script upserts the same demo records by
their natural keys (email, stall name, seed key) and refreshes the
time-relative fixtures; it never deletes or overwrites records that do
not belong to this seed, so unrelated data in the target database is left
alone. Time-relative states (recently Ready, overdue Ready, terminal
orders) are recomputed on every run.

Demo credentials are documented in ``README.md``; the password itself is
kept in ``fixtures.json`` and the README, not printed here.
"""

import json
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from mongoengine import disconnect

from app.models import (
    Cart,
    CartItem,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    User,
    Vendor,
)
from app.models.cart import Cart as CartModel
from app.models.common import utcnow

FIXTURES = json.loads((Path(__file__).resolve().parent / "fixtures.json").read_text())
BACKEND_ROOT = Path(__file__).resolve().parent.parent


def connect_database() -> str:
    """Point MongoEngine's default alias at the configured database."""
    load_dotenv(BACKEND_ROOT / ".env")
    host = os.getenv("MONGODB_HOST", "mongodb://127.0.0.1:27017")
    database = os.getenv("MONGODB_DB", "skipq_dev")
    from mongoengine import connect

    connect(db=database, host=host, uuidRepresentation="standard")
    return database


def seed_vendors():
    for spec in FIXTURES["vendors"]:
        vendor = Vendor.objects(name=spec["name"]).first()
        if vendor is None:
            vendor = Vendor(name=spec["name"])
        vendor.is_open = spec["is_open"]
        vendor.seed_key = spec["seed_key"]
        vendor.save()
    return len(FIXTURES["vendors"])


def seed_users():
    vendors = {v.seed_key: v for v in Vendor.objects()}
    for spec in FIXTURES["users"]:
        user = User.objects(email=User.normalize_email(spec["email"])).first()
        if user is None:
            user = User.create(
                spec["email"], FIXTURES["demo_password"], spec["role"]
            )
        user.role = spec["role"]
        user.vendor = vendors[spec["vendor_seed_key"]] if spec["role"] == "vendor" else None
        user.seed_key = spec["seed_key"]
        # Reset lockout state so sign-in tests can start from a clean counter.
        user.failed_login_count = 0
        user.locked_until = None
        user.save()
    return len(FIXTURES["users"])


def seed_menu_items():
    vendors = {v.seed_key: v for v in Vendor.objects()}
    for spec in FIXTURES["menu_items"]:
        item = MenuItem.objects(seed_key=spec["seed_key"]).first()
        if item is None:
            item = MenuItem()
        item.vendor = vendors[spec["vendor_seed_key"]]
        item.name = spec["name"]
        item.description = spec["description"]
        item.image_url = spec["image_url"]
        item.price_cents = spec["price_cents"]
        item.is_available = spec["is_available"]
        item.is_active = spec["is_active"]
        item.seed_key = spec["seed_key"]
        item.save()
    return len(FIXTURES["menu_items"])


def seed_carts():
    diners = {u.seed_key: u for u in User.objects()}
    vendors = {v.seed_key: v for v in Vendor.objects()}
    items = {i.seed_key: i for i in MenuItem.objects()}
    for spec in FIXTURES["carts"]:
        diner = diners[spec["diner_seed_key"]]
        cart = Cart.objects(diner=diner).first()
        if cart is None:
            cart = Cart(diner=diner)
        cart.vendor = vendors[spec["vendor_seed_key"]]
        cart.items = [
            CartItem(menu_item=items[line["item_seed_key"]], quantity=line["quantity"])
            for line in spec["lines"]
        ]
        cart.save()
    return len(FIXTURES["carts"])


def seed_orders():
    now = utcnow()
    diners = {u.seed_key: u for u in User.objects()}
    vendors = {v.seed_key: v for v in Vendor.objects()}
    items = {i.seed_key: i for i in MenuItem.objects()}
    for spec in FIXTURES["orders"]:
        order = Order.objects(seed_key=spec["seed_key"]).first()
        if order is None:
            order = Order(seed_key=spec["seed_key"])
        order.diner = diners[spec["diner_seed_key"]]
        order.vendor = vendors[spec["vendor_seed_key"]]
        order.queue_number = spec["queue_number"]
        order.status = spec["status"]
        order.created_at = now + timedelta(minutes=spec["created_offset_minutes"])
        order.ready_at = (
            now + timedelta(minutes=spec["ready_offset_minutes"])
            if spec.get("ready_offset_minutes") is not None
            else None
        )

        lines = []
        total = 0
        for line_spec in spec["lines"]:
            item = items[line_spec["item_seed_key"]]
            name_snapshot = line_spec.get("name_snapshot", item.name)
            price_snapshot = line_spec.get("price_cents_snapshot", item.price_cents)
            lines.append(
                OrderItem(
                    menu_item=item,
                    name_snapshot=name_snapshot,
                    price_cents_snapshot=price_snapshot,
                    quantity=line_spec["quantity"],
                )
            )
            total += price_snapshot * line_spec["quantity"]
        order.items = lines
        order.total_cents = total

        payment_status = spec["payment"]["status"]
        order.payment = Payment(
            method=spec["payment"]["method"],
            status=payment_status,
            amount_cents=total,
            paid_at=order.created_at,
            refunded_at=(
                now + timedelta(minutes=spec["refunded_offset_minutes"])
                if spec.get("refunded_offset_minutes") is not None
                else None
            ),
        )

        fingerprint_lines = [
            (str(line.menu_item.id), line.quantity, line.name_snapshot, line.price_cents_snapshot)
            for line in order.items
        ]
        order.checkout_key = f"seed-{spec['seed_key']}"
        order.checkout_fingerprint = CartModel.compute_fingerprint(
            str(order.vendor.id), fingerprint_lines
        )
        order.save()
    return len(FIXTURES["orders"])


def main() -> None:
    database = connect_database()
    try:
        counts = {
            "vendors": seed_vendors(),
            "users": seed_users(),
            "menu_items": seed_menu_items(),
            "carts": seed_carts(),
            "orders": seed_orders(),
        }
    finally:
        disconnect(alias="default")

    print(f"Seeded database '{database}':")
    for name, count in counts.items():
        print(f"  {name}: {count}")
    print(
        "Re-running this script upserts the same records; unrelated data is not "
        "deleted. Demo account credentials are documented in README.md."
    )


if __name__ == "__main__":
    main()
