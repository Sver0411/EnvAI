import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.production import ProductionConfigError, validate_production_config


def _settings(**overrides):
    values = {
        'secret_key': 'a' * 48,
        'database_url': 'postgresql+psycopg://envai:pass@db:5432/envai',
        'environment': 'production',
        'debug': False,
        'payment_provider': 'manual',
        'ai_provider': 'openai_compatible',
        'embedding_provider': 'managed_embedding',
        'cors_origins': ['https://app.example.com'],
        'allowed_hosts': ['app.example.com'],
        'docs_enabled': False,
    }
    values.update(overrides)
    return Settings(**values)


def test_production_config_rejects_unsafe_values():
    with pytest.raises(ProductionConfigError):
        validate_production_config(_settings(debug=True))
    with pytest.raises(ProductionConfigError):
        validate_production_config(_settings(payment_provider='mock'))
    with pytest.raises(ProductionConfigError):
        validate_production_config(_settings(ai_provider='mock'))
    with pytest.raises(ProductionConfigError):
        validate_production_config(_settings(secret_key='change-me-in-production-please-use-a-long-random-secret'))
    with pytest.raises(ProductionConfigError):
        validate_production_config(_settings(cors_origins=['*']))


def test_health_and_request_id(client):
    live = client.get('/health/live')
    assert live.json()['code'] == 0
    assert live.headers['X-Request-ID']
    assert live.headers['X-Content-Type-Options'] == 'nosniff'
    assert client.get('/health/ready').json()['code'] == 0
    assert 'envai_http_requests_total' in client.get('/metrics').text
