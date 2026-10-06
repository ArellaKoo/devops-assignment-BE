"""Return a JSON refusal instead of Flask's default HTML error page."""

from flask import current_app, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app) -> None:
    @app.errorhandler(HTTPException)
    def http_error(error):
        codes = {
            400: "validation_error",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
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
