from __future__ import annotations

from baeloop.models import AdvisorAnalysis, Intervention

EXTENDED_STEP_BUDGET = 30


def propose_intervention(analysis: AdvisorAnalysis) -> Intervention:
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

    if _all_max_step_failures_are_terminal_blindness(analysis):
        return Intervention(
            id="hyp_investigate_terminal_observation",
            kind="investigation",
            summary="Keep the candidate config and inspect terminal observation failure before increasing budget again.",
            rationale="Failure evidence points to terminal output blindness, so more steps would likely extend the command loop without fixing state visibility.",
            expected_effect="Identify whether the terminal task needs an observation extraction fix or should remain a documented baseline limitation.",
            risk="Does not immediately improve terminal success until the observation issue is addressed.",
            target_root_causes=["terminal_output_blindness"],
            supported_by=["dominant_root_cause=terminal_output_blindness"],
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


def _all_max_step_failures_are_terminal_blindness(analysis: AdvisorAnalysis) -> bool:
    max_step_count = analysis.candidate_failures.get("max_steps", 0)
    if not max_step_count:
        return False
    return analysis.candidate_root_causes.get("terminal_output_blindness", 0) >= max_step_count


def _has_non_terminal_max_step_failures(analysis: AdvisorAnalysis) -> bool:
    max_step_count = analysis.candidate_failures.get("max_steps", 0)
    terminal_blind_count = analysis.candidate_root_causes.get("terminal_output_blindness", 0)
    return max_step_count > terminal_blind_count
