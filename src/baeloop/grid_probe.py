from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel

from baeloop.terminal_probe import resolve_miniwob_url


class GridCoordinateState(BaseModel):
    goal: str = ""
    target_coordinate: tuple[int, int] | None = None
    svg_bid: str | None = None
    svg_bbox: list[float] | None = None
    svg_extent: list[float] | None = None
    target_svg_point: list[float] | None = None
    target_circle_bbox: list[float] | None = None
    target_click_point: list[int] | None = None
    done: bool = False
    reward: float = 0.0
    raw_reward: float = 0.0


class GridCoordinateProbeResult(BaseModel):
    name: str
    action: str
    action_error: str
    initial_state: GridCoordinateState
    final_state: GridCoordinateState
    reward: float
    terminated: bool


class GridCoordinateProbeReport(BaseModel):
    task_name: str
    seed: int
    base_url: str
    results: list[GridCoordinateProbeResult]

    @property
    def working_results(self) -> list[GridCoordinateProbeResult]:
        return [
            result
            for result in self.results
            if not result.action_error and result.reward > 0
        ]


def run_grid_coordinate_probe(
    *,
    seed: int = 25,
    base_url: str | None = None,
    task_name: str = "browsergym/miniwob.grid-coordinate",
) -> GridCoordinateProbeReport:
    base_url = base_url or resolve_miniwob_url()

    import browsergym.miniwob  # noqa: F401
    import gymnasium as gym
    from browsergym.core.action.highlevel import HighLevelActionSet

    os.environ["MINIWOB_URL"] = base_url
    action_mapping = HighLevelActionSet(["bid", "coord"]).to_python_code
    results: list[GridCoordinateProbeResult] = []

    for name in ("svg_root_bid_click", "mapped_mouse_click", "circle_center_mouse_click"):
        env = gym.make(
            task_name,
            headless=True,
            task_kwargs={"episode_max_time": 1000000},
            action_mapping=action_mapping,
        )
        try:
            obs, _info = env.reset(seed=seed)
            initial_state = _extract_grid_state(env, obs)
            action = _probe_action(name, initial_state)
            stepped_obs, reward, terminated, _truncated, _info = env.step(action)
            final_state = _extract_grid_state(env, stepped_obs, fallback_goal=initial_state.goal)
            results.append(
                GridCoordinateProbeResult(
                    name=name,
                    action=action,
                    action_error=str(stepped_obs.get("last_action_error", "")),
                    initial_state=initial_state,
                    final_state=final_state,
                    reward=float(reward),
                    terminated=bool(terminated),
                )
            )
        finally:
            env.close()

    return GridCoordinateProbeReport(
        task_name=task_name,
        seed=seed,
        base_url=base_url,
        results=results,
    )


def render_grid_coordinate_probe_markdown(report: GridCoordinateProbeReport) -> str:
    lines = [
        "# Grid Coordinate Action Probe",
        "",
        f"- Task: `{report.task_name}`",
        f"- Seed: `{report.seed}`",
        f"- Base URL: `{report.base_url}`",
        f"- Working sequences: `{len(report.working_results)}`",
        "",
        "## Summary",
        "",
        "| Sequence | Action | Error | Reward | Terminated | Target | Click Point |",
        "|---|---|---|---:|---|---|---|",
    ]
    for result in report.results:
        state = result.initial_state
        lines.append(
            f"| `{result.name}` | `{result.action}` | `{result.action_error or '-'}` | "
            f"{result.reward:.2f} | {str(result.terminated).lower()} | "
            f"`{state.target_coordinate}` | `{state.target_click_point}` |"
        )

    if report.results:
        state = report.results[0].initial_state
        lines.extend(
            [
                "",
                "## Initial Geometry",
                "",
                f"- Goal: `{state.goal}`",
                f"- SVG bid: `{state.svg_bid}`",
                f"- SVG bbox: `{state.svg_bbox}`",
                f"- SVG extent: `{state.svg_extent}`",
                f"- Target SVG point: `{state.target_svg_point}`",
                f"- Target circle bbox: `{state.target_circle_bbox}`",
                f"- Mapped click point: `{state.target_click_point}`",
            ]
        )
    return "\n".join(lines)


def map_svg_point_to_screen(
    *,
    svg_point: list[float],
    svg_extent: list[float],
    svg_bbox: list[float],
    bbox_scale: float = 1.0,
) -> list[int] | None:
    min_x, min_y, width, height = svg_extent
    bbox_x, bbox_y, bbox_width, bbox_height = [
        value / bbox_scale for value in svg_bbox
    ]
    if width <= 0 or height <= 0:
        return None
    return [
        round(bbox_x + (svg_point[0] - min_x) * bbox_width / width),
        round(bbox_y + (svg_point[1] - min_y) * bbox_height / height),
    ]


def _extract_grid_state(
    env,
    obs: dict,
    fallback_goal: str = "",
) -> GridCoordinateState:
    goal = _goal_text(obs) or fallback_goal
    target = _target_grid_coordinate(goal)
    html = _observation_text(obs, "pruned_html")
    svg_bid = _first_svg_bid(html)
    svg_bbox = _element_bbox(obs, svg_bid) if svg_bid else None
    svg_extent = _svg_extent(html, svg_bid) if svg_bid else None
    target_svg_point = _circle_svg_point(html, target) if target else None
    payload = env.unwrapped.page.evaluate(
        """(targetId) => {
  const svg = document.querySelector("svg");
  const target = svg && targetId ? svg.querySelector(`circle[id="${targetId}"]`) : null;
  const svgBox = svg ? svg.getBoundingClientRect() : null;
  const targetBox = target ? target.getBoundingClientRect() : null;
  const numbers = (elements, names) => Array.from(elements).flatMap((element) =>
    names.map((name) => Number(element.getAttribute(name))).filter(Number.isFinite)
  );
  const xValues = svg ? numbers(svg.querySelectorAll("line,circle"), ["x1", "x2", "cx"]) : [];
  const yValues = svg ? numbers(svg.querySelectorAll("line,circle"), ["y1", "y2", "cy"]) : [];
  const minX = xValues.length ? Math.min(0, ...xValues) : null;
  const minY = yValues.length ? Math.min(0, ...yValues) : null;
  const maxX = xValues.length ? Math.max(...xValues) : null;
  const maxY = yValues.length ? Math.max(...yValues) : null;
  return {
    svg_bid: svg ? svg.getAttribute("bid") : null,
    svg_bbox: svgBox ? [svgBox.x, svgBox.y, svgBox.width, svgBox.height] : null,
    svg_extent: minX === null || minY === null ? null : [minX, minY, maxX - minX, maxY - minY],
    target_svg_point: target ? [Number(target.getAttribute("cx")), Number(target.getAttribute("cy"))] : null,
    target_circle_bbox: targetBox ? [targetBox.x, targetBox.y, targetBox.width, targetBox.height] : null,
    done: Boolean(window.WOB_DONE_GLOBAL),
    reward: Number(window.WOB_REWARD_GLOBAL || 0),
    raw_reward: Number(window.WOB_RAW_REWARD_GLOBAL || 0),
  };
}""",
        _target_id(target) if target else None,
    )
    state = GridCoordinateState.model_validate(
        {
            "goal": goal,
            "target_coordinate": target,
            **payload,
        }
    )
    if svg_bid:
        state.svg_bid = svg_bid
    obs_svg_bbox = _element_bbox(obs, state.svg_bid) if state.svg_bid else None
    if obs_svg_bbox:
        state.svg_bbox = obs_svg_bbox
    if svg_bbox:
        state.svg_bbox = svg_bbox
    if svg_extent:
        state.svg_extent = svg_extent
    if target_svg_point:
        state.target_svg_point = target_svg_point
    if state.target_svg_point and state.svg_extent and state.svg_bbox:
        state.target_click_point = map_svg_point_to_screen(
            svg_point=state.target_svg_point,
            svg_extent=state.svg_extent,
            svg_bbox=state.svg_bbox,
            bbox_scale=_bbox_coordinate_scale(obs),
        )
    return state


def _probe_action(name: str, state: GridCoordinateState) -> str:
    if name == "svg_root_bid_click" and state.svg_bid:
        return f'click("{state.svg_bid}")'
    if name == "mapped_mouse_click" and state.target_click_point:
        return f"mouse_click({state.target_click_point[0]}, {state.target_click_point[1]})"
    if name == "circle_center_mouse_click" and state.target_circle_bbox:
        x, y, width, height = state.target_circle_bbox
        return f"mouse_click({round(x + width / 2)}, {round(y + height / 2)})"
    return "noop()"


def _goal_text(obs: dict) -> str:
    value = obs.get("goal")
    return value if isinstance(value, str) else ""


def _observation_text(obs: dict, key: str) -> str:
    value = obs.get(key)
    return value if isinstance(value, str) else ""


def _target_grid_coordinate(goal: str) -> tuple[int, int] | None:
    match = re.search(r"grid coordinate\s*\((-?\d+)\s*,\s*(-?\d+)\)", goal)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _target_id(target: tuple[int, int]) -> str:
    return f"({target[0]},{target[1]})"


def _first_svg_bid(html: str) -> str | None:
    match = re.search(r"<svg[^>]*\bbid=\"([^\"]+)\"", html)
    return match.group(1) if match else None


def _circle_svg_point(html: str, coordinate: tuple[int, int]) -> list[float] | None:
    escaped_coordinate = re.escape(_target_id(coordinate))
    circle_match = re.search(
        rf"<circle\b[^>]*\bid=\"{escaped_coordinate}\"[^>]*>",
        html,
        flags=re.DOTALL,
    )
    if not circle_match:
        return None
    tag = circle_match.group(0)
    cx = _float_attr(tag, "cx")
    cy = _float_attr(tag, "cy")
    if cx is None or cy is None:
        return None
    return [cx, cy]


def _svg_extent(html: str, svg_bid: str) -> list[float] | None:
    svg_match = re.search(
        rf"<svg\b[^>]*\bbid=\"{re.escape(svg_bid)}\"[^>]*>(.*?)</svg>",
        html,
        flags=re.DOTALL,
    )
    if not svg_match:
        return None
    svg = svg_match.group(1)
    x_values = _float_attrs(svg, ("x1", "x2", "cx"))
    y_values = _float_attrs(svg, ("y1", "y2", "cy"))
    if not x_values or not y_values:
        return None
    min_x = min(0.0, *x_values)
    min_y = min(0.0, *y_values)
    return [min_x, min_y, max(x_values) - min_x, max(y_values) - min_y]


def _element_bbox(obs: dict, bid: str) -> list[float] | None:
    properties = obs.get("extra_element_properties")
    if not isinstance(properties, dict):
        return None
    element = properties.get(bid)
    if not isinstance(element, dict):
        return None
    bbox = element.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        return [float(value) for value in bbox]
    except (TypeError, ValueError):
        return None


def _bbox_coordinate_scale(obs: dict) -> float:
    screenshot = obs.get("screenshot")
    root_bbox = _element_bbox(obs, "0")
    shape = getattr(screenshot, "shape", None)
    if root_bbox and isinstance(shape, tuple) and len(shape) >= 2 and shape[1]:
        return max(root_bbox[2] / float(shape[1]), 1.0)
    return 2.0


def _float_attrs(source: str, names: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for name in names:
        values.extend(
            float(match.group(1))
            for match in re.finditer(rf"\b{name}=\"(-?\d+(?:\.\d+)?)\"", source)
        )
    return values


def _float_attr(source: str, name: str) -> float | None:
    match = re.search(rf"\b{name}=\"(-?\d+(?:\.\d+)?)\"", source)
    return float(match.group(1)) if match else None


def default_grid_report_path() -> Path:
    return Path("reports/agentlab_grid_coordinate_probe.json")
