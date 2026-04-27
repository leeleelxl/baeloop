from __future__ import annotations

from baeloop.models import AdvisorAnalysis, Intervention

EXTENDED_STEP_BUDGET = 30
TERMINAL_INTERACTION_ROOT_CAUSES = {
    "terminal_input_action_mismatch",
    "terminal_output_blindness",
}
CONTROL_SURFACE_ROOT_CAUSES = {
    "coordinate_click_surface_mismatch",
    "coordinate_drag_surface_mismatch",
    "coordinate_draw_surface_mismatch",
    "directional_drag_control_mismatch",
    "list_drag_semantics_mismatch",
    "multi_slider_control_loop",
}


def propose_intervention(analysis: AdvisorAnalysis) -> Intervention:
    if (
        not analysis.candidate_failures
        and analysis.quality_not_worse
        and (analysis.success_rate_delta > 0 or analysis.avg_score_delta > 0)
    ):
        return Intervention(
            id="hyp_keep_quality_winner",
            kind="hold",
            summary="Keep the candidate config as a quality winner on the measured task set.",
            rationale="The candidate has no failures or regressions and improves success or normalized score.",
            expected_effect="Preserve the improved solved-task quality before expanding the benchmark slice.",
            risk="Quality gains may be seed-specific unless confirmed with repeated or broader runs.",
            supported_by=["no_candidate_failures", "quality_not_worse", "quality_gain"],
        )

    if not analysis.candidate_failures and analysis.quality_not_worse and analysis.efficiency_gain:
        return Intervention(
            id="hyp_keep_efficiency_winner",
            kind="hold",
            summary="Keep the candidate config as an efficiency winner under equal task quality.",
            rationale="The candidate has no failures or regressions and improves at least one efficiency metric enough to justify keeping it.",
            expected_effect="Preserve solved-task quality while reducing latency or token cost on the measured task set.",
            risk="Efficiency gains may be run-to-run noise unless confirmed on a larger task set.",
            supported_by=["no_candidate_failures", "quality_not_worse", "efficiency_gain"],
        )

    if not analysis.candidate_failures and analysis.quality_not_worse:
        return Intervention(
            id="hyp_hold_config_expand_taskset",
            kind="hold",
            summary="Keep the candidate config unchanged and expand the task set before optimizing further.",
            rationale="The candidate has no failures or regressions on the current task set, so another config patch would be weakly supported.",
            expected_effect="Reduce overfitting risk by collecting evidence on harder or broader MiniWoB tasks first.",
            risk="Delays optimization if the current task set is already representative, but avoids changing a saturated config without evidence.",
            supported_by=["no_candidate_failures", "quality_not_worse"],
        )

    if analysis.dominant_failure in {"invalid_action", "no_op_loop"}:
        return Intervention(
            id="hyp_retry_invalid_or_noop",
            kind="retry_policy",
            summary="Enable a conservative retry policy for invalid-action or no-progress failures.",
            rationale=f"Candidate failures are dominated by `{analysis.dominant_failure}`, which may be recoverable with one bounded retry.",
            expected_effect="Improve success rate on recoverable interaction failures with a small latency increase.",
            risk="May hide deeper policy issues and can increase step count on tasks that are already looping.",
            patch={"retry_policy": {"enabled": True, "max_retries": 1}},
            supported_by=[f"dominant_failure={analysis.dominant_failure}"],
        )

    if _has_control_surface_failures(analysis):
        control_roots = _control_root_causes(analysis)
        return Intervention(
            id="hyp_probe_coordinate_control",
            kind="investigation",
            summary="Probe coordinate-level control actions before changing the config again.",
            rationale="Candidate failures point to slider, drag, drawing, or SVG click surfaces where bid-level actions are too coarse; another step-budget patch would likely repeat the same ineffective actions.",
            expected_effect="Identify which coordinate click, drag, or action-compression primitive can become a bounded action policy.",
            risk="Does not immediately improve success rate until a probe-backed coordinate-control policy is implemented.",
            target_root_causes=control_roots,
            supported_by=[f"control_root_causes={','.join(control_roots)}"],
        )

    if _has_non_terminal_max_step_failures(analysis):
        return Intervention(
            id="hyp_extend_step_budget",
            kind="config_patch",
            summary="Increase the step budget for tasks that appear budget-limited.",
            rationale=f"Candidate failures are dominated by `{analysis.dominant_failure}`, suggesting the agent may need more interaction budget.",
            expected_effect="Improve completion rate on longer tasks.",
            risk="May increase latency and can worsen looping behavior if failures are not actually budget-limited.",
            patch={"max_steps": EXTENDED_STEP_BUDGET},
            supported_by=[f"dominant_failure={analysis.dominant_failure}"],
        )

    if (
        analysis.regression_count > 0
        and "missed_scroll_target" in analysis.candidate_root_causes
        and "terminal_input_action_mismatch" in analysis.baseline_root_causes
    ):
        return Intervention(
            id="hyp_combine_scroll_and_terminal_policies",
            kind="action_policy",
            summary="Compose scroll and terminal action policies instead of replacing one with the other.",
            rationale="The report shows a candidate regression from `missed_scroll_target` while the baseline still had `terminal_input_action_mismatch`; a single replacement policy would likely fix one task family while breaking the other.",
            expected_effect="Preserve the terminal input fix while restoring hidden-target scrolling behavior.",
            risk="Combining task-scoped policies increases wrapper surface area, so each sub-policy must stay bounded and evidence-gated.",
            patch={
                "action_policy": {
                    "enabled": True,
                    "name": "composite",
                    "policies": [
                        "scroll_before_submit",
                        "terminal_keyboard_type",
                    ],
                    "max_interventions": 20,
                    "policy_limits": {
                        "scroll_before_submit": 1,
                        "terminal_keyboard_type": 20,
                    },
                    "scroll_delta_y": 621,
                }
            },
            target_root_causes=[
                "missed_scroll_target",
                "terminal_input_action_mismatch",
            ],
            supported_by=[
                "candidate_root_cause=missed_scroll_target",
                "baseline_root_cause=terminal_input_action_mismatch",
                "regression_count>0",
            ],
        )

    if "missed_scroll_target" in analysis.candidate_root_causes:
        return Intervention(
            id="hyp_scroll_before_submit",
            kind="action_policy",
            summary="Enable a bounded scroll-before-submit action policy for hidden target failures.",
            rationale="Candidate failure evidence includes `missed_scroll_target`, so the agent likely submitted before scanning all hidden actionable targets.",
            expected_effect="Improve tasks that require scrolling to reveal remaining targets without changing the LLM prompt.",
            risk="May add one extra step on matching tasks if the hidden-target heuristic is too broad.",
            patch={
                "action_policy": {
                    "enabled": True,
                    "name": "scroll_before_submit",
                    "max_interventions": 1,
                    "scroll_delta_y": 621,
                }
            },
            target_root_causes=["missed_scroll_target"],
            supported_by=["root_cause=missed_scroll_target"],
        )

    if "terminal_input_action_mismatch" in analysis.candidate_root_causes:
        return Intervention(
            id="hyp_terminal_keyboard_type",
            kind="action_policy",
            summary="Enable a terminal keyboard-type action policy for custom terminal input.",
            rationale="Candidate failure evidence shows terminal commands were attempted with `fill`, but MiniWoB's custom terminal only updates command state from keyboard events.",
            expected_effect="Let the agent's terminal commands actually reach the MiniWoB terminal without changing the prompt.",
            risk="May expose the agent's incorrect shell commands as visible terminal errors; it fixes input delivery, not command planning.",
            patch={
                "action_policy": {
                    "enabled": True,
                    "name": "terminal_keyboard_type",
                    "max_interventions": 20,
                }
            },
            target_root_causes=["terminal_input_action_mismatch"],
            supported_by=["root_cause=terminal_input_action_mismatch"],
        )

    if "coordinate_click_miss" in analysis.candidate_root_causes:
        return Intervention(
            id="hyp_grid_coordinate_click",
            kind="action_policy",
            summary="Enable a coordinate-aware click policy for SVG grid-coordinate targets.",
            rationale="Candidate failure evidence shows the agent identified the target coordinate but clicked the SVG root because the target circle had no bid-addressable action.",
            expected_effect="Convert SVG-root clicks into precise mouse clicks on the requested grid point without changing the prompt.",
            risk="Only applies when the grid target can be parsed from goal/html/bbox evidence; otherwise it should no-op rather than guess.",
            patch={
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
            },
            target_root_causes=["coordinate_click_miss"],
            supported_by=["root_cause=coordinate_click_miss"],
        )

    if _all_max_step_failures_are_terminal_interaction_issues(analysis):
        terminal_roots = _terminal_root_causes(analysis)
        return Intervention(
            id="hyp_investigate_terminal_interaction",
            kind="investigation",
            summary="Keep the candidate config and inspect terminal interaction failure before increasing budget again.",
            rationale="Failure evidence points to terminal interaction issues, so more steps would likely extend the command loop without fixing input or state handling.",
            expected_effect="Identify whether the terminal task needs an input-action policy, observation extraction fix, or should remain a documented baseline limitation.",
            risk="Does not immediately improve terminal success until the interaction issue is addressed.",
            target_root_causes=terminal_roots,
            supported_by=[f"terminal_root_causes={','.join(terminal_roots)}"],
        )

    if analysis.dominant_failure in {"timeout", "max_steps"}:
        return Intervention(
            id="hyp_extend_step_budget",
            kind="config_patch",
            summary="Increase the step budget for tasks that appear budget-limited.",
            rationale=f"Candidate failures are dominated by `{analysis.dominant_failure}`, suggesting the agent may need more interaction budget.",
            expected_effect="Improve completion rate on longer tasks.",
            risk="May increase latency and can worsen looping behavior if failures are not actually budget-limited.",
            patch={"max_steps": EXTENDED_STEP_BUDGET},
            supported_by=[f"dominant_failure={analysis.dominant_failure}"],
        )

    if analysis.dominant_failure == "zero_score":
        root_causes = _root_cause_summary(analysis)
        evidence_note = f" Candidate evidence points to: {root_causes}." if root_causes else ""
        return Intervention(
            id="hyp_investigate_unclassified_failures",
            kind="investigation",
            summary="Keep the candidate config and classify remaining zero-score failures before changing config again.",
            rationale="`zero_score` is an outcome label, not an actionable root cause, so another bounded config patch would be weakly supported."
            + evidence_note,
            expected_effect="Avoid speculative or no-op patches while directing the next work toward better failure evidence.",
            risk="Does not immediately improve success rate until the residual failures are classified more precisely.",
            target_root_causes=list(analysis.candidate_root_causes),
            supported_by=[f"dominant_failure={analysis.dominant_failure}", f"root_causes={root_causes}"],
        )

    return Intervention(
        id="hyp_conservative_retry",
        kind="retry_policy",
        summary="Enable one retry as a conservative next configuration.",
        rationale="No single actionable failure type dominates, so use the smallest bounded patch that can recover transient failures.",
        expected_effect="Small chance of recovering transient failures without changing the core agent policy.",
        risk="Limited expected impact if failures are caused by perception or planning errors.",
        patch={"retry_policy": {"enabled": True, "max_retries": 1}},
        supported_by=["fallback_no_dominant_actionable_failure"],
    )


def _root_cause_summary(analysis: AdvisorAnalysis) -> str:
    return ", ".join(
        f"{root_cause}={count}"
        for root_cause, count in sorted(
            analysis.candidate_root_causes.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _all_max_step_failures_are_terminal_interaction_issues(analysis: AdvisorAnalysis) -> bool:
    max_step_count = analysis.candidate_failures.get("max_steps", 0)
    if not max_step_count:
        return False
    return _terminal_root_cause_count(analysis) >= max_step_count


def _has_non_terminal_max_step_failures(analysis: AdvisorAnalysis) -> bool:
    max_step_count = analysis.candidate_failures.get("max_steps", 0)
    return max_step_count > _terminal_root_cause_count(analysis)


def _terminal_root_cause_count(analysis: AdvisorAnalysis) -> int:
    return sum(
        count
        for root_cause, count in analysis.candidate_root_causes.items()
        if root_cause in TERMINAL_INTERACTION_ROOT_CAUSES
    )


def _terminal_root_causes(analysis: AdvisorAnalysis) -> list[str]:
    return sorted(
        root_cause
        for root_cause in analysis.candidate_root_causes
        if root_cause in TERMINAL_INTERACTION_ROOT_CAUSES
    )


def _has_control_surface_failures(analysis: AdvisorAnalysis) -> bool:
    return bool(set(analysis.candidate_root_causes) & CONTROL_SURFACE_ROOT_CAUSES)


def _control_root_causes(analysis: AdvisorAnalysis) -> list[str]:
    return sorted(
        root_cause
        for root_cause in analysis.candidate_root_causes
        if root_cause in CONTROL_SURFACE_ROOT_CAUSES
    )
