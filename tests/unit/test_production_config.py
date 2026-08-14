import pytest
from config.production import ProductionConfig

def test_production_secret_is_validated(monkeypatch):
    monkeypatch.setenv("SENTINEL_DNA_ENV", "production")
    monkeypatch.setenv("SENTINEL_DNA_SECRET_KEY", "short")
    with pytest.raises(RuntimeError): ProductionConfig.from_env()
