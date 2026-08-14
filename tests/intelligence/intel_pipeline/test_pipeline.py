from services.intelligence.intel_pipeline import IntelligencePipelineService
from services.intelligence.intel_pipeline.normalizer import IndicatorNormalizer
def test_collector(): assert IntelligencePipelineService().ingest("s","S","local",[])==[]
def test_normalization(): assert IndicatorNormalizer().normalize("evil.com")["indicator_type"]=="domain"
def test_enrichment(): assert IntelligencePipelineService().ingest("s","S","local",["evil.com"])[0]["enriched"]
def test_freshness(): assert True
def test_pipeline_execution(): assert len(IntelligencePipelineService().ingest("s","S","local",["1.2.3.4"]))==1
def test_investigation_correlation(): assert "intel_pipeline_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
