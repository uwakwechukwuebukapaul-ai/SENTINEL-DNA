"""
Agent Pipeline Runtime Integration Tests
"""

from services.intelligence.orchestration.agent_pipeline import (
    AgentPipeline,
)

from services.intelligence.orchestration.orchestration_result import (
    OrchestrationResult,
)

from services.intelligence.runtime.runtime_task_executor import (
    RuntimeTaskExecutor,
)

from services.intelligence.runtime.task import (
    Task,
    TaskStatus,
)


class FakeAgent:

    def __init__(
        self,
        name="analysis",
    ):
        self.name = name
        self.executed = 0


    def execute(
        self,
        context,
    ):

        self.executed += 1

        return {
            "success": True,
            "context": context,
        }



class FakeRegistry:

    def __init__(
        self,
        agent,
    ):
        self.agent = agent


    def get(
        self,
        name,
    ):

        if name == self.agent.name:
            return self.agent

        return None



class FakePlan:

    def __init__(
        self,
        name="runtime-test",
    ):
        self.name = name
        self.agents = [
            "analysis"
        ]



class FakeContext:

    case_id = "CASE-001"



class FakeRuntime:

    def __init__(self):

        self.task_executor = RuntimeTaskExecutor()



def test_pipeline_returns_orchestration_result():

    agent = FakeAgent()

    pipeline = AgentPipeline(
        registry=FakeRegistry(agent),
    )


    result = pipeline.execute(
        FakePlan(),
        FakeContext(),
    )


    assert isinstance(
        result,
        OrchestrationResult,
    )

    assert result.success is True

    assert "analysis" in result.agents_executed



def test_pipeline_executes_agent():

    agent = FakeAgent()

    pipeline = AgentPipeline(
        registry=FakeRegistry(agent),
    )


    result = pipeline.execute(
        FakePlan(),
        FakeContext(),
    )


    assert agent.executed == 1

    assert "analysis" in result.results



def test_pipeline_missing_agent_records_error():

    class EmptyRegistry:

        def get(
            self,
            name,
        ):
            return None


    pipeline = AgentPipeline(
        registry=EmptyRegistry(),
    )


    result = pipeline.execute(
        FakePlan(),
        FakeContext(),
    )


    assert result.success is False

    assert len(result.errors) == 1

    assert "Agent not found: analysis" in result.errors[0]



def test_runtime_task_executor_executes_capability():

    runtime = FakeRuntime()


    runtime.task_executor.register(
        "analysis",
        lambda payload: {
            "success": True,
            "value": payload["value"],
        },
    )


    task = Task(
        capability="analysis",
        payload={
            "value": 42,
        },
    )


    result = runtime.task_executor.execute(
        task,
    )


    assert result["success"] is True

    assert result["value"] == 42

    assert task.status == TaskStatus.COMPLETED



def test_runtime_task_executor_missing_capability_fails_task():

    runtime = FakeRuntime()


    task = Task(
        capability="missing",
        payload={},
    )


    result = runtime.task_executor.execute(
        task,
    )


    assert result["status"] == "unavailable"
    assert result["error_code"] == "capability_unavailable"

    assert task.status == TaskStatus.FAILED

    assert runtime.task_executor.failed == 1
