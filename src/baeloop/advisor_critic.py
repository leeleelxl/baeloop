from __future__ import annotations

from baeloop.models import AdvisorAnalysis, AdvisorProposal, Intervention

TERMINAL_INTERACTION_ROOT_CAUSES = {
    "terminal_input_action_mismatch",
    "terminal_output_blindness",
}


def critique_intervention(
    analysis: AdvisorAnalysis,
    intervention: Intervention,
) -> AdvisorProposal:
    decision = "accepted"
    notes = _critic_notes(analysis, intervention)

    if intervention.kind in {"config_patch", "retry_policy", "action_policy", "observation_policy"} and not intervention.patch:
        decision = "rejected"
        notes.append("patch-bearing intervention kind must include a bounded patch")

    return AdvisorProposal(
        hypothesis_id=intervention.id,
        summary=intervention.summary,
        rationale=intervention.rationale,
        expected_effect=intervention.expected_effect,
        risk=intervention.risk,
        patch=intervention.patch if decision == "accepted" else {},
        intervention=intervention,
        critic_decision=decision,
        critic_notes=notes,
    )


def _critic_notes(analysis: AdvisorAnalysis, intervention: Intervention) -> list[str]:
    notes: list[str] = []
    if intervention.patch:
        notes.append("bounded patch present")
    else:
        notes.append("no patch emitted; recommendation is hold or investigation")

    if analysis.regression_count:
        notes.append(f"candidate has {analysis.regression_count} regressions")
    else:
        notes.append("no regressions detected")

    if analysis.evidence_count:
        notes.append(f"uses {analysis.evidence_count} candidate failure evidence records")
    else:
        notes.append("no candidate failure evidence records")

    if (
        intervention.id == "hyp_extend_step_budget"
        and analysis.dominant_root_cause in TERMINAL_INTERACTION_ROOT_CAUSES
    ):
        notes.append("step-budget patch would not address terminal interaction failure")

    return notes
