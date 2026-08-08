from services.intelligence.pipeline import (
    PipelineEngine,
)


class FakeIntegrator:

    def process(
        self,
        investigation,
    ):

        return {
            "decision": "respond"
        }



class FakeReporter:

    def generate(
        self,
        investigation,
    ):

        return {
            "summary": "Generated"
        }



def test_pipeline_execution():

    engine = PipelineEngine(
        integrator=FakeIntegrator(),
        reporter=FakeReporter(),
    )


    result = engine.execute(
        {
            "id": "INV-001"
        }
    )


    assert result["status"] == "completed"



def test_pipeline_integrates_intelligence():

    engine = PipelineEngine(
        integrator=FakeIntegrator(),
    )


    result = engine.execute({})


    assert (
        result["intelligence"]["decision"]
        == "respond"
    )



def test_pipeline_history():

    engine = PipelineEngine()

    engine.execute({})


    assert len(
        engine.get_history()
    ) == 1



def test_pipeline_clear_history():

    engine = PipelineEngine()

    engine.execute({})

    engine.clear_history()


    assert engine.get_history() == []