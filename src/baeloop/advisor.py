from __future__ import annotations

from baeloop.advisor_analysis import analyze_report
from baeloop.advisor_critic import critique_intervention
from baeloop.advisor_hypothesis import propose_intervention
from baeloop.models import AdvisorProposal, ComparisonReport


def propose_patch(report: ComparisonReport) -> AdvisorProposal:
    analysis = analyze_report(report)
    intervention = propose_intervention(analysis)
    return critique_intervention(analysis, intervention)
