from __future__ import annotations

from collections import Counter

from baeloop.models import AdvisorProposal, ComparisonReport, FailureEvidence

LATENCY_IMPROVEMENT_SEC = -0.5
TOKEN_IMPROVEMENT = -100.0
EXTENDED_STEP_BUDGET = 30


def propose_patch(report: ComparisonReport) -> AdvisorProposal:
    candidate_failures = report.failure_summary.get("candidate", {})
    candidate_evidence = report.failure_evidence.get("candidate", [])
    delta = report.metrics["delta"]
    quality_not_worse = (
        report.regression_count == 0
        and delta["success_rate"] >= 0
        and delta["avg_normalized_score"] >= 0
    )
    if not candidate_failures and quality_not_worse and _has_efficiency_gain(delta):
        return AdvisorProposal(
            hypothesis_id="hyp_keep_efficiency_winner",
            summary="Keep the candidate config as an efficiency winner under equal task quality.",
            rationale="The candidate has no failures or regressions and improves at least one efficiency metric enough to justify keeping it.",
            expected_effect="Preserve solved-task quality while reducing latency or token cost on the measured task set.",
            risk="Efficiency gains may be run-to-run noise unless confirmed on a larger task set.",
            patch={},
        )

    if not candidate_failures and quality_not_worse:
        return AdvisorProposal(
            hypothesis_id="hyp_hold_config_expand_taskset",
            summary="Keep the candidate config unchanged and expand the task set before optimizing further.",
            rationale="The candidate has no failures or regressions on the current task set, so another config patch would be weakly supported.",
            expected_effect="Reduce overfitting risk by collecting evidence on harder or broader MiniWoB tasks first.",
            risk="Delays optimization if the current task set is already representative, but avoids changing a saturated config without evidence.",
            patch={},
        )

    dominant_failure = _dominant_failure(candidate_failures)
    dominant_root_cause = _dominant_root_cause(candidate_evidence)

    if dominant_failure in {"invalid_action", "no_op_loop"}:
        return AdvisorProposal(
            hypothesis_id="hyp_retry_invalid_or_noop",
            summary="Enable a conservative retry policy for invalid-action or no-progress failures.",
            rationale=f"Candidate failures are dominated by `{dominant_failure}`, which may be recoverable with one bounded retry.",
            expected_effect="Improve success rate on recoverable interaction failures with a small latency increase.",
            risk="May hide deeper policy issues and can increase step count on tasks that are already looping.",
            patch={"retry_policy": {"enabled": True, "max_retries": 1}},
        )

    if dominant_root_cause == "terminal_output_blindness":
        return AdvisorProposal(
            hypothesis_id="hyp_investigate_terminal_observation",
            summary="Keep the candidate config and inspect terminal observation failure before increasing budget again.",
            rationale="Failure evidence points to terminal output blindness, so more steps would likely extend the command loop without fixing state visibility.",
            expected_effect="Identify whether the terminal task needs an observation extraction fix or should remain a documented baseline limitation.",
            risk="Does not immediately improve terminal success until the observation issue is addressed.",
            patch={},
        )

    if dominant_failure in {"timeout", "max_steps"}:
        return AdvisorProposal(
            hypothesis_id="hyp_extend_step_budget",
            summary="Increase the step budget for tasks that appear budget-limited.",
            rationale=f"Candidate failures are dominated by `{dominant_failure}`, suggesting the agent may need more interaction budget.",
            expected_effect="Improve completion rate on longer tasks.",
            risk="May increase latency and can worsen looping behavior if failures are not actually budget-limited.",
            patch={"max_steps": EXTENDED_STEP_BUDGET},
        )

    if dominant_failure == "zero_score":
        root_causes = _root_cause_summary(candidate_evidence)
        evidence_note = f" Candidate evidence points to: {root_causes}." if root_causes else ""
        return AdvisorProposal(
            hypothesis_id="hyp_investigate_unclassified_failures",
            summary="Keep the candidate config and classify remaining zero-score failures before changing config again.",
            rationale="`zero_score` is an outcome label, not an actionable root cause, so another bounded config patch would be weakly supported."
            + evidence_note,
            expected_effect="Avoid speculative or no-op patches while directing the next work toward better failure evidence.",
            risk="Does not immediately improve success rate until the residual failures are classified more precisely.",
            patch={},
        )

    return AdvisorProposal(
        hypothesis_id="hyp_conservative_retry",
        summary="Enable one retry as a conservative next configuration.",
        rationale="No single actionable failure type dominates, so use the smallest bounded patch that can recover transient failures.",
        expected_effect="Small chance of recovering transient failures without changing the core agent policy.",
        risk="Limited expected impact if failures are caused by perception or planning errors.",
        patch={"retry_policy": {"enabled": True, "max_retries": 1}},
    )


def _dominant_failure(failures: dict[str, int]) -> str | None:
    if not failures:
        return None
    return max(failures.items(), key=lambda item: item[1])[0]


def _dominant_root_cause(evidence: list[FailureEvidence]) -> str | None:
    if not evidence:
        return None
    return Counter(item.root_cause for item in evidence).most_common(1)[0][0]


def _root_cause_summary(evidence: list[FailureEvidence]) -> str:
    counts = Counter(item.root_cause for item in evidence)
    return ", ".join(f"{root_cause}={count}" for root_cause, count in counts.most_common())


def _has_efficiency_gain(delta: dict[str, float]) -> bool:
    return (
        delta.get("avg_latency_sec", 0.0) <= LATENCY_IMPROVEMENT_SEC
        or delta.get("avg_input_tokens", 0.0) <= TOKEN_IMPROVEMENT
        or delta.get("avg_output_tokens", 0.0) <= TOKEN_IMPROVEMENT
    )
