"""Offline unit tests for SkipQ sign-in, lockout, tokens and role gates.

``User.authenticate`` and the token signature/expiry logic run for real on
in-memory records; only the persistence seams (``find_by_email``, ``save``,
``find_by_id``) are supplied by the tests. The shared unit fixture's socket
sentinel fails the suite on any accidental database connection.
"""

from datetime import datetime, timedelta, timezone
from bson import ObjectId

import pytest
from werkzeug.security import generate_password_hash

from app.errors import (
    AuthenticationRequired,
    Forbidden,
    InvalidCredentials,
    LoginLocked,
)
from app.models.user import User

SECRET = "unit-test-token-secret"
OTHER_SECRET = "another-token-secret"
T0 = datetime(2026, 10, 7, 12, 0, 0, tzinfo=timezone.utc)


def _code(excinfo):
    return excinfo.value.code


def make_account(email="diner.one@skipq.test", password="correct-horse", role="diner"):
    return User(
        id=ObjectId(),
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        failed_login_count=0,
        locked_until=None,
    )


@pytest.fixture
def account(monkeypatch):
    """Supply record access: find_by_email resolves the in-memory account, save is recorded."""
    user = make_account()
    saved = []
    monkeypatch.setattr(
        User,
        "find_by_email",
        staticmethod(lambda email: user if User.normalize_email(email) == user.email else None),
    )
    monkeypatch.setattr(User, "save", lambda self, *args, **kwargs: (saved.append(self), self)[1])
    return user, saved


@pytest.fixture
def token_seam(monkeypatch):
    """Supply find_by_id so token verification never touches MongoDB; record lookups."""
    user = make_account()
    seen = []

    def find_by_id(user_id):
        seen.append(user_id)
        return user if user_id == str(user.id) else None

    monkeypatch.setattr(User, "find_by_id", staticmethod(find_by_id))
    return user, seen


class TestEmailNormalisation:
    def test_strips_and_lowercases_email(self):
        """GIVEN the email '  Diner.One@SkipQ.TEST ' WHEN it is normalised THEN it is stored as 'diner.one@skipq.test'."""
        assert User.normalize_email("  Diner.One@SkipQ.TEST ") == "diner.one@skipq.test"

    @pytest.mark.parametrize("value", [None, 42, ["diner.one@skipq.test"]])
    def test_refuses_non_string_email(self, value):
        """GIVEN a missing or non-string email WHEN it is normalised THEN an invalid-credentials error is raised."""
        with pytest.raises(InvalidCredentials):
            User.normalize_email(value)


class TestCredentialChecks:
    def test_correct_password_returns_account_and_keeps_counter_zero(self, account):
        """GIVEN a seeded diner WHEN they sign in with the correct password THEN the account is returned and no failure is recorded."""
        user, _ = account
        result = User.authenticate(user.email, "correct-horse", T0)
        assert result is user
        assert user.failed_login_count == 0
        assert user.locked_until is None

    def test_first_four_wrong_passwords_raise_401_and_count(self, account):
        """GIVEN a seeded diner WHEN the password is wrong on attempts 1–4 THEN each attempt raises 401 and the failure counter grows to the attempt number."""
        user, _ = account
        for attempt in range(1, 5):
            with pytest.raises(InvalidCredentials) as excinfo:
                User.authenticate(user.email, "wrong", T0)
            assert _code(excinfo) == "invalid_credentials"
            assert user.failed_login_count == attempt

    def test_fifth_wrong_password_locks_for_15_minutes(self, account):
        """GIVEN four recorded failures WHEN the fifth attempt is also wrong THEN the account is locked for 15 minutes from the attempt, the counter resets, and 429 is raised."""
        user, _ = account
        for _ in range(4):
            with pytest.raises(InvalidCredentials):
                User.authenticate(user.email, "wrong", T0)
        with pytest.raises(LoginLocked) as excinfo:
            User.authenticate(user.email, "wrong", T0)
        assert _code(excinfo) == "login_locked"
        assert user.locked_until == T0 + timedelta(minutes=15)
        assert user.failed_login_count == 0

    def test_locked_account_refuses_even_correct_password_before_unlock(self, account):
        """GIVEN an account locked until 15 minutes from now WHEN it signs in with the correct password five minutes in THEN the lock refuses it before the password is checked."""
        user, _ = account
        user.locked_until = T0 + timedelta(minutes=15)
        with pytest.raises(LoginLocked):
            User.authenticate(user.email, "correct-horse", T0 + timedelta(minutes=5))

    def test_lock_expires_at_the_inclusive_boundary(self, account):
        """GIVEN an account whose lock ends at T WHEN a wrong password is tried at T THEN the account is no longer locked and the attempt counts as the first failure."""
        user, _ = account
        user.locked_until = T0
        with pytest.raises(InvalidCredentials):
            User.authenticate(user.email, "wrong", T0)
        assert user.failed_login_count == 1
        assert user.locked_until is None

    def test_correct_password_after_lock_expiry_restores_the_account(self, account):
        """GIVEN an expired lock WHEN the correct password is used after it expires THEN the account signs in and the lock and counter are cleared."""
        user, _ = account
        user.locked_until = T0 - timedelta(minutes=1)
        user.failed_login_count = 4
        result = User.authenticate(user.email, "correct-horse", T0)
        assert result is user
        assert user.locked_until is None
        assert user.failed_login_count == 0

    def test_unknown_email_raises_401(self, account):
        """GIVEN an email with no stored account WHEN sign-in is attempted THEN an invalid-credentials 401 is raised without leaking which part was wrong."""
        _, _ = account
        with pytest.raises(InvalidCredentials) as excinfo:
            User.authenticate("nobody@skipq.test", "correct-horse", T0)
        assert _code(excinfo) == "invalid_credentials"

    @pytest.mark.parametrize("value", [None, 42])
    def test_non_string_email_raises_401(self, value, account):
        """GIVEN a missing or non-string email field WHEN sign-in is attempted THEN an invalid-credentials 401 is raised."""
        _, _ = account
        with pytest.raises(InvalidCredentials):
            User.authenticate(value, "correct-horse", T0)


class TestRoleGates:
    def test_matching_role_returns_the_actor(self):
        """GIVEN a diner account WHEN the diner role is required THEN the same account is returned so the model can apply scope checks."""
        from app.auth import require_role

        user = make_account()
        assert require_role(user, "diner") is user

    def test_wrong_role_is_refused_with_an_actionable_message(self):
        """GIVEN a vendor account WHEN the diner role is required THEN a 403 names the role the action needs."""
        from app.auth import require_role

        user = make_account(role="vendor")
        with pytest.raises(Forbidden) as excinfo:
            require_role(user, "diner")
        assert "diner" in excinfo.value.message

    def test_missing_actor_is_refused(self):
        """GIVEN no verified account WHEN any role gate is applied THEN a 403 is raised before record access."""
        from app.auth import require_role

        with pytest.raises(Forbidden):
            require_role(None, "vendor")

    def test_unrecognised_role_value_is_refused_by_every_persona(self):
        """GIVEN an account whose role is not diner or vendor WHEN any persona gate is applied THEN both persona gates refuse it."""
        from app.auth import require_role

        user = make_account()
        user.role = "admin"
        with pytest.raises(Forbidden):
            require_role(user, "diner")
        with pytest.raises(Forbidden):
            require_role(user, "vendor")


class TestTokenLifetime:
    def test_round_trip_returns_the_trusted_account(self, token_seam):
        """GIVEN a token issued at T WHEN it is verified at T with the same secret THEN the stored account is returned through the id seam."""
        user, seen = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0)
        assert verify_token(token, SECRET, now=T0) is user
        assert seen == [str(user.id)]

    def test_token_is_valid_at_the_exact_ttl_boundary(self, token_seam):
        """GIVEN a token issued at T WHEN it is verified 3,600 seconds later THEN it is still accepted, inclusive of the expiry."""
        user, _ = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0)
        assert verify_token(token, SECRET, now=T0 + timedelta(seconds=3600)) is user

    def test_token_one_second_past_ttl_is_refused(self, token_seam):
        """GIVEN a token issued at T WHEN it is verified 3,601 seconds later THEN it is refused and the account seam is never consulted."""
        user, seen = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0)
        assert verify_token(token, SECRET, now=T0 + timedelta(seconds=3601)) is None
        assert seen == []

    def test_token_signed_in_the_future_is_refused(self, token_seam):
        """GIVEN a token issued five minutes from now WHEN it is verified at now THEN the negative age is refused rather than accepted early."""
        user, _ = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0 + timedelta(minutes=5))
        assert verify_token(token, SECRET, now=T0) is None

    def test_tampered_payload_is_refused(self, token_seam):
        """GIVEN a valid token WHEN one character of its payload is altered THEN the signature mismatch refuses it."""
        user, _ = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0)
        payload, _, rest = token.partition(".")
        assert verify_token(payload + "x" + "." + rest, SECRET, now=T0) is None

    def test_token_from_a_different_secret_is_refused(self, token_seam):
        """GIVEN a token signed with one secret WHEN it is verified with another THEN it is refused."""
        user, _ = token_seam
        from app.auth import issue_token, verify_token

        token = issue_token(user, SECRET, now=T0)
        assert verify_token(token, OTHER_SECRET, now=T0) is None

    @pytest.mark.parametrize("token", ["garbage", "a.b.c", ""])
    def test_malformed_tokens_are_refused(self, token, token_seam):
        """GIVEN a token without the signed payload, timestamp and signature parts WHEN it is verified THEN it is refused without leaking internals."""
        _, seen = token_seam
        from app.auth import verify_token

        assert verify_token(token, SECRET, now=T0) is None
        assert seen == []

    @pytest.mark.parametrize("token", ["é", "not-a-token-é", "令牌"])
    def test_non_ascii_tokens_are_refused_without_account_lookup(self, token, token_seam):
        """GIVEN a non-ASCII token WHEN it is verified THEN it is refused before any account lookup."""
        _, seen = token_seam
        from app.auth import verify_token

        assert verify_token(token, SECRET, now=T0) is None
        assert seen == []

    def test_signed_but_unknown_account_is_refused(self, token_seam):
        """GIVEN a token whose signature verifies but whose id matches no stored account WHEN it is verified THEN no user is returned."""
        from app.auth import issue_token, verify_token

        stranger = make_account(email="diner.two@skipq.test")
        token = issue_token(stranger, SECRET, now=T0)
        assert verify_token(token, SECRET, now=T0) is None


class TestCurrentUser:
    def test_non_ascii_bearer_on_protected_route_returns_401(self, app, token_seam):
        """GIVEN a non-ASCII Bearer token WHEN a protected route is called THEN 401 authentication_required is returned without an account lookup."""
        _, seen = token_seam

        response = app.test_client().get(
            "/api/diner/stalls", headers={"Authorization": "Bearer é"}
        )

        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "authentication_required"
        assert seen == []

    def test_missing_authorisation_header_requires_sign_in(self, app):
        """GIVEN a request with no Authorization header WHEN the current user is resolved THEN authentication_required is raised."""
        with app.test_request_context():
            from app.auth import current_user

            with pytest.raises(AuthenticationRequired):
                current_user()

    @pytest.mark.parametrize(
        "header",
        ["Token abc", "Basic abc", "Bearer", "Bearer   ", "bearer abc"],
    )
    def test_malformed_authorisation_header_requires_sign_in(self, app, header):
        """GIVEN an Authorization header that is not a Bearer token WHEN the current user is resolved THEN authentication_required is raised."""
        with app.test_request_context(headers={"Authorization": header}):
            from app.auth import current_user

            with pytest.raises(AuthenticationRequired):
                current_user()

    def test_garbage_bearer_token_requires_sign_in(self, app):
        """GIVEN a Bearer value with no valid signed parts WHEN the current user is resolved THEN authentication_required is raised."""
        with app.test_request_context(headers={"Authorization": "Bearer not-a-token"}):
            from app.auth import current_user

            with pytest.raises(AuthenticationRequired):
                current_user()

    def test_valid_bearer_token_returns_the_trusted_account(self, app, monkeypatch):
        """GIVEN a Bearer token signed with the app's secret WHEN the current user is resolved THEN the trusted account is returned."""
        user = make_account()
        monkeypatch.setattr(
            User, "find_by_id", staticmethod(lambda user_id: user if user_id == str(user.id) else None)
        )
        from app.auth import current_user, issue_token

        token = issue_token(user, app.config["TOKEN_SECRET"])
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            assert current_user() is user


class TestGetTokenEndpoint:
    def test_valid_login_returns_token_and_persona_without_credentials(self, app, account, monkeypatch):
        """GIVEN a seeded diner WHEN they POST correct credentials (un-normalised email) THEN 200 carries a token and persona, no password hash, and the token verifies to the account."""
        user, _ = account
        from app.auth import verify_token

        response = app.test_client().post(
            "/api/user/gettoken",
            json={"email": "  Diner.One@SkipQ.TEST ", "password": "correct-horse"},
        )
        assert response.status_code == 200
        body = response.get_json()
        assert isinstance(body["token"], str)
        assert body["persona"]["email"] == "diner.one@skipq.test"
        assert body["persona"]["role"] == "diner"
        assert body["persona"]["id"] == str(user.id)
        assert "password_hash" not in response.get_data(as_text=True)
        monkeypatch.setattr(
            User, "find_by_id", staticmethod(lambda user_id: user if user_id == str(user.id) else None)
        )
        assert verify_token(body["token"], app.config["TOKEN_SECRET"]) is user

    def test_wrong_password_returns_401_invalid_credentials(self, app, account):
        """GIVEN a seeded diner with a wrong password WHEN they POST to /api/user/gettoken THEN 401 invalid_credentials is returned and one failure is recorded."""
        user, _ = account
        response = app.test_client().post(
            "/api/user/gettoken", json={"email": user.email, "password": "wrong"}
        )
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "invalid_credentials"
        assert user.failed_login_count == 1

    def test_locked_account_returns_429_login_locked(self, app, monkeypatch):
        """GIVEN an account locked for ten more minutes WHEN anyone signs in with it THEN 429 login_locked is returned."""
        user = make_account()
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        monkeypatch.setattr(
            User, "find_by_email", staticmethod(lambda email: user if email == user.email else None)
        )
        response = app.test_client().post(
            "/api/user/gettoken", json={"email": user.email, "password": "correct-horse"}
        )
        assert response.status_code == 429
        assert response.get_json()["error"]["code"] == "login_locked"

    def test_unknown_email_returns_401(self, app, account):
        """GIVEN an email with no account WHEN sign-in is POSTed THEN 401 invalid_credentials is returned, the same refusal as a wrong password."""
        _, _ = account
        response = app.test_client().post(
            "/api/user/gettoken", json={"email": "nobody@skipq.test", "password": "x"}
        )
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "invalid_credentials"

    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"email": "diner.one@skipq.test"},
            {"password": "correct-horse"},
            {"email": "diner.one@skipq.test", "password": ""},
            ["not", "an", "object"],
        ],
    )
    def test_malformed_login_body_returns_400(self, app, account, payload):
        """GIVEN a login body that is missing email or password or is not an object WHEN it is POSTed THEN 400 validation_error names what to fix."""
        _, _ = account
        response = app.test_client().post(
            "/api/user/gettoken",
            json=None if payload == ["not", "an", "object"] else payload,
        )
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "validation_error"

    def test_login_without_json_body_returns_400(self, app, account):
        """GIVEN a POST with no body WHEN it reaches /api/user/gettoken THEN 400 validation_error asks for the JSON email and password."""
        _, _ = account
        response = app.test_client().post("/api/user/gettoken")
        assert response.status_code == 400
        assert response.get_json()["error"]["code"] == "validation_error"
