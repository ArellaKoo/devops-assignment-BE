"""Shared helpers for SkipQ model documents.

All times are stored in UTC. PyMongo returns naive datetimes, so every
persisted datetime is normalised with :func:`as_utc` before it is compared
or serialised; unit tests may supply aware datetimes and the helper is a
no-op for those.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def as_utc(value):
    """Return ``value`` as an aware UTC datetime, or ``None``."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def iso_utc(value) -> str | None:
    """Serialise a stored time as ISO 8601 UTC (``...+00:00``)."""
    normalized = as_utc(value)
    return normalized.isoformat() if normalized is not None else None


def document_id(value) -> str | None:
    """JSON boundary: document ids are strings, never BSON objects."""
    return str(value.id) if value is not None and value.id is not None else None


def same_document(a, b) -> bool:
    """Compare two records (or ids) by id so distinct instances of one record match."""
    if a is None or b is None:
        return False
    a_id = getattr(a, "id", a)
    b_id = getattr(b, "id", b)
    if a_id is None or b_id is None:
        return False
    return str(a_id) == str(b_id)
