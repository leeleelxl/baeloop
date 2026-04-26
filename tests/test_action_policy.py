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


def _grid_obs() -> dict:
    return {
        "goal": "Click on the grid coordinate (1,2).",
        "url": "file:///tmp/miniwob/grid-coordinate.html",
        "pruned_html": """
        <div bid="12" id="area" visible="">
          <svg bid="13" visible="">
            <line x1="0" x2="150" y1="75" y2="75"></line>
            <line x1="75" x2="75" y1="0" y2="150"></line>
            <circle class="plot-point" cx="75" cy="75" id="(0,0)" r="4"></circle>
            <circle class="plot-point" cx="105" cy="15" id="(1,2)" r="4"></circle>
          </svg>
        </div>
        """,
        "extra_element_properties": {
            "13": {"bbox": [12.0, 162.0, 450.0, 450.0]},
        },
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
    assert state.interventions == 1
    assert state.interventions_by_policy == {"scroll_before_submit": 1}


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
    assert state.interventions == 1
    assert state.interventions_by_policy == {"terminal_keyboard_type": 1}


def test_composite_action_policy_applies_task_scoped_rewrites() -> None:
    state = ActionPolicyState()
    policy = ActionPolicyConfig(
        enabled=True,
        name="composite",
        policies=["scroll_before_submit", "terminal_keyboard_type"],
        max_interventions=20,
        policy_limits={"scroll_before_submit": 1, "terminal_keyboard_type": 20},
        scroll_delta_y=621,
    )

    social = apply_action_policy("click('104')", _social_obs(), policy, state)
    terminal = apply_action_policy("fill('25', 'ls')", _terminal_obs(), policy, state)

    assert social.applied is True
    assert social.policy_name == "scroll_before_submit"
    assert social.action == "scroll(0, 621)"
    assert terminal.applied is True
    assert terminal.policy_name == "terminal_keyboard_type"
    assert terminal.action == "focus('25')\nkeyboard_type('ls')"
    assert state.interventions == 2
    assert state.interventions_by_policy == {
        "scroll_before_submit": 1,
        "terminal_keyboard_type": 1,
    }


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


def test_grid_coordinate_click_rewrites_svg_root_click_to_mouse_click() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="click('13')",
        obs=_grid_obs(),
        policy=ActionPolicyConfig(
            enabled=True,
            name="grid_coordinate_click",
            max_interventions=1,
        ),
        state=state,
    )

    assert decision.applied is True
    assert decision.action == "mouse_click(164, 104)"
    assert decision.original_action == "click('13')"
    assert decision.policy_name == "grid_coordinate_click"
    assert state.interventions_by_policy == {"grid_coordinate_click": 1}


def test_grid_coordinate_click_ignores_non_svg_clicks() -> None:
    state = ActionPolicyState()
    decision = apply_action_policy(
        action="click('99')",
        obs=_grid_obs(),
        policy=ActionPolicyConfig(
            enabled=True,
            name="grid_coordinate_click",
            max_interventions=1,
        ),
        state=state,
    )

    assert decision.applied is False
    assert decision.action == "click('99')"


def test_policy_wrapper_exposes_extended_action_set_for_composite_terminal_policy() -> None:
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
            name="composite",
            policies=["scroll_before_submit", "terminal_keyboard_type"],
            max_interventions=20,
            policy_limits={"scroll_before_submit": 1, "terminal_keyboard_type": 20},
        ),
    )

    python_code = wrapped.action_set.to_python_code("focus('25')\nkeyboard_type('ls')")

    assert "def keyboard_type" in python_code


def test_policy_wrapper_exposes_extended_action_set_for_grid_policy() -> None:
    base_agent = SimpleNamespace(
        actions=[],
        action_set=SimpleNamespace(to_python_code=lambda _action: ""),
        obs_preprocessor=lambda obs: obs,
    )
    base_agent.get_action = lambda _obs: ("click('13')", SimpleNamespace(extra_info={}))
    base_agent.reset = lambda seed=None: None

    wrapped = PolicyWrappedAgent(
        base_agent=base_agent,
        action_policy=ActionPolicyConfig(
            enabled=True,
            name="grid_coordinate_click",
            max_interventions=1,
        ),
    )

    python_code = wrapped.action_set.to_python_code("mouse_click(164, 104)")

    assert "def mouse_click" in python_code


def test_agentlab_wrapper_rejects_unknown_composite_action_policy() -> None:
    config = AgentConfig(
        id="bad_composite_policy",
        model="gpt-4o-mini",
        max_steps=5,
        action_policy=ActionPolicyConfig(
            enabled=True,
            name="composite",
            policies=["scroll_before_submit", "unknown_policy"],
            max_interventions=1,
        ),
    )

    try:
        _maybe_wrap_agent_args(SimpleNamespace(agent_name="base"), config)
    except AgentLabAdapterUnavailable as exc:
        assert "Unsupported action policy" in str(exc)
        assert "unknown_policy" in str(exc)
    else:
        raise AssertionError("Expected unknown composite action policies to be rejected")
