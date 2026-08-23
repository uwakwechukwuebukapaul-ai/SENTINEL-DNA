"""
Runtime Task Executor Tests
"""

from services.intelligence.runtime.runtime_task_executor import (
    RuntimeTaskExecutor,
)

from services.intelligence.runtime.task import (
    Task,
)



def create_task():

    return Task(
        capability="analysis",
        payload={
            "value": 1
        },
    )



def test_init():

    executor = RuntimeTaskExecutor()

    assert (
        executor.executed
        ==
        0
    )



def test_register():

    executor = RuntimeTaskExecutor()


    executor.register(
        "analysis",
        lambda data: True,
    )


    assert (
        executor.available(
            "analysis"
        )
        is True
    )



def test_execute():

    executor = RuntimeTaskExecutor()


    executor.register(
        "analysis",
        lambda data: {
            "done":
                True
        },
    )


    result = executor.execute(
        create_task()
    )


    assert (
        result["done"]
        is True
    )



def test_task_complete():

    executor = RuntimeTaskExecutor()


    executor.register(
        "analysis",
        lambda data: True,
    )


    task = create_task()


    executor.execute(
        task
    )


    assert (
        task.status.value
        ==
        "completed"
    )



def test_missing_handler():

    executor = RuntimeTaskExecutor()


    result = executor.execute(
        create_task()
    )


    assert result["status"] == "unavailable"
    assert result["error_code"] == "capability_unavailable"



def test_status():

    executor = RuntimeTaskExecutor()


    result = executor.status()


    assert "executed" in result

    assert "failed" in result

    assert "handlers" in result
