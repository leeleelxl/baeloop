from pathlib import Path

from typer.testing import CliRunner

from baeloop.adapters.agentlab import AgentLabAdapterUnavailable
from baeloop.cli import app
from baeloop.io import read_jsonl_records, write_jsonl_records
from baeloop.models import AgentConfig, RetryPolicy, RunRecord, TaskSet, TaskSpec
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


def test_cli_run_persists_partial_records_on_adapter_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "id: baseline",
                "model: gpt-4o-mini",
                "max_steps: 15",
                "",
            ]
        ),
        encoding="utf-8",
    )
    taskset_path = tmp_path / "taskset.yaml"
    taskset_path.write_text(
        "\n".join(
            [
                "id: smoke",
                "benchmark: miniwob",
                "tasks:",
                "  - env_id: browsergym/miniwob.click-button",
                "    seed: 1",
                "    max_steps: 10",
                "  - env_id: browsergym/miniwob.enter-text",
                "    seed: 2",
                "    max_steps: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "records.jsonl"

    def fake_iter_taskset_records(*args, **kwargs):
        yield RunRecord(
            experiment_id="exp_test",
            config_id="baseline",
            task_id="browsergym/miniwob.click-button#seed=1",
            status="success",
            normalized_score=1.0,
            step_count=1,
            latency_sec=1.0,
        )
        raise AgentLabAdapterUnavailable("boom")

    monkeypatch.setattr("baeloop.cli.iter_taskset_records", fake_iter_taskset_records)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--config",
            str(config_path),
            "--taskset",
            str(taskset_path),
            "--out",
            str(out),
            "--adapter",
            "agentlab",
        ],
    )

    assert result.exit_code == 1
    assert [record.task_id for record in read_jsonl_records(out)] == [
        "browsergym/miniwob.click-button#seed=1"
    ]
