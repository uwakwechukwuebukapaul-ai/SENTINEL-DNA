import pytest

pytest.importorskip("flask")

from dashboard.app import app


def test_case_notes_require_csrf_and_authentication():
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.post("/api/cases/CASE-TEST/notes", json={"note": "review"})
    assert response.status_code == 403
