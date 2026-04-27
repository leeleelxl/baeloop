from baeloop.advisor_analysis import analyze_report
from baeloop.advisor import propose_patch
from baeloop.compare import build_comparison_report, render_markdown
from baeloop.failure_analysis import collect_failure_evidence
from baeloop.models import AdvisorProposal, RunRecord
from baeloop.patcher import materialize_config_patch


def test_compare_tracks_regressions_and_improvements() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_b",
            status="failed",
            normalized_score=0.0,
            step_count=3,
            latency_sec=1.5,
            failure_type="invalid_action",
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.1,
            failure_type="invalid_action",
        ),
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_b",
            status="success",
            normalized_score=1.0,
            step_count=4,
            latency_sec=1.8,
        ),
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")

    assert report.regression_count == 1
    assert len(report.improvements) == 1
    assert report.failure_summary["candidate"] == {"invalid_action": 1}
    assert report.compared_task_count == 2
    assert report.missing_in_baseline == []
    assert report.missing_in_candidate == []


def test_compare_summarizes_diagnostics_efficiency_metrics() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=2.0,
            diagnostics={
                "input_tokens": 1000,
                "output_tokens": 100,
                "llm_call_count": 2,
                "agent_retry_count": 0.0,
                "busted_retry_count": 0,
                "action_policy_interventions": 0,
            },
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
            diagnostics={
                "input_tokens": 800,
                "output_tokens": 90,
                "llm_call_count": 2,
                "agent_retry_count": 0.0,
                "busted_retry_count": 0,
                "action_policy_interventions": 1,
            },
        )
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")

    assert report.metrics["baseline"].avg_input_tokens == 1000
    assert report.metrics["candidate"].avg_input_tokens == 800
    assert report.metrics["delta"]["avg_input_tokens"] == -200
    assert report.metrics["delta"]["avg_latency_sec"] == -1
    assert report.metrics["delta"]["avg_action_policy_interventions"] == 1


def test_analyst_summarizes_candidate_failure_evidence() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.social-media-all#seed=26",
            status="success",
            normalized_score=1.0,
            step_count=5,
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
            latency_sec=2.0,
            failure_type="zero_score",
        )
    ]

    analysis = analyze_report(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert analysis.dominant_failure == "zero_score"
    assert analysis.dominant_root_cause == "missed_scroll_target"
    assert analysis.candidate_root_causes == {"missed_scroll_target": 1}
    assert analysis.evidence_count == 1


def test_markdown_report_shows_baseline_and_candidate_failure_taxonomy() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.0,
            failure_type="max_steps",
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.0,
            failure_type="invalid_action",
        )
    ]

    markdown = render_markdown(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert "| Failure Type | Baseline | Candidate |" in markdown
    assert "| `max_steps` | 1 | 0 |" in markdown
    assert "| `invalid_action` | 0 | 1 |" in markdown


def test_failure_evidence_classifies_known_hard_task_patterns() -> None:
    evidence = collect_failure_evidence(
        [
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.grid-coordinate#seed=25",
                status="failed",
                normalized_score=0.0,
                step_count=1,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.social-media-all#seed=26",
                status="failed",
                normalized_score=0.0,
                step_count=8,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.terminal#seed=27",
                status="max_steps",
                normalized_score=0.0,
                step_count=30,
                latency_sec=1.0,
                failure_type="max_steps",
            ),
        ]
    )

    assert [item.root_cause for item in evidence] == [
        "coordinate_click_miss",
        "missed_scroll_target",
        "terminal_input_action_mismatch",
    ]


def test_failure_evidence_classifies_control_surface_patterns() -> None:
    evidence = collect_failure_evidence(
        [
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.use-slider-2#seed=35",
                status="max_steps",
                normalized_score=0.0,
                step_count=20,
                latency_sec=1.0,
                failure_type="max_steps",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.drag-circle#seed=40",
                status="failed",
                normalized_score=0.0,
                step_count=2,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.drag-cube#seed=41",
                status="failed",
                normalized_score=0.0,
                step_count=9,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.drag-items-grid#seed=43",
                status="failed",
                normalized_score=0.0,
                step_count=1,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.draw-circle#seed=48",
                status="failed",
                normalized_score=0.0,
                step_count=6,
                latency_sec=1.0,
                failure_type="zero_score",
            ),
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="browsergym/miniwob.click-pie#seed=49",
                status="max_steps",
                normalized_score=0.0,
                step_count=20,
                latency_sec=1.0,
                failure_type="max_steps",
            ),
        ]
    )

    assert [item.root_cause for item in evidence] == [
        "multi_slider_control_loop",
        "coordinate_drag_surface_mismatch",
        "directional_drag_control_mismatch",
        "list_drag_semantics_mismatch",
        "coordinate_draw_surface_mismatch",
        "coordinate_click_surface_mismatch",
    ]


def test_compare_report_renders_failure_evidence() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="success",
            normalized_score=1.0,
            step_count=1,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="failed",
            normalized_score=0.0,
            step_count=1,
            latency_sec=1.0,
            failure_type="zero_score",
        )
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")
    markdown = render_markdown(report)

    assert report.failure_evidence["candidate"][0].root_cause == "coordinate_click_miss"
    assert "## Failure Evidence" in markdown
    assert "`coordinate_click_miss`" in markdown


def test_compare_rejects_mixed_config_records() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="other_baseline",
            task_id="task_b",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]

    try:
        build_comparison_report(baseline, candidate, taskset_id="smoke")
    except ValueError as exc:
        assert "exactly one config_id" in str(exc)
    else:
        raise AssertionError("Expected mixed config records to be rejected")


def test_compare_reports_missing_tasks_and_uses_common_task_metrics() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_only_base",
            status="failed",
            normalized_score=0.0,
            step_count=10,
            latency_sec=10.0,
            failure_type="timeout",
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=4,
            latency_sec=2.0,
        ),
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_only_candidate",
            status="failed",
            normalized_score=0.0,
            step_count=10,
            latency_sec=10.0,
            failure_type="timeout",
        ),
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")

    assert report.compared_task_count == 1
    assert report.missing_in_baseline == ["task_only_candidate"]
    assert report.missing_in_candidate == ["task_only_base"]
    assert report.metrics["baseline"].task_count == 1
    assert report.metrics["candidate"].task_count == 1


def test_compare_tracks_score_delta_without_success_flip() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="failed",
            normalized_score=0.8,
            step_count=5,
            latency_sec=1.0,
            failure_type="partial_score",
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="failed",
            normalized_score=0.1,
            step_count=5,
            latency_sec=1.0,
            failure_type="partial_score",
        )
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")

    assert report.regression_count == 1
    assert abs(report.regressions[0].score_delta - -0.7) < 1e-9


def test_advisor_generates_retry_patch_for_invalid_action() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.1,
            failure_type="invalid_action",
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.patch == {"retry_policy": {"enabled": True, "max_retries": 1}}
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "retry_policy"
    assert proposal.critic_decision == "accepted"


def test_advisor_extends_step_budget_with_bounded_non_noop_patch() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="max_steps",
            normalized_score=0.0,
            step_count=20,
            latency_sec=20.0,
            failure_type="max_steps",
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_extend_step_budget"
    assert proposal.patch == {"max_steps": 30}
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "config_patch"
    assert "bounded patch present" in proposal.critic_notes


def test_advisor_probes_coordinate_control_before_extending_budget() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.click-pie#seed=49",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.drag-circle#seed=40",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.click-pie#seed=49",
            status="max_steps",
            normalized_score=0.0,
            step_count=20,
            latency_sec=20.0,
            failure_type="max_steps",
        ),
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.drag-circle#seed=40",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=2.0,
            failure_type="zero_score",
        ),
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_probe_coordinate_control"
    assert proposal.patch == {}
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "investigation"
    assert proposal.intervention.target_root_causes == [
        "coordinate_click_surface_mismatch",
        "coordinate_drag_surface_mismatch",
    ]


def test_advisor_holds_config_for_unclassified_zero_score_failures() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.1,
            failure_type="zero_score",
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_investigate_unclassified_failures"
    assert proposal.patch == {}
    assert "unclassified_zero_score=1" in proposal.rationale
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "investigation"


def test_advisor_generates_action_policy_for_missed_scroll_target() -> None:
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

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_scroll_before_submit"
    assert proposal.patch == {
        "action_policy": {
            "enabled": True,
            "name": "scroll_before_submit",
            "max_interventions": 1,
            "scroll_delta_y": 621,
        }
    }
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "action_policy"
    assert proposal.intervention.target_root_causes == ["missed_scroll_target"]


def test_advisor_composes_action_policies_when_single_policy_regresses_other_root_cause() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="scroll_policy",
            task_id="browsergym/miniwob.social-media-all#seed=26",
            status="success",
            normalized_score=1.0,
            step_count=9,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="scroll_policy",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="max_steps",
            normalized_score=0.0,
            step_count=30,
            latency_sec=30.0,
            failure_type="max_steps",
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="terminal_policy",
            task_id="browsergym/miniwob.social-media-all#seed=26",
            status="failed",
            normalized_score=0.0,
            step_count=4,
            latency_sec=1.0,
            failure_type="zero_score",
        ),
        RunRecord(
            experiment_id="new",
            config_id="terminal_policy",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="success",
            normalized_score=1.0,
            step_count=4,
            latency_sec=4.0,
        ),
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_combine_scroll_and_terminal_policies"
    assert proposal.patch == {
        "action_policy": {
            "enabled": True,
            "name": "composite",
            "policies": ["scroll_before_submit", "terminal_keyboard_type"],
            "max_interventions": 20,
            "policy_limits": {
                "scroll_before_submit": 1,
                "terminal_keyboard_type": 20,
            },
            "scroll_delta_y": 621,
        }
    }
    assert proposal.intervention is not None
    assert proposal.intervention.kind == "action_policy"
    assert proposal.intervention.target_root_causes == [
        "missed_scroll_target",
        "terminal_input_action_mismatch",
    ]


def test_advisor_avoids_budget_patch_for_terminal_input_action_mismatch() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="max_steps",
            normalized_score=0.0,
            step_count=30,
            latency_sec=30.0,
            failure_type="max_steps",
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_terminal_keyboard_type"
    assert proposal.patch == {
        "action_policy": {
            "enabled": True,
            "name": "terminal_keyboard_type",
            "max_interventions": 20,
        }
    }
    assert proposal.intervention is not None
    assert proposal.intervention.target_root_causes == ["terminal_input_action_mismatch"]


def test_advisor_generates_grid_coordinate_action_policy_for_coordinate_click_miss() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="combined_policy",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="success",
            normalized_score=1.0,
            step_count=1,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="combined_policy_new",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="failed",
            normalized_score=0.0,
            step_count=1,
            latency_sec=1.0,
            failure_type="zero_score",
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_grid_coordinate_click"
    assert proposal.patch == {
        "action_policy": {
            "enabled": True,
            "name": "composite",
            "policies": [
                "scroll_before_submit",
                "terminal_keyboard_type",
                "grid_coordinate_click",
            ],
            "max_interventions": 25,
            "policy_limits": {
                "scroll_before_submit": 1,
                "terminal_keyboard_type": 20,
                "grid_coordinate_click": 1,
            },
            "scroll_delta_y": 621,
        }
    }
    assert proposal.intervention is not None
    assert proposal.intervention.target_root_causes == ["coordinate_click_miss"]


def test_advisor_avoids_budget_patch_when_all_max_step_failures_are_terminal_interaction_issues() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="success",
            normalized_score=1.0,
            step_count=1,
            latency_sec=1.0,
        ),
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        ),
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.grid-coordinate#seed=25",
            status="failed",
            normalized_score=0.0,
            step_count=1,
            latency_sec=1.0,
            failure_type="zero_score",
        ),
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="browsergym/miniwob.terminal#seed=27",
            status="max_steps",
            normalized_score=0.0,
            step_count=30,
            latency_sec=30.0,
            failure_type="max_steps",
        ),
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_terminal_keyboard_type"
    assert proposal.patch == {
        "action_policy": {
            "enabled": True,
            "name": "terminal_keyboard_type",
            "max_interventions": 20,
        }
    }


def test_advisor_holds_config_when_candidate_has_no_failures_or_regressions() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.1,
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_hold_config_expand_taskset"
    assert proposal.patch == {}


def test_advisor_keeps_quality_winner_when_quality_improves() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="failed",
            normalized_score=0.0,
            step_count=2,
            latency_sec=1.0,
            failure_type="zero_score",
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=2.0,
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_keep_quality_winner"
    assert proposal.patch == {}


def test_advisor_keeps_efficiency_winner_when_quality_is_equal() -> None:
    baseline = [
        RunRecord(
            experiment_id="base",
            config_id="baseline",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=2.0,
        )
    ]
    candidate = [
        RunRecord(
            experiment_id="new",
            config_id="variant",
            task_id="task_a",
            status="success",
            normalized_score=1.0,
            step_count=2,
            latency_sec=1.0,
        )
    ]

    proposal = propose_patch(build_comparison_report(baseline, candidate, taskset_id="smoke"))

    assert proposal.hypothesis_id == "hyp_keep_efficiency_winner"
    assert proposal.patch == {}


def test_advisor_accepts_reports_without_diagnostics_delta_fields() -> None:
    report = build_comparison_report(
        [
            RunRecord(
                experiment_id="base",
                config_id="baseline",
                task_id="task_a",
                status="success",
                normalized_score=1.0,
                step_count=2,
                latency_sec=1.0,
            )
        ],
        [
            RunRecord(
                experiment_id="new",
                config_id="variant",
                task_id="task_a",
                status="success",
                normalized_score=1.0,
                step_count=2,
                latency_sec=1.0,
            )
        ],
        taskset_id="smoke",
    )
    report.metrics["delta"].pop("avg_input_tokens")
    report.metrics["delta"].pop("avg_output_tokens")

    proposal = propose_patch(report)

    assert proposal.hypothesis_id == "hyp_hold_config_expand_taskset"


def test_patcher_deep_merges_bounded_patch() -> None:
    proposal = AdvisorProposal(
        hypothesis_id="hyp_retry_invalid_or_noop",
        summary="summary",
        rationale="rationale",
        expected_effect="effect",
        risk="risk",
        patch={"retry_policy": {"enabled": True, "max_retries": 1}},
    )

    patched = materialize_config_patch(
        base_config={
            "id": "baseline",
            "agent": "agentlab_generic",
            "model": "gpt-4o-mini",
            "max_steps": 15,
            "retry_policy": {"enabled": False, "max_retries": 0},
        },
        proposal=proposal,
    )

    assert patched["id"] == "baseline_hyp_retry_invalid_or_noop"
    assert patched["retry_policy"] == {"enabled": True, "max_retries": 1}
    assert patched["parent_config_id"] == "baseline"


def test_patcher_accepts_action_policy_patch() -> None:
    proposal = AdvisorProposal(
        hypothesis_id="hyp_scroll_before_submit",
        summary="summary",
        rationale="rationale",
        expected_effect="effect",
        risk="risk",
        patch={
            "action_policy": {
                "enabled": True,
                "name": "scroll_before_submit",
                "max_interventions": 1,
            }
        },
    )

    patched = materialize_config_patch(
        base_config={
            "id": "baseline",
            "agent": "agentlab_generic",
            "model": "gpt-4o-mini",
            "max_steps": 30,
            "retry_policy": {"enabled": True, "max_retries": 1},
            "action_policy": {"enabled": False, "name": "none", "max_interventions": 0},
        },
        proposal=proposal,
    )

    assert patched["action_policy"]["enabled"] is True
    assert patched["action_policy"]["name"] == "scroll_before_submit"
    assert patched["action_policy"]["max_interventions"] == 1


def test_patcher_rejects_invalid_materialized_config() -> None:
    proposal = AdvisorProposal(
        hypothesis_id="hyp_bad_retry",
        summary="summary",
        rationale="rationale",
        expected_effect="effect",
        risk="risk",
        patch={"retry_policy": {"max_retries": -1}},
    )

    try:
        materialize_config_patch(
            base_config={
                "id": "baseline",
                "agent": "agentlab_generic",
                "model": "gpt-4o-mini",
                "max_steps": 15,
                "retry_policy": {"enabled": False, "max_retries": 0},
            },
            proposal=proposal,
        )
    except ValueError as exc:
        assert "max_retries" in str(exc)
    else:
        raise AssertionError("Expected invalid materialized config to be rejected")


def test_patcher_rejects_non_empty_noop_patch() -> None:
    proposal = AdvisorProposal(
        hypothesis_id="hyp_noop",
        summary="summary",
        rationale="rationale",
        expected_effect="effect",
        risk="risk",
        patch={"max_steps": 20},
    )

    try:
        materialize_config_patch(
            base_config={
                "id": "baseline",
                "agent": "agentlab_generic",
                "model": "gpt-4o-mini",
                "max_steps": 20,
                "retry_policy": {"enabled": False, "max_retries": 0},
            },
            proposal=proposal,
        )
    except ValueError as exc:
        assert "does not change" in str(exc)
    else:
        raise AssertionError("Expected non-empty no-op patch to be rejected")
