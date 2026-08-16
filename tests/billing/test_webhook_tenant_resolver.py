import pytest
from services.billing.webhooks import OperationalWebhookTenantResolver


class Trust:
    def __init__(self, tenant_id='tenant-a'):
        self.canonical_tenant_id = tenant_id

    def resolve(self, provider, issuer, external_tenant_id):
        assert (provider, issuer, external_tenant_id) == ('paystack', 'https://deployment', 'configured')
        return TrustResult(self.canonical_tenant_id)


class TrustResult:
    def __init__(self, tenant_id): self.canonical_tenant_id = tenant_id


def test_resolver_uses_trusted_deployment_mapping_only():
    resolver = OperationalWebhookTenantResolver(Trust(), provider='paystack', issuer='https://deployment', external_tenant_id='configured')
    assert resolver() == 'tenant-a'


def test_resolver_requires_configuration_and_does_not_accept_payload_tenant():
    with pytest.raises(ValueError):
        OperationalWebhookTenantResolver(Trust(), provider='paystack', issuer='', external_tenant_id='configured')
    resolver = OperationalWebhookTenantResolver(Trust(), provider='paystack', issuer='https://deployment', external_tenant_id='configured')
    assert resolver() == 'tenant-a'
