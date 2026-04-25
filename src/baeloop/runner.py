from __future__ import annotations

from collections.abc import Iterator

from baeloop.adapters.agentlab import run_agentlab_task
from baeloop.adapters.mock import run_mock_task
from baeloop.models import AgentConfig, RunRecord, TaskSet


def run_taskset(
    config: AgentConfig,
    taskset: TaskSet,
    adapter: str = "mock",
    experiment_id: str | None = None,
) -> list[RunRecord]:
    return list(iter_taskset_records(config, taskset, adapter, experiment_id))


def iter_taskset_records(
    config: AgentConfig,
    taskset: TaskSet,
    adapter: str = "mock",
    experiment_id: str | None = None,
) -> Iterator[RunRecord]:
    resolved_experiment_id = experiment_id or f"exp_{config.id}_{taskset.id}"
    if adapter == "mock":
        for task in taskset.tasks:
            yield run_mock_task(config=config, task=task, experiment_id=resolved_experiment_id)
        return
    if adapter == "agentlab":
        for task in taskset.tasks:
            yield run_agentlab_task(config=config, task=task, experiment_id=resolved_experiment_id)
        return
    raise ValueError(f"Unsupported adapter `{adapter}`. Available adapters: mock, agentlab")
