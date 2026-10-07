"""Token issuance and verification shared by every SkipQ endpoint.

Tokens are 3,600-second Bearer values signed with the locally configured
``TOKEN_SECRET`` (itsdangerous ``TimestampSigner``). The signed payload is
the account's ObjectId, so a token is worthless without the secret and
expires with it; the account is re-fetched through the ``User.find_by_id``
persistence seam, so deleted or locked-out state is honoured at request
time. Role gates live here as a pure function so every persona Blueprint
enforces the same rule, while record ownership stays in the models.
"""

from functools import wraps

from flask import current_app, request
from itsdangerous import BadSignature
from itsdangerous.timed import TimestampSigner

from app.errors import AuthenticationRequired, Forbidden
from app.models.common import as_utc, utcnow
from app.models.user import User

TOKEN_SALT = "skipq.auth-token.v1"
TOKEN_TTL_SECONDS = 3_600


class _InjectableTimestampSigner(TimestampSigner):
    """TimestampSigner whose clock callers can supply for tests."""

    def __init__(self, secret, now=None):
        super().__init__(secret, salt=TOKEN_SALT)
        self._now = now

    def get_timestamp(self):
        return int(as_utc(self._now if self._now is not None else utcnow()).timestamp())


def issue_token(user, secret, now=None) -> str:
    """Sign the 3,600-second Bearer token carrying the account's id."""
    signer = _InjectableTimestampSigner(secret, now=now)
    return signer.sign(str(user.id)).decode("ascii")


def verify_token(token, secret, now=None):
    """Return the account the token was issued to, or ``None``.

    Refused when the token is malformed, was not signed by ``secret``, is
    older than 3,600 seconds (inclusive boundary: exactly 3,600 is still
    valid), is dated in the future, or its id matches no stored account.
    """
    if not isinstance(token, str) or not token:
        return None
    signer = _InjectableTimestampSigner(secret, now=now)
    try:
        payload = signer.unsign(token.encode("ascii"), max_age=TOKEN_TTL_SECONDS)
    except (BadSignature, UnicodeEncodeError):
        return None
    return User.find_by_id(payload.decode("ascii"))


def current_user() -> User:
    """Resolve the trusted account behind the request's Bearer token."""
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme != "Bearer" or not token.strip():
        raise AuthenticationRequired("Sign in again to continue.")
    user = verify_token(token.strip(), current_app.config["TOKEN_SECRET"])
    if user is None:
        raise AuthenticationRequired("Sign in again to continue.")
    return user


def require_role(user, role) -> User:
    """Gate a persona operation: only matching accounts may continue."""
    if user is None or user.role != role:
        raise Forbidden(
            f"This action requires a {role} account. Sign in as the right persona."
        )
    return user


def role_required(role):
    """Blueprint decorator: verify the token, then enforce the persona role."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            require_role(current_user(), role)
            return view(*args, **kwargs)

        return wrapper

    return decorator
