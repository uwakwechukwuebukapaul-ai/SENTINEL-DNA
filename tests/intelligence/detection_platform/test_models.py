from dataclasses import FrozenInstanceError
import pytest
from services.intelligence.detection_platform.detection_intelligence import DetectionIntelligence
def test_detection_model_is_frozen_and_serializable():
    value=DetectionIntelligence('tenant','id'); assert value.to_dict()['tenant_id']=='tenant'
    with pytest.raises(FrozenInstanceError): value.posture='available'
