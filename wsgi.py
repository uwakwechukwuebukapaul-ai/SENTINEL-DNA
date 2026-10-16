"""Canonical production WSGI entry point for Sentinel DNA."""

# The dashboard application owns the browser routes, authentication API,
# canonical request context, and protected analyst surfaces. The old root
# factory only registered the investigations API and therefore did not serve
# the login/signup pages or their authentication endpoints.
from dashboard.app import app as application
