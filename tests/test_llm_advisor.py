from __future__ import annotations

import json

from baeloop.compare import build_comparison_report
from baeloop.llm_advisor import LLMAdvisorConfig, propose_patch_with_llm
from baeloop.models import RunRecord


class FakeChatClient:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.stages: list[str] = []

    def complete(self, *, stage, messages, config):
        self.stages.append(stage)
        return self.responses[stage]


def test_llm_advisor_runs_agent_stages_and_returns_bounded_proposal() -> None:
    report = _social_media_report()
    client = FakeChatClient(
        {
            "analyst": json.dumps(
                {
                    "summary": "Candidate regressed on hidden social targets.",
                    "dominant_root_causes": ["missed_scroll_target"],
                    "key_deltas": ["success_rate decreased"],
                    "risk_flags": ["one task only"],
                }
            ),
            "hypothesis": json.dumps(
                {
                    "id": "hyp_scroll_before_submit",
                    "kind": "action_policy",
                    "summary": "Enable bounded scroll-before-submit.",
                    "rationale": "Failure evidence shows hidden remaining reply target.",
                    "expected_effect": "Reveal hidden targets before submit.",
                    "risk": "Could add one extra action on matching task.",
                    "patch": {
                        "action_policy": {
                            "enabled": True,
                            "name": "scroll_before_submit",
                            "max_interventions": 1,
                            "scroll_delta_y": 621,
                        }
                    },
                    "target_root_causes": ["missed_scroll_target"],
                    "supported_by": ["root_cause=missed_scroll_target"],
                }
            ),
            "critic": json.dumps(
                {
                    "decision": "accepted",
                    "notes": ["patch is bounded", "evidence supports root cause"],
                }
            ),
        }
    )

    proposal = propose_patch_with_llm(report, config=LLMAdvisorConfig(), client=client)

    assert client.stages == ["analyst", "hypothesis", "critic"]
    assert proposal.advisor_mode == "llm"
    assert proposal.hypothesis_id == "hyp_scroll_before_submit"
    assert proposal.patch["action_policy"]["name"] == "scroll_before_submit"
    assert proposal.critic_decision == "accepted"
    assert "analyst" in proposal.advisor_stage_notes


def test_llm_advisor_falls_back_on_invalid_json() -> None:
    report = _social_media_report()
    client = FakeChatClient({"analyst": "not json"})

    proposal = propose_patch_with_llm(report, config=LLMAdvisorConfig(), client=client)

    assert proposal.advisor_mode == "llm_fallback"
    assert proposal.hypothesis_id == "hyp_scroll_before_submit"
    assert proposal.patch["action_policy"]["name"] == "scroll_before_submit"
    assert "fallback_error" in proposal.advisor_stage_notes


def test_llm_advisor_rejects_unbounded_patch_and_falls_back() -> None:
    report = _social_media_report()
    client = FakeChatClient(
        {
            "analyst": json.dumps({"summary": "x"}),
            "hypothesis": json.dumps(
                {
                    "id": "hyp_unsafe",
                    "kind": "config_patch",
                    "summary": "Unsafe patch.",
                    "rationale": "Unsupported.",
                    "expected_effect": "Unknown.",
                    "risk": "High.",
                    "patch": {"shell_command": "rm -rf /"},
                    "target_root_causes": ["missed_scroll_target"],
                    "supported_by": ["unsupported"],
                }
            ),
        }
    )

    proposal = propose_patch_with_llm(report, config=LLMAdvisorConfig(), client=client)

    assert proposal.advisor_mode == "llm_fallback"
    assert proposal.hypothesis_id == "hyp_scroll_before_submit"
    assert "fallback_error" in proposal.advisor_stage_notes


def test_llm_critic_can_reject_otherwise_valid_patch() -> None:
    report = _social_media_report()
    client = FakeChatClient(
        {
            "analyst": json.dumps({"summary": "x"}),
            "hypothesis": json.dumps(
                {
                    "id": "hyp_scroll_before_submit",
                    "kind": "action_policy",
                    "summary": "Enable bounded scroll-before-submit.",
                    "rationale": "Failure evidence shows hidden remaining reply target.",
                    "expected_effect": "Reveal hidden targets before submit.",
                    "risk": "Could add one extra action on matching task.",
                    "patch": {"action_policy": {"enabled": True, "name": "scroll_before_submit"}},
                    "target_root_causes": ["missed_scroll_target"],
                    "supported_by": ["root_cause=missed_scroll_target"],
                }
            ),
            "critic": json.dumps({"decision": "rejected", "notes": ["too broad"]}),
        }
    )

    proposal = propose_patch_with_llm(report, config=LLMAdvisorConfig(), client=client)

    assert proposal.advisor_mode == "llm"
    assert proposal.critic_decision == "rejected"
    assert proposal.patch == {}


def _social_media_report():
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.social-media-all#seed=26",
            status="success",
            normalized_score=1.0,
            step_count=7,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.social-media-all#seed=26",
            status="failed",
            normalized_score=0.0,
            step_count=8,
            latency_sec=1.0,
            failure_type="zero_score",
        )
    ]
    return build_comparison_report(baseline, candidate, taskset_id="smoke")
