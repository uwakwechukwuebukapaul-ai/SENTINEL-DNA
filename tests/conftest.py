import pytest

@pytest.fixture
def authenticated_session():
    return {"user_id": 1, "role": "analyst"}
