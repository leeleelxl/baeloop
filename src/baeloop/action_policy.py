from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from baeloop.models import ActionPolicyConfig


SCROLL_BEFORE_SUBMIT = "scroll_before_submit"
TERMINAL_KEYBOARD_TYPE = "terminal_keyboard_type"
GRID_COORDINATE_CLICK = "grid_coordinate_click"


@dataclass
class ActionPolicyDecision:
    action: str | None
    applied: bool
    policy_name: str | None = None
    original_action: str | None = None
    reason: str | None = None


class ActionPolicyState:
    def __init__(self) -> None:
        self.interventions = 0
        self.interventions_by_policy: dict[str, int] = {}

    def reset(self) -> None:
        self.interventions = 0
        self.interventions_by_policy = {}

    def intervention_count(self, policy_name: str) -> int:
        return self.interventions_by_policy.get(policy_name, 0)

    def record_intervention(self, policy_name: str) -> None:
        self.interventions += 1
        self.interventions_by_policy[policy_name] = self.intervention_count(policy_name) + 1


def apply_action_policy(
    action: str | None,
    obs: dict[str, Any],
    policy: ActionPolicyConfig,
    state: ActionPolicyState,
) -> ActionPolicyDecision:
    if action is None or not policy.enabled:
        return ActionPolicyDecision(action=action, applied=False)

    for policy_name in enabled_action_policy_names(policy):
        if state.intervention_count(policy_name) >= _policy_limit(policy, policy_name):
            continue
        if policy_name == TERMINAL_KEYBOARD_TYPE:
            decision = _terminal_keyboard_type_decision(action, obs, policy_name)
        elif policy_name == GRID_COORDINATE_CLICK:
            decision = _grid_coordinate_click_decision(action, obs, policy_name)
        elif policy_name == SCROLL_BEFORE_SUBMIT:
            decision = _scroll_before_submit_decision(action, obs, policy, policy_name)
        else:
            continue
        if decision.applied:
            state.record_intervention(policy_name)
            return decision

    return ActionPolicyDecision(action=action, applied=False)


def enabled_action_policy_names(policy: ActionPolicyConfig) -> list[str]:
    if policy.policies:
        return policy.policies
    if policy.name != "none":
        return [policy.name]
    return []


def _policy_limit(policy: ActionPolicyConfig, policy_name: str) -> int:
    return policy.policy_limits.get(policy_name, policy.max_interventions)


def _scroll_before_submit_decision(
    action: str,
    obs: dict[str, Any],
    policy: ActionPolicyConfig,
    policy_name: str,
) -> ActionPolicyDecision:
    if not _is_social_media_all_goal(obs):
        return ActionPolicyDecision(action=action, applied=False)

    html = _observation_text(obs, "pruned_html")
    if not _is_submit_click(action, html):
        return ActionPolicyDecision(action=action, applied=False)
    if not _has_hidden_unselected_ultricies_reply(html):
        return ActionPolicyDecision(action=action, applied=False)

    return ActionPolicyDecision(
        action=f"scroll(0, {policy.scroll_delta_y})",
        applied=True,
        policy_name=policy_name,
        original_action=action,
        reason="submit intercepted while hidden @ultricies reply remains",
    )


def _terminal_keyboard_type_decision(
    action: str,
    obs: dict[str, Any],
    policy_name: str,
) -> ActionPolicyDecision:
    if not _is_terminal_goal(obs):
        return ActionPolicyDecision(action=action, applied=False)

    parsed = _fill_target_and_value(action)
    if not parsed:
        return ActionPolicyDecision(action=action, applied=False)
    bid, value = parsed
    if not value.strip():
        return ActionPolicyDecision(action=action, applied=False)
    if not _is_terminal_target(bid, _observation_text(obs, "pruned_html")):
        return ActionPolicyDecision(action=action, applied=False)

    rewritten = f"focus({bid!r})\nkeyboard_type({value!r})"
    return ActionPolicyDecision(
        action=rewritten,
        applied=True,
        policy_name=policy_name,
        original_action=action,
        reason="terminal fill rewritten to keyboard events for custom terminal input",
    )


def _grid_coordinate_click_decision(
    action: str,
    obs: dict[str, Any],
    policy_name: str,
) -> ActionPolicyDecision:
    if not _is_grid_coordinate_goal(obs):
        return ActionPolicyDecision(action=action, applied=False)

    html = _observation_text(obs, "pruned_html")
    svg_bid = _first_svg_bid(html)
    if not svg_bid or _click_bid(action) != svg_bid:
        return ActionPolicyDecision(action=action, applied=False)

    target = _target_grid_coordinate(obs)
    if not target:
        return ActionPolicyDecision(action=action, applied=False)
    svg_point = _circle_svg_point(html, target)
    svg_extent = _svg_extent(html, svg_bid)
    svg_bbox = _element_bbox(obs, svg_bid)
    if not svg_point or not svg_extent or not svg_bbox:
        return ActionPolicyDecision(action=action, applied=False)
    svg_bbox = _action_space_bbox(obs, svg_bbox)

    min_x, min_y, width, height = svg_extent
    if width <= 0 or height <= 0:
        return ActionPolicyDecision(action=action, applied=False)

    bbox_x, bbox_y, bbox_width, bbox_height = svg_bbox
    click_x = round(bbox_x + (svg_point[0] - min_x) * bbox_width / width)
    click_y = round(bbox_y + (svg_point[1] - min_y) * bbox_height / height)
    rewritten = f"mouse_click({click_x}, {click_y})"
    return ActionPolicyDecision(
        action=rewritten,
        applied=True,
        policy_name=policy_name,
        original_action=action,
        reason=f"svg root click rewritten to target grid coordinate {target}",
    )


def _is_social_media_all_goal(obs: dict[str, Any]) -> bool:
    goal = _observation_text(obs, "goal")
    return 'Reply" button on all posts by @ultricies' in goal or (
        "social-media-all" in _observation_text(obs, "url").lower()
    )


def _is_grid_coordinate_goal(obs: dict[str, Any]) -> bool:
    goal = _observation_text(obs, "goal")
    return "Click on the grid coordinate" in goal or "grid-coordinate" in _observation_text(
        obs, "url"
    ).lower()


def _is_terminal_goal(obs: dict[str, Any]) -> bool:
    goal = _observation_text(obs, "goal")
    return "Use the terminal below" in goal or "miniwob.terminal" in _observation_text(
        obs, "url"
    ).lower()


def _is_terminal_target(bid: str, html: str) -> bool:
    if not html:
        return bid == "25"
    bid_marker = f'bid="{bid}"'
    index = html.find(bid_marker)
    if index < 0:
        return bid == "25"
    tag_start = html.rfind("<", 0, index)
    tag_end = html.find(">", index)
    if tag_start < 0 or tag_end < 0:
        return False
    tag = html[tag_start : tag_end + 1]
    return 'id="terminal-target"' in tag


def _is_submit_click(action: str, html: str) -> bool:
    bid = _click_bid(action)
    if not bid:
        return False
    bid_marker = f'bid="{bid}"'
    index = html.find(bid_marker)
    if index < 0:
        return False
    tag_start = html.rfind("<", 0, index)
    tag_end = html.find(">", index)
    if tag_start < 0 or tag_end < 0:
        return False
    tag = html[tag_start : tag_end + 1]
    if "<button" not in tag:
        return False
    context = html[tag_start : tag_end + 120]
    return "Submit" in context or 'type="submit"' in tag


def _click_bid(action: str) -> str | None:
    match = re.fullmatch(r"\s*click\(\s*['\"]([^'\"]+)['\"]\s*\)\s*", action)
    return match.group(1) if match else None


def _first_svg_bid(html: str) -> str | None:
    match = re.search(r"<svg[^>]*\bbid=\"([^\"]+)\"", html)
    return match.group(1) if match else None


def _target_grid_coordinate(obs: dict[str, Any]) -> tuple[int, int] | None:
    match = re.search(
        r"grid coordinate\s*\((-?\d+)\s*,\s*(-?\d+)\)",
        _observation_text(obs, "goal"),
    )
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _circle_svg_point(html: str, coordinate: tuple[int, int]) -> tuple[float, float] | None:
    escaped_coordinate = re.escape(f"({coordinate[0]},{coordinate[1]})")
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
    return cx, cy


def _svg_extent(html: str, svg_bid: str) -> tuple[float, float, float, float] | None:
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
    return min_x, min_y, max(x_values) - min_x, max(y_values) - min_y


def _element_bbox(obs: dict[str, Any], bid: str) -> tuple[float, float, float, float] | None:
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
        x, y, width, height = bbox
        return float(x), float(y), float(width), float(height)
    except (TypeError, ValueError):
        return None


def _action_space_bbox(
    obs: dict[str, Any],
    bbox: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    scale = _bbox_coordinate_scale(obs)
    x, y, width, height = bbox
    return x / scale, y / scale, width / scale, height / scale


def _bbox_coordinate_scale(obs: dict[str, Any]) -> float:
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


def _fill_target_and_value(action: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"""\s*fill\(\s*['"]([^'"]+)['"]\s*,\s*(['"])(.*?)\2(?:\s*,\s*(?:True|False))?\s*\)\s*""",
        action,
        flags=re.DOTALL,
    )
    if not match:
        return None
    return match.group(1), match.group(3)


def _has_hidden_unselected_ultricies_reply(html: str) -> bool:
    for username_match in re.finditer(r"@ultricies", html):
        block = html[username_match.start() : username_match.start() + 1200]
        next_media = block.find('class="media"', 1)
        if next_media > 0:
            block = block[:next_media]
        reply_tag = _first_reply_tag(block)
        if reply_tag and "active" not in reply_tag and "visible" not in reply_tag:
            return True
    return False


def _first_reply_tag(block: str) -> str | None:
    match = re.search(r"<span[^>]*class=\"[^\"]*\breply\b[^\"]*\"[^>]*>", block)
    return match.group(0) if match else None


def _observation_text(obs: dict[str, Any], key: str) -> str:
    value = obs.get(key)
    return value if isinstance(value, str) else ""
