from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import gzip
import json
import os
import pickle
from pathlib import Path
from typing import Any

from baeloop.action_policy import (
    SCROLL_BEFORE_SUBMIT,
    TERMINAL_KEYBOARD_TYPE,
    ActionPolicyState,
    apply_action_policy,
)
from baeloop.doctor import probe_agentlab_environment
from baeloop.models import ActionPolicyConfig, AgentConfig, RunRecord, TaskSpec


class AgentLabAdapterUnavailable(RuntimeError):
    """Raised when the AgentLab adapter cannot run in the current environment."""


@dataclass
class OpenAICompatibleModelArgs:
    model_name: str
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    max_total_tokens: int | None = 128000
    max_input_tokens: int | None = 128000
    max_new_tokens: int | None = 16384
    temperature: float = 0.1
    vision_support: bool = True
    log_probs: bool = False

    def make_model(self):
        from agentlab.llm.chat_api import ChatModel
        from openai import OpenAI

        return ChatModel(
            model_name=self.model_name,
            api_key=os.environ[self.api_key_env],
            temperature=self.temperature,
            max_tokens=self.max_new_tokens,
            client_class=OpenAI,
            client_args={"base_url": self.base_url} if self.base_url else None,
            log_probs=self.log_probs,
        )

    def prepare_server(self):
        pass

    def close_server(self):
        pass


@dataclass
class PolicyWrappedAgentArgs:
    base_agent_args: Any
    action_policy: ActionPolicyConfig

    def __post_init__(self):
        self.agent_name = f"{self.base_agent_args.agent_name}-{self.action_policy.name}"

    def make_agent(self):
        return PolicyWrappedAgent(
            base_agent=self.base_agent_args.make_agent(),
            action_policy=self.action_policy,
        )

    def prepare(self):
        if hasattr(self.base_agent_args, "prepare"):
            return self.base_agent_args.prepare()
        return None

    def close(self):
        if hasattr(self.base_agent_args, "close"):
            return self.base_agent_args.close()
        return None


class PolicyWrappedAgent:
    def __init__(self, base_agent: Any, action_policy: ActionPolicyConfig):
        self.base_agent = base_agent
        self.action_policy = action_policy
        self.policy_state = ActionPolicyState()
        if action_policy.name == TERMINAL_KEYBOARD_TYPE:
            self.action_set = _terminal_policy_action_set()

    def __getattr__(self, name: str):
        return getattr(self.base_agent, name)

    def obs_preprocessor(self, obs: dict) -> dict:
        return self.base_agent.obs_preprocessor(obs)

    def reset(self, seed=None):
        self.policy_state.reset()
        return self.base_agent.reset(seed=seed)

    def get_action(self, obs):
        action, agent_info = self.base_agent.get_action(obs)
        decision = apply_action_policy(
            action=action,
            obs=obs,
            policy=self.action_policy,
            state=self.policy_state,
        )
        if decision.applied:
            self._replace_last_base_action(decision.action)
            self._annotate_agent_info(agent_info, decision)
            return decision.action, agent_info

        self._annotate_agent_info(agent_info, decision)
        return action, agent_info

    def _replace_last_base_action(self, action: str | None) -> None:
        actions = getattr(self.base_agent, "actions", None)
        if isinstance(actions, list) and actions:
            actions[-1] = action

    def _annotate_agent_info(self, agent_info, decision) -> None:
        if getattr(agent_info, "extra_info", None) is None:
            agent_info.extra_info = {}
        agent_info.extra_info["action_policy_applied"] = decision.applied
        if decision.applied:
            agent_info.extra_info.update(
                {
                    "action_policy_name": decision.policy_name,
                    "action_policy_original_action": decision.original_action,
                    "action_policy_rewritten_action": decision.action,
                    "action_policy_reason": decision.reason,
                }
            )


MODEL_KEY_ALIASES = {
    "gpt-4o-mini": "openai/gpt-4o-mini-2024-07-18",
    "gpt-4o-mini-2024-07-18": "openai/gpt-4o-mini-2024-07-18",
    "gpt-5-mini": "openai/gpt-5-mini-2025-08-07",
    "gpt-5-mini-2025-08-07": "openai/gpt-5-mini-2025-08-07",
}


def run_agentlab_task(config: AgentConfig, task: TaskSpec, experiment_id: str) -> RunRecord:
    environment = probe_agentlab_environment(check_playwright_browser=False)
    if not environment.ready:
        missing = [
            dependency.module
            for dependency in environment.dependencies
            if not dependency.available
        ]
        raise AgentLabAdapterUnavailable(
            "AgentLab adapter is not ready. Missing modules: "
            f"{', '.join(missing)}. Run `baeloop doctor --adapter agentlab` "
            "and install the required AgentLab/BrowserGym dependencies before using this adapter."
        )

    _preflight_config_credentials(config)

    from browsergym.experiments.loop import EnvArgs, ExpArgs

    agent_args = _make_generic_agent_args(config)
    env_args = EnvArgs(
        task_name=_task_name_from_env_id(task.env_id),
        task_seed=task.seed,
        max_steps=min(config.max_steps, task.max_steps),
        headless=True,
    )
    exp_args = ExpArgs(
        agent_args=agent_args,
        env_args=env_args,
        save_screenshot=False,
    )
    exp_args.prepare(_trace_root())
    exp_args.run()

    summary = json.loads((Path(exp_args.exp_dir) / "summary_info.json").read_text())
    return _run_record_from_summary(
        config=config,
        task=task,
        experiment_id=experiment_id,
        summary=summary,
        exp_dir=Path(exp_args.exp_dir),
    )


def _make_generic_agent_args(config: AgentConfig):
    from agentlab.agents.generic_agent import AGENT_4o_MINI, CHAT_MODEL_ARGS_DICT, GenericAgentArgs
    from agentlab.llm.chat_api import CheatMiniWoBLLMArgs

    flags = deepcopy(AGENT_4o_MINI.flags)
    max_retry = _agentlab_retry_attempts(config)
    if config.observation_mode == "html":
        flags.obs.use_html = True
    if _is_cheat_model(config.model):
        flags.obs.use_html = True
        return _maybe_wrap_agent_args(
            GenericAgentArgs(
                agent_name="GenericAgent-cheat-miniwob",
                chat_model_args=CheatMiniWoBLLMArgs(),
                flags=flags,
                max_retry=max_retry,
            ),
            config,
        )

    if config.api_base_url:
        return _maybe_wrap_agent_args(
            GenericAgentArgs(
                chat_model_args=OpenAICompatibleModelArgs(
                    model_name=config.model,
                    base_url=config.api_base_url,
                    api_key_env=config.api_key_env or "OPENAI_API_KEY",
                    max_total_tokens=128000,
                    max_input_tokens=128000,
                    max_new_tokens=16384,
                    temperature=0.1,
                    vision_support=True,
                ),
                flags=flags,
                max_retry=max_retry,
            ),
            config,
        )

    model_key = MODEL_KEY_ALIASES.get(config.model, config.model)
    if model_key not in CHAT_MODEL_ARGS_DICT:
        raise AgentLabAdapterUnavailable(
            f"Unsupported AgentLab model `{config.model}`. Use one of the AgentLab "
            "CHAT_MODEL_ARGS_DICT keys or a known alias such as `gpt-4o-mini`."
        )
    return _maybe_wrap_agent_args(
        GenericAgentArgs(
            chat_model_args=deepcopy(CHAT_MODEL_ARGS_DICT[model_key]),
            flags=flags,
            max_retry=max_retry,
        ),
        config,
    )


def _maybe_wrap_agent_args(agent_args, config: AgentConfig):
    if not config.action_policy.enabled:
        return agent_args
    if config.action_policy.name not in {SCROLL_BEFORE_SUBMIT, TERMINAL_KEYBOARD_TYPE}:
        raise AgentLabAdapterUnavailable(
            f"Unsupported action policy `{config.action_policy.name}`."
        )
    return PolicyWrappedAgentArgs(
        base_agent_args=agent_args,
        action_policy=config.action_policy,
    )


def _terminal_policy_action_set():
    from browsergym.core.action.highlevel import HighLevelActionSet

    return HighLevelActionSet(["bid", "coord"], multiaction=True)


def _agentlab_retry_attempts(config: AgentConfig) -> int:
    # AgentLab's `n_retry` loop counts the initial model call as one attempt.
    if not config.retry_policy.enabled:
        return 1
    return 1 + config.retry_policy.max_retries


def _preflight_model_credentials(model: str) -> None:
    if _is_cheat_model(model):
        return

    model_key = MODEL_KEY_ALIASES.get(model, model)
    required_env = _required_api_key_env(model_key)
    if required_env and not os.environ.get(required_env):
        raise AgentLabAdapterUnavailable(
            f"AgentLab model `{model}` requires `{required_env}` to be set."
        )


def _preflight_config_credentials(config: AgentConfig) -> None:
    if _is_cheat_model(config.model):
        return
    if config.api_base_url:
        required_env = config.api_key_env or "OPENAI_API_KEY"
        if not os.environ.get(required_env):
            raise AgentLabAdapterUnavailable(
                f"AgentLab model `{config.model}` uses `{config.api_base_url}` and requires "
                f"`{required_env}` to be set."
            )
        return
    _preflight_model_credentials(config.model)


def _required_api_key_env(model_key: str) -> str | None:
    if model_key.startswith("openai/"):
        return "OPENAI_API_KEY"
    if model_key.startswith("azure/"):
        return "AZURE_OPENAI_API_KEY"
    if model_key.startswith("anthropic/"):
        return "ANTHROPIC_API_KEY"
    if model_key.startswith("openrouter/"):
        return "OPENROUTER_API_KEY"
    return None


def _is_cheat_model(model: str) -> bool:
    return model == "test/cheat_miniwob_click_test"


def _task_name_from_env_id(env_id: str) -> str:
    if env_id.startswith("browsergym/"):
        return env_id.removeprefix("browsergym/")
    return env_id


def _trace_root() -> Path:
    root = Path("runs/agentlab_traces")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _run_record_from_summary(
    config: AgentConfig,
    task: TaskSpec,
    experiment_id: str,
    summary: dict,
    exp_dir: Path | None = None,
) -> RunRecord:
    score = max(0.0, min(float(summary.get("cum_reward", 0.0)), 1.0))
    err_msg = summary.get("err_msg")
    status = _status_from_summary(score=score, summary=summary)
    latency = float(summary.get("stats.cum_step_elapsed", 0.0) or 0.0) + float(
        summary.get("stats.cum_agent_elapsed", 0.0) or 0.0
    )
    diagnostics = _diagnostics_from_summary(summary)
    if exp_dir:
        diagnostics.update(_action_policy_diagnostics(exp_dir))
    return RunRecord(
        experiment_id=experiment_id,
        config_id=config.id,
        task_id=task.task_id,
        status=status,
        normalized_score=score,
        step_count=int(summary.get("n_steps", 0) or 0),
        latency_sec=latency,
        failure_type=_failure_type(status=status, error=err_msg),
        error=err_msg,
        diagnostics=diagnostics,
    )


def _diagnostics_from_summary(summary: dict) -> dict[str, int | float | str | bool]:
    keys = {
        "agent_retry_count": "stats.cum_n_retry",
        "agent_retry_max": "stats.max_n_retry",
        "busted_retry_count": "stats.cum_busted_retry",
        "busted_retry_max": "stats.max_busted_retry",
        "llm_call_count": "stats.cum_n_retry_llm",
        "llm_call_max": "stats.max_n_retry_llm",
        "input_tokens": "stats.cum_input_tokens",
        "output_tokens": "stats.cum_output_tokens",
    }
    diagnostics: dict[str, int | float | str | bool] = {}
    for name, summary_key in keys.items():
        value = summary.get(summary_key)
        if isinstance(value, int | float | str | bool):
            diagnostics[name] = value
    return diagnostics


def _action_policy_diagnostics(exp_dir: Path) -> dict[str, int | str]:
    interventions = 0
    policy_name: str | None = None
    for step_file in sorted(exp_dir.glob("step_*.pkl.gz")):
        try:
            with gzip.open(step_file, "rb") as handle:
                step_info = pickle.load(handle)
        except Exception:
            continue
        agent_info = getattr(step_info, "agent_info", None)
        extra_info = getattr(agent_info, "extra_info", None)
        if not isinstance(extra_info, dict):
            continue
        if extra_info.get("action_policy_applied") is True:
            interventions += 1
            if isinstance(extra_info.get("action_policy_name"), str):
                policy_name = extra_info["action_policy_name"]

    diagnostics: dict[str, int | str] = {"action_policy_interventions": interventions}
    if policy_name:
        diagnostics["action_policy_name"] = policy_name
    return diagnostics


def _status_from_summary(score: float, summary: dict) -> str:
    if summary.get("err_msg"):
        return "error"
    if score >= 1.0:
        return "success"
    if summary.get("truncated"):
        return "max_steps"
    return "failed"


def _failure_type(status: str, error: str | None) -> str | None:
    if status == "success":
        return None
    if status == "error":
        return "exception" if error else "error"
    if status == "max_steps":
        return "max_steps"
    return "zero_score"
