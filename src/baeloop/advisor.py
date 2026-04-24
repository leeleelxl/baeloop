from __future__ import annotations

from baeloop.models import AdvisorProposal, ComparisonReport


def propose_patch(report: ComparisonReport) -> AdvisorProposal:
    candidate_failures = report.failure_summary.get("candidate", {})
    dominant_failure = _dominant_failure(candidate_failures)

    if dominant_failure in {"invalid_action", "no_op_loop"}:
        return AdvisorProposal(
            hypothesis_id="hyp_retry_invalid_or_noop",
            summary="Enable a conservative retry policy for invalid-action or no-progress failures.",
            rationale=f"Candidate failures are dominated by `{dominant_failure}`, which may be recoverable with one bounded retry.",
            expected_effect="Improve success rate on recoverable interaction failures with a small latency increase.",
            risk="May hide deeper policy issues and can increase step count on tasks that are already looping.",
            patch={"retry_policy": {"enabled": True, "max_retries": 1}},
        )

    if dominant_failure in {"timeout", "max_steps"}:
        return AdvisorProposal(
            hypothesis_id="hyp_extend_step_budget",
            summary="Increase the step budget for tasks that appear budget-limited.",
            rationale=f"Candidate failures are dominated by `{dominant_failure}`, suggesting the agent may need more interaction budget.",
            expected_effect="Improve completion rate on longer tasks.",
            risk="May increase latency and can worsen looping behavior if failures are not actually budget-limited.",
            patch={"max_steps": 20},
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
