from pathlib import Path
import pickle

import pytest

from baeloop.adapters.agentlab import (
    AgentLabAdapterUnavailable,
    OpenAICompatibleModelArgs,
    _agentlab_retry_attempts,
    _preflight_config_credentials,
    _required_api_key_env,
    _run_record_from_summary,
    _task_name_from_env_id,
    run_agentlab_task,
)
from baeloop.doctor import probe_miniwob_url, probe_modules, probe_playwright_chromium
from baeloop.models import (
    AgentConfig,
    DependencyProbe,
    EnvironmentReport,
    RetryPolicy,
    TaskSet,
    TaskSpec,
)
from baeloop.runner import run_taskset


def test_probe_modules_reports_available_and_missing_modules() -> None:
    probes = probe_modules(["sys", "baeloop_missing_dependency_for_test"])
    by_module = {probe.module: probe for probe in probes}

    assert by_module["sys"].available is True
    assert by_module["baeloop_missing_dependency_for_test"].available is False


def test_probe_modules_supports_non_strict_spec_mode() -> None:
    probes = probe_modules(["sys", "baeloop_missing_dependency_for_test"], strict_import=False)
    by_module = {probe.module: probe for probe in probes}

    assert by_module["sys"].available is True
    assert by_module["baeloop_missing_dependency_for_test"].available is False


def test_playwright_chromium_probe_reports_existing_executable(tmp_path: Path) -> None:
    executable = tmp_path / "chromium"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    probe = probe_playwright_chromium(
        sync_playwright_factory=lambda: FakePlaywrightContext(str(executable))
    )

    assert probe.available is True
    assert probe.note == str(executable)


def test_playwright_chromium_probe_reports_missing_executable(tmp_path: Path) -> None:
    missing_executable = tmp_path / "missing-chromium"

    probe = probe_playwright_chromium(
        sync_playwright_factory=lambda: FakePlaywrightContext(str(missing_executable))
    )

    assert probe.available is False
    assert "playwright install chromium" in str(probe.note)


def test_miniwob_url_probe_reports_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINIWOB_URL", raising=False)

    probe = probe_miniwob_url()

    assert probe.available is False
    assert "not set" in str(probe.note)


def test_miniwob_url_probe_accepts_existing_file_url(tmp_path: Path) -> None:
    miniwob_dir = tmp_path / "miniwob"
    miniwob_dir.mkdir()

    probe = probe_miniwob_url(f"file://{miniwob_dir}")

    assert probe.available is True


def test_agentlab_adapter_fails_actionably_when_dependencies_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "baeloop.adapters.agentlab.probe_agentlab_environment",
        lambda **_: probe_modules_report_ready(False),
    )

    with pytest.raises(AgentLabAdapterUnavailable, match="Missing modules: agentlab"):
        run_agentlab_task(
            config=AgentConfig(id="baseline", model="gpt-4o-mini", max_steps=15),
            task=TaskSpec(env_id="browsergym/miniwob.click-button", seed=1, max_steps=10),
            experiment_id="exp_test",
        )


def test_agentlab_runtime_preflight_skips_repeated_chromium_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_kwargs = {}

    def fake_probe_agentlab_environment(**kwargs):
        captured_kwargs.update(kwargs)
        return probe_modules_report_ready(False)

    monkeypatch.setattr(
        "baeloop.adapters.agentlab.probe_agentlab_environment",
        fake_probe_agentlab_environment,
    )

    with pytest.raises(AgentLabAdapterUnavailable):
        run_agentlab_task(
            config=AgentConfig(id="baseline", model="gpt-4o-mini", max_steps=15),
            task=TaskSpec(env_id="browsergym/miniwob.click-button", seed=1, max_steps=10),
            experiment_id="exp_test",
        )

    assert captured_kwargs == {"check_playwright_browser": False}


def test_runner_accepts_agentlab_adapter_path(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run_agentlab_task(config: AgentConfig, task: TaskSpec, experiment_id: str):
        calls.append((config.id, task.task_id, experiment_id))
        raise RuntimeError("stop after dispatch")

    monkeypatch.setattr("baeloop.runner.run_agentlab_task", fake_run_agentlab_task)

    with pytest.raises(RuntimeError, match="stop after dispatch"):
        run_taskset(
            config=AgentConfig(id="baseline", model="gpt-4o-mini", max_steps=15),
            taskset=TaskSet(
                id="smoke",
                benchmark="miniwob",
                tasks=[
                    TaskSpec(
                        env_id="browsergym/miniwob.click-button",
                        seed=1,
                        max_steps=10,
                    )
                ],
            ),
            adapter="agentlab",
        )

    assert calls == [
        (
            "baseline",
            "browsergym/miniwob.click-button#seed=1",
            "exp_baseline_smoke",
        )
    ]


def test_agentlab_task_name_normalization() -> None:
    assert _task_name_from_env_id("browsergym/miniwob.click-test") == "miniwob.click-test"
    assert _task_name_from_env_id("miniwob.click-test") == "miniwob.click-test"


def test_agentlab_api_key_mapping() -> None:
    assert _required_api_key_env("openai/gpt-4o-mini-2024-07-18") == "OPENAI_API_KEY"
    assert _required_api_key_env("azure/gpt-4o-mini-2024-07-18") == "AZURE_OPENAI_API_KEY"
    assert _required_api_key_env("anthropic/claude-3-7-sonnet-20250219") == "ANTHROPIC_API_KEY"
    assert _required_api_key_env("openrouter/openai/gpt-5-mini") == "OPENROUTER_API_KEY"
    assert _required_api_key_env("test/cheat_miniwob_click_test") is None


def test_agentlab_retry_policy_maps_to_attempt_count() -> None:
    assert (
        _agentlab_retry_attempts(
            AgentConfig(
                id="baseline",
                model="gpt-4o-mini",
                max_steps=15,
                retry_policy=RetryPolicy(enabled=False, max_retries=0),
            )
        )
        == 1
    )
    assert (
        _agentlab_retry_attempts(
            AgentConfig(
                id="retry_disabled_ignores_budget",
                model="gpt-4o-mini",
                max_steps=15,
                retry_policy=RetryPolicy(enabled=False, max_retries=3),
            )
        )
        == 1
    )
    assert (
        _agentlab_retry_attempts(
            AgentConfig(
                id="one_retry",
                model="gpt-4o-mini",
                max_steps=15,
                retry_policy=RetryPolicy(enabled=True, max_retries=1),
            )
        )
        == 2
    )


def test_agentlab_relay_config_requires_configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OHFI_API_KEY", raising=False)

    with pytest.raises(AgentLabAdapterUnavailable, match="OHFI_API_KEY"):
        _preflight_config_credentials(
            AgentConfig(
                id="relay",
                model="gpt-5.4",
                api_base_url="https://api.ai.ohfi.com.cn/v1",
                api_key_env="OHFI_API_KEY",
                max_steps=3,
            )
        )


def test_openai_compatible_model_args_is_picklable() -> None:
    args = OpenAICompatibleModelArgs(
        model_name="gpt-5.4",
        base_url="https://api.ai.ohfi.com.cn/v1",
        api_key_env="OHFI_API_KEY",
    )

    loaded = pickle.loads(pickle.dumps(args))

    assert loaded.model_name == "gpt-5.4"
    assert loaded.base_url == "https://api.ai.ohfi.com.cn/v1"


def test_agentlab_summary_normalization() -> None:
    record = _run_record_from_summary(
        config=AgentConfig(id="agentlab_cheat", model="test/cheat_miniwob_click_test", max_steps=3),
        task=TaskSpec(env_id="browsergym/miniwob.click-test", seed=1, max_steps=3),
        experiment_id="exp_test",
        summary={
            "n_steps": 1,
            "cum_reward": 1.0,
            "err_msg": None,
            "terminated": True,
            "truncated": False,
            "stats.cum_step_elapsed": 0.5,
            "stats.cum_agent_elapsed": 1.5,
        },
    )

    assert record.status == "success"
    assert record.normalized_score == 1.0
    assert record.latency_sec == 2.0


def probe_modules_report_ready(ready: bool) -> EnvironmentReport:
    return EnvironmentReport(
        adapter="agentlab",
        ready=ready,
        dependencies=[
            DependencyProbe(
                module="agentlab",
                available=ready,
                note=None if ready else "module import spec not found",
            )
        ],
    )


class FakePlaywrightContext:
    def __init__(self, executable_path: str) -> None:
        self.chromium = type("FakeChromium", (), {"executable_path": executable_path})()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None
