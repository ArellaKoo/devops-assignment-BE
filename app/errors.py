"""JSON refusal contract for every SkipQ endpoint.

Rules raise :class:`DomainError` subclasses with a stable error code and an
actionable message; the registered handler turns them into the JSON error
shape used by every refusal in the application.
"""

from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException


class DomainError(Exception):
    """A business-rule refusal that maps to a stable JSON error response."""

    code = "request_refused"
    status = 409

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    code = "validation_error"
    status = 400


class AuthenticationRequired(DomainError):
    code = "authentication_required"
    status = 401


class InvalidCredentials(DomainError):
    code = "invalid_credentials"
    status = 401


class LoginLocked(DomainError):
    code = "login_locked"
    status = 429


class Forbidden(DomainError):
    code = "forbidden"
    status = 403


class NotFound(DomainError):
    code = "not_found"
    status = 404


class StallClosed(DomainError):
    code = "stall_closed"
    status = 409


class ItemUnavailable(DomainError):
    code = "item_unavailable"
    status = 409


class CrossStallCart(DomainError):
    code = "cross_stall_cart"
    status = 409


class CartEmpty(DomainError):
    code = "cart_empty"
    status = 409


class PriceChanged(DomainError):
    code = "price_changed"
    status = 409


class PaymentFailed(DomainError):
    code = "payment_failed"
    status = 409


class CheckoutKeyConflict(DomainError):
    code = "checkout_key_conflict"
    status = 409


class InvalidTransition(DomainError):
    code = "invalid_transition"
    status = 409


class NoShowTooEarly(DomainError):
    code = "no_show_too_early"
    status = 409


def register_error_handlers(app) -> None:
    @app.errorhandler(DomainError)
    def domain_error(error):
        return (
            jsonify(error={"code": error.code, "message": error.message}),
            error.status,
        )

    @app.errorhandler(HTTPException)
    def http_error(error):
        codes = {
            400: "validation_error",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            429: "rate_limited",
        }
        response = error.get_response()
        response.data = current_app.json.dumps(
            {
                "error": {
                    "code": codes.get(error.code, "request_refused"),
                    "message": error.description,
                }
            }
        )
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unhandled application error")
        return jsonify(
            error={
                "code": "internal_error",
                "message": "The request could not be completed. Please try again.",
            }
        ), 500
