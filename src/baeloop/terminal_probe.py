from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel


class TerminalState(BaseModel):
    active_input: str = ""
    input_value: str = ""
    lines: list[str] = []
    done: bool = False
    reward: float = 0.0
    raw_reward: float = 0.0


class TerminalProbeResult(BaseModel):
    name: str
    actions: list[str]
    action_errors: list[str]
    initial_state: TerminalState
    final_state: TerminalState
    command_visible: bool
    terminal_changed: bool
    reward: float
    terminated: bool


class TerminalOracleResult(BaseModel):
    target_extension: str | None
    target_file: str | None
    actions: list[str]
    action_errors: list[str]
    listed_state: TerminalState
    final_state: TerminalState
    reward: float
    terminated: bool


class TerminalProbeReport(BaseModel):
    task_name: str
    seed: int
    base_url: str
    results: list[TerminalProbeResult]
    oracle_result: TerminalOracleResult | None = None

    @property
    def working_results(self) -> list[TerminalProbeResult]:
        return [
            result
            for result in self.results
            if not any(result.action_errors)
            and (result.command_visible or result.reward > 0)
        ]


DEFAULT_TERMINAL_PROBES: dict[str, list[str]] = {
    "fill_press": [
        'fill("25", "ls *.gpg")',
        'press("25", "Enter")',
    ],
    "focus_keyboard_type_enter": [
        'focus("25")',
        'keyboard_type("ls *.gpg")',
        'keyboard_press("Enter")',
    ],
    "click_input_keyboard_type_enter": [
        'click("25")',
        'keyboard_type("ls *.gpg")',
        'keyboard_press("Enter")',
    ],
    "click_terminal_keyboard_type_enter": [
        'click("14")',
        'keyboard_type("ls *.gpg")',
        'keyboard_press("Enter")',
    ],
    "mouse_click_keyboard_type_enter": [
        "mouse_click(75, 180)",
        'keyboard_type("ls *.gpg")',
        'keyboard_press("Enter")',
    ],
    "keyboard_type_enter_no_focus": [
        'keyboard_type("ls *.gpg")',
        'keyboard_press("Enter")',
    ],
}


def run_terminal_probe(
    *,
    seed: int = 27,
    base_url: str | None = None,
    task_name: str = "browsergym/miniwob.terminal",
) -> TerminalProbeReport:
    base_url = base_url or resolve_miniwob_url()

    import browsergym.miniwob  # noqa: F401
    import gymnasium as gym
    from browsergym.core.action.highlevel import HighLevelActionSet

    os.environ["MINIWOB_URL"] = base_url
    action_mapping = HighLevelActionSet(["bid", "coord"]).to_python_code
    results: list[TerminalProbeResult] = []
    for name, actions in DEFAULT_TERMINAL_PROBES.items():
        env = gym.make(
            task_name,
            headless=True,
            task_kwargs={"episode_max_time": 1000000},
            action_mapping=action_mapping,
        )
        try:
            _obs, _info = env.reset(seed=seed)
            initial_state = _extract_terminal_state(env)
            action_errors: list[str] = []
            reward = 0.0
            terminated = False
            obs = {}
            for action in actions:
                obs, reward, terminated, _truncated, _info = env.step(action)
                action_errors.append(str(obs.get("last_action_error", "")))
            final_state = _extract_terminal_state(env)
            results.append(
                TerminalProbeResult(
                    name=name,
                    actions=actions,
                    action_errors=action_errors,
                    initial_state=initial_state,
                    final_state=final_state,
                    command_visible=_command_visible(final_state, "ls *.gpg"),
                    terminal_changed=_terminal_changed(initial_state, final_state),
                    reward=float(reward),
                    terminated=bool(terminated),
                )
            )
        finally:
            env.close()

    return TerminalProbeReport(
        task_name=task_name,
        seed=seed,
        base_url=base_url,
        results=results,
        oracle_result=_run_terminal_oracle(
            gym=gym,
            task_name=task_name,
            seed=seed,
            action_mapping=action_mapping,
        ),
    )


def render_terminal_probe_markdown(report: TerminalProbeReport) -> str:
    lines = [
        "# Terminal Action Probe",
        "",
        f"- Task: `{report.task_name}`",
        f"- Seed: `{report.seed}`",
        f"- Base URL: `{report.base_url}`",
        f"- Working sequences: `{len(report.working_results)}`",
        "",
        "## Summary",
        "",
        "| Sequence | Errors | Command Visible | Terminal Changed | Reward | Terminated |",
        "|---|---:|---|---|---:|---|",
    ]
    for result in report.results:
        error_count = sum(1 for error in result.action_errors if error)
        lines.append(
            f"| `{result.name}` | {error_count} | {str(result.command_visible).lower()} | "
            f"{str(result.terminal_changed).lower()} | {result.reward:.2f} | "
            f"{str(result.terminated).lower()} |"
        )

    if report.oracle_result:
        oracle = report.oracle_result
        lines.extend(
            [
                "",
                "## Oracle Check",
                "",
                f"- Target extension: `{oracle.target_extension}`",
                f"- Target file: `{oracle.target_file}`",
                f"- Reward: `{oracle.reward:.2f}`",
                f"- Terminated: `{str(oracle.terminated).lower()}`",
                f"- Action errors: `{_compact_errors(oracle.action_errors)}`",
                f"- Listed terminal lines: `{_compact_lines(oracle.listed_state.lines)}`",
                f"- Final terminal lines: `{_compact_lines(oracle.final_state.lines)}`",
                "",
                "Actions:",
                "",
                *[f"- `{action}`" for action in oracle.actions],
                "",
            ]
        )

    lines.extend(["", "## Details", ""])
    for result in report.results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                "Actions:",
                "",
                *[f"- `{action}`" for action in result.actions],
                "",
                f"- Action errors: `{_compact_errors(result.action_errors)}`",
                f"- Initial terminal lines: `{_compact_lines(result.initial_state.lines)}`",
                f"- Final terminal lines: `{_compact_lines(result.final_state.lines)}`",
                f"- Final input value: `{result.final_state.input_value}`",
                f"- Final active input: `{result.final_state.active_input}`",
                "",
            ]
        )
    return "\n".join(lines)


def resolve_miniwob_url() -> str:
    if os.environ.get("MINIWOB_URL"):
        return os.environ["MINIWOB_URL"]

    candidate = Path.cwd() / "external" / "miniwob-plusplus" / "miniwob" / "html" / "miniwob"
    if candidate.exists():
        return f"file://{candidate.resolve()}/"

    raise ValueError(
        "MINIWOB_URL is not set and external/miniwob-plusplus/miniwob/html/miniwob was not found"
    )


def _extract_terminal_state(env) -> TerminalState:
    page = env.unwrapped.page
    payload = page.evaluate(
        """() => ({
  active_input: document.getElementById("active-input")?.textContent || "",
  input_value: document.getElementById("terminal-target")?.value || "",
  lines: Array.from(
    document.querySelectorAll("#terminal-contents .terminal-line, #terminal-contents .terminal-output")
  ).map((element) => element.innerText.replace(/\\s+/g, " ").trim()).filter(Boolean),
  done: Boolean(window.WOB_DONE_GLOBAL),
  reward: Number(window.WOB_REWARD_GLOBAL || 0),
  raw_reward: Number(window.WOB_RAW_REWARD_GLOBAL || 0),
})"""
    )
    return TerminalState.model_validate(payload)


def _run_terminal_oracle(*, gym, task_name: str, seed: int, action_mapping) -> TerminalOracleResult:
    env = gym.make(
        task_name,
        headless=True,
        task_kwargs={"episode_max_time": 1000000},
        action_mapping=action_mapping,
    )
    actions = [
        'focus("25")',
        'keyboard_type("ls")',
        'keyboard_press("Enter")',
    ]
    action_errors: list[str] = []
    reward = 0.0
    terminated = False
    target_extension: str | None = None
    target_file: str | None = None
    try:
        obs, _info = env.reset(seed=seed)
        target_extension = _target_extension(obs.get("goal", ""))
        for action in actions:
            obs, reward, terminated, _truncated, _info = env.step(action)
            action_errors.append(str(obs.get("last_action_error", "")))
        listed_state = _extract_terminal_state(env)
        target_file = _select_target_file(_files_from_lines(listed_state.lines), target_extension)
        if target_file:
            rm_actions = [
                'focus("25")',
                f'keyboard_type("rm {target_file}")',
                'keyboard_press("Enter")',
            ]
            actions.extend(rm_actions)
            for action in rm_actions:
                obs, reward, terminated, _truncated, _info = env.step(action)
                action_errors.append(str(obs.get("last_action_error", "")))
        final_state = _extract_terminal_state(env)
    finally:
        env.close()

    return TerminalOracleResult(
        target_extension=target_extension,
        target_file=target_file,
        actions=actions,
        action_errors=action_errors,
        listed_state=listed_state,
        final_state=final_state,
        reward=float(reward),
        terminated=bool(terminated),
    )


def _target_extension(goal: str) -> str | None:
    marker = "ending with the extension ."
    if marker in goal:
        return "." + goal.split(marker, 1)[1].split()[0].strip().strip(".")
    if "no file extension" in goal:
        return ""
    return None


def _files_from_lines(lines: list[str]) -> list[str]:
    files: list[str] = []
    for line in lines:
        if line.startswith("user$") or line.startswith("error:"):
            continue
        if line.startswith("Welcome!") or line.startswith("Last login:"):
            continue
        files.extend(line.split())
    return files


def _select_target_file(files: list[str], target_extension: str | None) -> str | None:
    if target_extension is None:
        return None
    if target_extension == "":
        return next((file for file in files if "." not in file), None)
    return next((file for file in files if file.endswith(target_extension)), None)


def _command_visible(state: TerminalState, command: str) -> bool:
    return command in state.active_input or command in state.input_value or any(
        command in line for line in state.lines
    )


def _terminal_changed(initial: TerminalState, final: TerminalState) -> bool:
    return (
        initial.active_input != final.active_input
        or initial.input_value != final.input_value
        or initial.lines != final.lines
    )


def _compact_errors(errors: list[str]) -> str:
    meaningful_errors = [error for error in errors if error]
    return " | ".join(meaningful_errors) if meaningful_errors else "none"


def _compact_lines(lines: list[str]) -> str:
    return " | ".join(lines[-8:]) if lines else "none"
