from __future__ import annotations

from collections import Counter

from baeloop.models import AdvisorAnalysis, ComparisonReport

LATENCY_IMPROVEMENT_SEC = -0.5
TOKEN_IMPROVEMENT = -100.0


def analyze_report(report: ComparisonReport) -> AdvisorAnalysis:
    candidate_failures = report.failure_summary.get("candidate", {})
    candidate_evidence = report.failure_evidence.get("candidate", [])
    candidate_root_causes = Counter(item.root_cause for item in candidate_evidence)
    delta = report.metrics["delta"]
    assert isinstance(delta, dict)

    return AdvisorAnalysis(
        candidate_failures=candidate_failures,
        candidate_root_causes=dict(candidate_root_causes),
        dominant_failure=_dominant(candidate_failures),
        dominant_root_cause=_dominant(candidate_root_causes),
        quality_not_worse=(
            report.regression_count == 0
            and delta["success_rate"] >= 0
            and delta["avg_normalized_score"] >= 0
        ),
        efficiency_gain=_has_efficiency_gain(delta),
        success_rate_delta=delta["success_rate"],
        avg_score_delta=delta["avg_normalized_score"],
        regression_count=report.regression_count,
        evidence_count=len(candidate_evidence),
    )


def _dominant(counts: dict[str, int] | Counter[str]) -> str | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _has_efficiency_gain(delta: dict[str, float]) -> bool:
    return (
        delta.get("avg_latency_sec", 0.0) <= LATENCY_IMPROVEMENT_SEC
        or delta.get("avg_input_tokens", 0.0) <= TOKEN_IMPROVEMENT
        or delta.get("avg_output_tokens", 0.0) <= TOKEN_IMPROVEMENT
    )
