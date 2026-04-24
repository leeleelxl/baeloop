from __future__ import annotations

from baeloop.models import AgentConfig, RunRecord, RunStatus, TaskSpec


def run_mock_task(config: AgentConfig, task: TaskSpec, experiment_id: str) -> RunRecord:
    """Return deterministic smoke-test records without launching a browser."""
    retry_enabled = config.retry_policy.enabled and config.retry_policy.max_retries > 0
    task_name = task.env_id.rsplit(".", maxsplit=1)[-1]
    step_budget = min(config.max_steps, task.max_steps)

    if task_name == "enter-text" and not retry_enabled:
        return _record(
            experiment_id=experiment_id,
            config_id=config.id,
            task=task,
            status="failed",
            score=0.0,
            steps=min(step_budget, 5),
            latency=4.1,
            failure_type="invalid_action",
        )

    if task_name == "drag-box" and not retry_enabled:
        return _record(
            experiment_id=experiment_id,
            config_id=config.id,
            task=task,
            status="failed",
            score=0.0,
            steps=step_budget,
            latency=8.4,
            failure_type="no_op_loop",
        )

    if task_name == "click-checkboxes" and step_budget < 20:
        return _record(
            experiment_id=experiment_id,
            config_id=config.id,
            task=task,
            status="timeout",
            score=0.0,
            steps=step_budget,
            latency=9.0,
            failure_type="timeout",
        )

    required_steps = _required_success_steps(task_name, retry_enabled=retry_enabled)
    if step_budget < required_steps:
        return _record(
            experiment_id=experiment_id,
            config_id=config.id,
            task=task,
            status="max_steps",
            score=0.0,
            steps=step_budget,
            latency=step_budget * 0.5,
            failure_type="max_steps",
        )

    return _success_record(config=config, task=task, experiment_id=experiment_id)


def _success_record(config: AgentConfig, task: TaskSpec, experiment_id: str) -> RunRecord:
    task_name = task.env_id.rsplit(".", maxsplit=1)[-1]
    step_budget = min(config.max_steps, task.max_steps)
    required_steps = _required_success_steps(
        task_name,
        retry_enabled=config.retry_policy.enabled and config.retry_policy.max_retries > 0,
    )
    latency_by_task = {
        "click-button": 3.2,
        "enter-text": 5.2
        if config.retry_policy.enabled and config.retry_policy.max_retries > 0
        else 4.1,
        "choose-list": 4.7,
        "drag-box": 7.8,
        "click-checkboxes": 10.5,
    }
    return _record(
        experiment_id=experiment_id,
        config_id=config.id,
        task=task,
        status="success",
        score=1.0,
        steps=min(required_steps, step_budget),
        latency=latency_by_task.get(task_name, 4.0),
        failure_type=None,
    )


def _required_success_steps(task_name: str, retry_enabled: bool) -> int:
    return {
        "click-button": 4,
        "enter-text": 7 if retry_enabled else 5,
        "choose-list": 6,
        "drag-box": 12,
        "click-checkboxes": 18,
    }.get(task_name, 5)


def _record(
    experiment_id: str,
    config_id: str,
    task: TaskSpec,
    status: RunStatus,
    score: float,
    steps: int,
    latency: float,
    failure_type: str | None,
) -> RunRecord:
    return RunRecord(
        experiment_id=experiment_id,
        config_id=config_id,
        task_id=task.task_id,
        status=status,
        normalized_score=score,
        step_count=steps,
        latency_sec=latency,
        failure_type=failure_type,
    )
