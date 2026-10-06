"""Startup regression checks; these do not replace assessed domain tests."""

import pytest
from mongoengine import get_db
from werkzeug.exceptions import TooManyRequests


def test_json_method_refusal_preserves_allow_header(app):
    """GIVEN a GET route WHEN POST is refused THEN JSON retains allowed methods."""
    app.add_url_rule("/fixture-only", view_func=lambda: "OK", methods=["GET"])

    response = app.test_client().post("/fixture-only")

    assert response.status_code == 405
    assert response.is_json
    assert response.get_json()["error"]["code"] == "method_not_allowed"
    assert "GET" in response.headers.get("Allow", "").split(", ")


def test_json_throttling_refusal_preserves_retry_after(app):
    """GIVEN retry timing WHEN an HTTP refusal becomes JSON THEN timing remains."""
    def rate_limited():
        raise TooManyRequests(retry_after=60)

    app.add_url_rule("/fixture-only", view_func=rate_limited)

    response = app.test_client().get("/fixture-only")

    assert response.status_code == 429
    assert response.is_json
    assert response.headers.get("Retry-After") == "60"


@pytest.mark.parametrize(
    ("app", "expected_database"),
    [
        ("skipq_unit_alpha", "skipq_unit_alpha"),
        ("skipq_unit_beta", "skipq_unit_beta"),
    ],
    indirect=["app"],
)
def test_factory_database_changes_after_fixture_teardown(app, expected_database):
    """GIVEN sequential fixtures WHEN DB changes THEN the prior alias is released."""
    assert get_db().name == expected_database
