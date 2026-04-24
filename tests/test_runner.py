from pathlib import Path

from baeloop.io import read_jsonl_records, write_jsonl_records
from baeloop.models import AgentConfig, RetryPolicy, TaskSet, TaskSpec
from baeloop.runner import run_taskset


def test_mock_run_is_deterministic_and_config_sensitive() -> None:
    taskset = TaskSet(
        id="smoke",
        benchmark="miniwob",
        tasks=[
            TaskSpec(env_id="browsergym/miniwob.enter-text", seed=1, max_steps=10),
            TaskSpec(env_id="browsergym/miniwob.click-checkboxes", seed=2, max_steps=25),
        ],
    )
    baseline = AgentConfig(
        id="baseline",
        model="gpt-4o-mini",
        max_steps=15,
        retry_policy=RetryPolicy(enabled=False, max_retries=0),
    )
    retry = AgentConfig(
        id="retry",
        model="gpt-4o-mini",
        max_steps=20,
        retry_policy=RetryPolicy(enabled=True, max_retries=1),
    )

    baseline_records = run_taskset(baseline, taskset)
    retry_records = run_taskset(retry, taskset)

    assert [record.status for record in baseline_records] == ["failed", "timeout"]
    assert [record.status for record in retry_records] == ["success", "success"]
    assert baseline_records == run_taskset(baseline, taskset)


def test_jsonl_roundtrip_for_run_records(tmp_path: Path) -> None:
    config = AgentConfig(id="baseline", model="gpt-4o-mini", max_steps=15)
    taskset = TaskSet(
        id="smoke",
        benchmark="miniwob",
        tasks=[TaskSpec(env_id="browsergym/miniwob.click-button", seed=1, max_steps=10)],
    )
    records = run_taskset(config, taskset)
    out = tmp_path / "records.jsonl"

    write_jsonl_records(out, records)

    assert read_jsonl_records(out) == records
