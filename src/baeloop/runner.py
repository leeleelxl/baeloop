from __future__ import annotations

from baeloop.adapters.agentlab import run_agentlab_task
from baeloop.adapters.mock import run_mock_task
from baeloop.models import AgentConfig, RunRecord, TaskSet


def run_taskset(
    config: AgentConfig,
    taskset: TaskSet,
    adapter: str = "mock",
    experiment_id: str | None = None,
) -> list[RunRecord]:
    resolved_experiment_id = experiment_id or f"exp_{config.id}_{taskset.id}"
    if adapter == "mock":
        return [
            run_mock_task(config=config, task=task, experiment_id=resolved_experiment_id)
            for task in taskset.tasks
        ]
    if adapter == "agentlab":
        return [
            run_agentlab_task(config=config, task=task, experiment_id=resolved_experiment_id)
            for task in taskset.tasks
        ]
    raise ValueError(f"Unsupported adapter `{adapter}`. Available adapters: mock, agentlab")
