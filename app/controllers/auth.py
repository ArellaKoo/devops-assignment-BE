"""Login endpoint: exchange seeded credentials for a signed Bearer token."""

from flask import Blueprint, current_app, jsonify, request

from app.auth import issue_token
from app.errors import ValidationError
from app.models.common import utcnow
from app.models.user import User

auth_bp = Blueprint("auth", __name__)


def _required_string(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"A non-empty {name} is required to sign in.")
    return value


@auth_bp.post("/api/user/gettoken")
def get_token():
    """POST email + password. 200 with token and persona; 400/401/429 refusals."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Send a JSON body with your email and password.")
    user = User.authenticate(_required_string(data, "email"), _required_string(data, "password"), utcnow())
    token = issue_token(user, current_app.config["TOKEN_SECRET"])
    return jsonify({"token": token, "persona": user.to_dict()}), 200
