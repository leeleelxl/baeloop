from __future__ import annotations

import gzip
import pickle
from types import SimpleNamespace

from baeloop.models import ActionPolicyConfig
from baeloop.policy_replay import replay_action_policy_trace, render_policy_replay_markdown


def test_replay_action_policy_trace_detects_counterfactual_intervention(tmp_path) -> None:
    _write_step(tmp_path / "step_0.pkl.gz", "click('19')", _social_obs())
    _write_step(tmp_path / "step_1.pkl.gz", "click('104')", _social_obs())

    report = replay_action_policy_trace(
        trace_dir=tmp_path,
        policy=ActionPolicyConfig(
            enabled=True,
            name="scroll_before_submit",
            max_interventions=1,
            scroll_delta_y=621,
        ),
    )

    assert report.fired is True
    assert report.applied_count == 1
    assert report.first_intervention is not None
    assert report.first_intervention.step == 1
    assert report.first_intervention.original_action == "click('104')"
    assert report.first_intervention.rewritten_action == "scroll(0, 621)"


def test_render_policy_replay_markdown_includes_first_intervention(tmp_path) -> None:
    _write_step(tmp_path / "step_0.pkl.gz", "click('104')", _social_obs())
    report = replay_action_policy_trace(
        trace_dir=tmp_path,
        policy=ActionPolicyConfig(
            enabled=True,
            name="scroll_before_submit",
            max_interventions=1,
        ),
    )

    markdown = render_policy_replay_markdown(report)

    assert "## First Intervention" in markdown
    assert "| 0 | true | `click('104')` | `scroll(0, 621)` |" in markdown


def test_replay_action_policy_trace_rejects_disabled_policy(tmp_path) -> None:
    _write_step(tmp_path / "step_0.pkl.gz", "click('104')", _social_obs())

    try:
        replay_action_policy_trace(
            trace_dir=tmp_path,
            policy=ActionPolicyConfig(enabled=False, name="scroll_before_submit"),
        )
    except ValueError as exc:
        assert "enabled action_policy" in str(exc)
    else:
        raise AssertionError("Expected disabled action policies to be rejected")


def _write_step(path, action: str, obs: dict[str, str]) -> None:
    with gzip.open(path, "wb") as handle:
        pickle.dump(SimpleNamespace(action=action, obs=obs), handle)


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
