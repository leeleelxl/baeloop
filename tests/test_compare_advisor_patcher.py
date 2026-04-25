from baeloop.advisor import propose_patch
from baeloop.compare import build_comparison_report, render_markdown
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
            },
        )
    ]

    report = build_comparison_report(baseline, candidate, taskset_id="smoke")

    assert report.metrics["baseline"].avg_input_tokens == 1000
    assert report.metrics["candidate"].avg_input_tokens == 800
    assert report.metrics["delta"]["avg_input_tokens"] == -200
    assert report.metrics["delta"]["avg_latency_sec"] == -1


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
