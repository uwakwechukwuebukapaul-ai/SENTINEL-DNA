"""Canonical production WSGI entry point for Sentinel DNA."""

from app import create_app


application = create_app()
