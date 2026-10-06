"""User document: seeded accounts for the diner and vendor personas.

Emails are stored normalised (trimmed, lowercase). Passwords are stored as
Werkzeug hashes only. Lockout: failed attempts 1–4 return 401, the fifth
failed attempt locks the account for 15 minutes and returns 429, and
attempts while locked also return 429. At unlock the failure counter
resets; a successful sign-in always resets it.
"""

from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId

from mongoengine import DateTimeField, Document, IntField, ReferenceField, StringField
from werkzeug.security import check_password_hash, generate_password_hash

from app.errors import InvalidCredentials, LoginLocked
from app.models.common import as_utc, iso_utc, utcnow

FAILED_ATTEMPT_LIMIT = 5
LOCK_DURATION = timedelta(minutes=15)


class User(Document):
    meta = {"collection": "users"}

    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    role = StringField(required=True, choices=("diner", "vendor"))
    vendor = ReferenceField("Vendor", default=None)
    failed_login_count = IntField(default=0)
    locked_until = DateTimeField(default=None)
    created_at = DateTimeField(default=utcnow)
    seed_key = StringField(default=None)

    @staticmethod
    def normalize_email(email) -> str:
        """Normalise the way SkipQ stores and matches emails."""
        if not isinstance(email, str):
            raise InvalidCredentials("Incorrect email or password. You can try again.")
        return email.strip().lower()

    @classmethod
    def find_by_email(cls, email):
        """Persistence seam: look up an account by its normalised email."""
        return cls.objects(email=cls.normalize_email(email)).first()

    @classmethod
    def find_by_id(cls, user_id):
        """Persistence seam: look up an account by its stored ObjectId string."""
        try:
            return cls.objects(id=ObjectId(user_id)).first()
        except (InvalidId, TypeError, ValueError):
            return None

    @classmethod
    def create(cls, email, password, role, vendor=None, seed_key=None):
        """Persistence seam: create an account with a hashed password."""
        document = cls(
            email=cls.normalize_email(email),
            password_hash=generate_password_hash(password),
            role=role,
            vendor=vendor,
            seed_key=seed_key,
        )
        document.save()
        return document

    @classmethod
    def authenticate(cls, email, password, now) -> "User":
        """Verify credentials against the account for ``email``.

        Raises ``InvalidCredentials`` (401) for a wrong password on attempts
        1–4 and ``LoginLocked`` (429) from the fifth failed attempt, while
        locked, and after the lock expires the counter resets before
        verifying. Only ``find_by_email`` and ``save`` are persistence
        seams; the lockout logic itself runs for real.
        """
        user = cls.find_by_email(email)
        if user is None:
            raise InvalidCredentials("Incorrect email or password. You can try again.")
        return user.verify_password_and_update_lockout(password, now)

    def verify_password_and_update_lockout(self, password, now) -> "User":
        """Instance-level credential check and lockout bookkeeping."""
        now = as_utc(now)
        locked_until = as_utc(self.locked_until)
        if locked_until is not None and now < locked_until:
            raise LoginLocked(
                "This account is locked after too many failed sign-ins. "
                f"Try again after {locked_until:%H:%M} UTC."
            )
        if locked_until is not None and now >= locked_until:
            # Lock period has passed: reset the counter, then verify credentials.
            self.locked_until = None
            self.failed_login_count = 0

        if check_password_hash(self.password_hash, password):
            if self.failed_login_count or self.locked_until is not None:
                self.failed_login_count = 0
                self.locked_until = None
                self.save()
            return self

        self.failed_login_count += 1
        if self.failed_login_count >= FAILED_ATTEMPT_LIMIT:
            self.locked_until = now + LOCK_DURATION
            self.failed_login_count = 0
            self.save()
            raise LoginLocked(
                "This account is locked for 15 minutes after five failed sign-ins."
            )
        self.save()
        raise InvalidCredentials("Incorrect email or password. You can try again.")

    def to_dict(self) -> dict:
        return {
            "id": str(self.id) if self.id is not None else None,
            "email": self.email,
            "role": self.role,
            "vendor": str(self.vendor.id) if self.vendor is not None else None,
            "created_at": iso_utc(self.created_at),
        }
