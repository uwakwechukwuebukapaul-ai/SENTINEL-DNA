from dataclasses import FrozenInstanceError
import pytest
from services.data_fabric.models import SecurityDataSource
def test_source_is_frozen_and_tenant_scoped():
    a=SecurityDataSource('a','source-1','x'); assert a.tenant_id=='a'
    with pytest.raises(FrozenInstanceError): a.name='y'
