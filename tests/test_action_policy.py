from types import SimpleNamespace

from baeloop.action_policy import ActionPolicyState, apply_action_policy
from baeloop.adapters.agentlab import (
    AgentLabAdapterUnavailable,
    PolicyWrappedAgent,
    _maybe_wrap_agent_args,
)
from baeloop.models import ActionPolicyConfig, AgentConfig


def _social_obs() -> dict[str, str]:
    return {
        "goal": 'Click the "Reply" button on all posts by @ultricies and then click Submit.',
        "pruned_html": """
        <div bid="93" class="media" data-result="8">
          <span bid="96" class="username">@ultricies</span>
          <span bid="99" class="reply" clickable=""></span>
        </div>
        <p bid="103" id="submitRow">
          <button bid="104" clickable="" type="button">Submit</button>
        </p>
        """,
    }


def _terminal_obs() -> dict[str, str]:
    return {
        "goal": "Use the terminal below to delete a file ending with the extension .gpg",
        "pruned_html": """
        <div bid="14" clickable="" id="terminal" visible="">
          <input bid="25" clickable="" id="terminal-target" type="text" value="" visible=""/>
        </div>
        """,
    }


def test_scroll_before_submit_rewrites_submit_when_hidden_reply_remains() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="click('104')",
        obs=_social_obs(),
        policy=ActionPolicyConfig(
            enabled=True,
            name="scroll_before_submit",
            max_interventions=1,
            scroll_delta_y=621,
        ),
        state=state,
    )

    assert decision.applied is True
    assert decision.action == "scroll(0, 621)"
    assert decision.original_action == "click('104')"


def test_scroll_before_submit_is_bounded_to_one_intervention() -> None:
    state = ActionPolicyState()
    policy = ActionPolicyConfig(
        enabled=True,
        name="scroll_before_submit",
        max_interventions=1,
        scroll_delta_y=621,
    )

    first = apply_action_policy("click('104')", _social_obs(), policy, state)
    second = apply_action_policy("click('104')", _social_obs(), policy, state)

    assert first.applied is True
    assert second.applied is False
    assert second.action == "click('104')"


def test_scroll_before_submit_ignores_non_submit_actions() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="click('99')",
        obs=_social_obs(),
        policy=ActionPolicyConfig(
            enabled=True,
            name="scroll_before_submit",
            max_interventions=1,
        ),
        state=state,
    )

    assert decision.applied is False
    assert decision.action == "click('99')"


def test_policy_wrapper_updates_agent_history_and_agent_info() -> None:
    base_agent = SimpleNamespace(
        actions=[],
        action_set=object(),
        obs_preprocessor=lambda obs: obs,
    )

    def get_action(_obs):
        base_agent.actions.append("click('104')")
        return "click('104')", SimpleNamespace(extra_info={})

    base_agent.get_action = get_action
    base_agent.reset = lambda seed=None: base_agent.actions.clear()

    wrapped = PolicyWrappedAgent(
        base_agent=base_agent,
        action_policy=ActionPolicyConfig(
            enabled=True,
            name="scroll_before_submit",
            max_interventions=1,
            scroll_delta_y=621,
        ),
    )

    action, agent_info = wrapped.get_action(_social_obs())

    assert action == "scroll(0, 621)"
    assert base_agent.actions[-1] == "scroll(0, 621)"
    assert agent_info.extra_info["action_policy_applied"] is True
    assert agent_info.extra_info["action_policy_original_action"] == "click('104')"


def test_policy_wrapper_exposes_extended_action_set_for_terminal_policy() -> None:
    base_agent = SimpleNamespace(
        actions=[],
        action_set=SimpleNamespace(to_python_code=lambda _action: ""),
        obs_preprocessor=lambda obs: obs,
    )
    base_agent.get_action = lambda _obs: ("fill('25', 'ls')", SimpleNamespace(extra_info={}))
    base_agent.reset = lambda seed=None: None

    wrapped = PolicyWrappedAgent(
        base_agent=base_agent,
        action_policy=ActionPolicyConfig(
            enabled=True,
            name="terminal_keyboard_type",
            max_interventions=5,
        ),
    )

    python_code = wrapped.action_set.to_python_code("focus('25')\nkeyboard_type('ls')")

    assert "def keyboard_type" in python_code


def test_agentlab_wrapper_rejects_unknown_action_policy() -> None:
    config = AgentConfig(
        id="bad_policy",
        model="gpt-4o-mini",
        max_steps=5,
        action_policy=ActionPolicyConfig(
            enabled=True,
            name="unknown_policy",
            max_interventions=1,
        ),
    )

    try:
        _maybe_wrap_agent_args(SimpleNamespace(agent_name="base"), config)
    except AgentLabAdapterUnavailable as exc:
        assert "Unsupported action policy" in str(exc)
    else:
        raise AssertionError("Expected unknown action policies to be rejected")


def test_terminal_keyboard_type_rewrites_fill_to_keyboard_events() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="fill('25', 'ls')",
        obs=_terminal_obs(),
        policy=ActionPolicyConfig(
            enabled=True,
            name="terminal_keyboard_type",
            max_interventions=5,
        ),
        state=state,
    )

    assert decision.applied is True
    assert decision.action == "focus('25')\nkeyboard_type('ls')"
    assert decision.original_action == "fill('25', 'ls')"


def test_terminal_keyboard_type_ignores_non_terminal_tasks() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="fill('25', 'ls')",
        obs={"goal": "Enter text into the field.", "pruned_html": ""},
        policy=ActionPolicyConfig(
            enabled=True,
            name="terminal_keyboard_type",
            max_interventions=5,
        ),
        state=state,
    )

    assert decision.applied is False
    assert decision.action == "fill('25', 'ls')"
