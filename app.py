"""Canonical application entry point used by development and WSGI servers."""

from dashboard.app import app as _dashboard_app


def create_app():
    """Return the Flask application with the browser and API surfaces."""
    return _dashboard_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config.get("DEBUG", False),
    )
