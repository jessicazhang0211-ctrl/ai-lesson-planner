from werkzeug.exceptions import HTTPException
from app.utils.response import err


def register_error_handlers(app):
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return err(str(e), http_status=400)

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
        return err("internal server error", http_status=500)
