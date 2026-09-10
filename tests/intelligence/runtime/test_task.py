from services.intelligence.runtime.task import (
    Task,
    TaskPriority,
    TaskStatus,
)


def test_task_defaults():

    task = Task(
        capability="ioc_enrichment",
        payload={"ioc": "8.8.8.8"},
    )

    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.NORMAL
    assert task.can_retry


def test_start():

    task = Task(
        capability="test",
        payload={},
    )

    task.start()

    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None


def test_queue_sets_durable_execution_state():
    task = Task(capability="test", payload={})
    task.queue()

    assert task.status == TaskStatus.QUEUED
    assert task.execution_status == "queued"
    assert task.to_dict()["execution_state"] == "QUEUED"


def test_complete():

    task = Task(
        capability="test",
        payload={},
    )

    task.complete()

    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None


def test_retry():

    task = Task(
        capability="test",
        payload={},
    )

    task.increment_retry()

    assert task.retries == 1


def test_to_dict():

    task = Task(
        capability="ioc",
        payload={"ip": "1.1.1.1"},
    )

    data = task.to_dict()

    assert data["capability"] == "ioc"
    assert data["payload"]["ip"] == "1.1.1.1"
