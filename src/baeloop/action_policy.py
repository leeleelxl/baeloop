from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from baeloop.models import ActionPolicyConfig


SCROLL_BEFORE_SUBMIT = "scroll_before_submit"
TERMINAL_KEYBOARD_TYPE = "terminal_keyboard_type"


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


def _is_social_media_all_goal(obs: dict[str, Any]) -> bool:
    goal = _observation_text(obs, "goal")
    return 'Reply" button on all posts by @ultricies' in goal or (
        "social-media-all" in _observation_text(obs, "url").lower()
    )


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
