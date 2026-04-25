from __future__ import annotations

from baeloop.failure_analysis import collect_failure_evidence, summarize_failures
from baeloop.models import ComparisonReport, FailureEvidence, MetricSummary, RunRecord, TaskDelta

SCORE_DELTA_THRESHOLD = 1e-9


def compute_metrics(records: list[RunRecord]) -> MetricSummary:
    if not records:
        return MetricSummary(
            task_count=0,
            success_rate=0.0,
            avg_normalized_score=0.0,
            avg_step_count=0.0,
            avg_latency_sec=0.0,
            failure_taxonomy={},
        )

    count = len(records)
    success_count = sum(1 for record in records if record.status == "success")
    return MetricSummary(
        task_count=count,
        success_rate=success_count / count,
        avg_normalized_score=sum(record.normalized_score for record in records) / count,
        avg_step_count=sum(record.step_count for record in records) / count,
        avg_latency_sec=sum(record.latency_sec for record in records) / count,
        avg_input_tokens=_avg_diagnostic(records, "input_tokens"),
        avg_output_tokens=_avg_diagnostic(records, "output_tokens"),
        avg_llm_call_count=_avg_diagnostic(records, "llm_call_count"),
        avg_agent_retry_count=_avg_diagnostic(records, "agent_retry_count"),
        avg_busted_retry_count=_avg_diagnostic(records, "busted_retry_count"),
        avg_action_policy_interventions=_avg_diagnostic(records, "action_policy_interventions"),
        failure_taxonomy=summarize_failures(records),
    )


def _avg_diagnostic(records: list[RunRecord], key: str) -> float:
    values = [
        value
        for record in records
        if isinstance((value := record.diagnostics.get(key)), int | float)
    ]
    if not values:
        return 0.0
    return sum(float(value) for value in values) / len(values)


def _index_by_task(records: list[RunRecord]) -> dict[str, RunRecord]:
    indexed: dict[str, RunRecord] = {}
    for record in records:
        if record.task_id in indexed:
            raise ValueError(f"Duplicate task_id in run records: {record.task_id}")
        indexed[record.task_id] = record
    return indexed


def _single_config_id(records: list[RunRecord], label: str) -> str:
    config_ids = sorted({record.config_id for record in records})
    if len(config_ids) != 1:
        raise ValueError(f"{label} records must have exactly one config_id, got: {config_ids}")
    return config_ids[0]


def build_comparison_report(
    baseline_records: list[RunRecord],
    candidate_records: list[RunRecord],
    taskset_id: str,
) -> ComparisonReport:
    if not baseline_records:
        raise ValueError("Baseline records are empty")
    if not candidate_records:
        raise ValueError("Candidate records are empty")

    baseline_config_id = _single_config_id(baseline_records, "Baseline")
    candidate_config_id = _single_config_id(candidate_records, "Candidate")
    baseline_by_task = _index_by_task(baseline_records)
    candidate_by_task = _index_by_task(candidate_records)
    common_task_ids = sorted(set(baseline_by_task) & set(candidate_by_task))
    if not common_task_ids:
        raise ValueError("No overlapping task_id values between baseline and candidate")
    missing_in_baseline = sorted(set(candidate_by_task) - set(baseline_by_task))
    missing_in_candidate = sorted(set(baseline_by_task) - set(candidate_by_task))

    regressions: list[TaskDelta] = []
    improvements: list[TaskDelta] = []
    for task_id in common_task_ids:
        baseline = baseline_by_task[task_id]
        candidate = candidate_by_task[task_id]
        delta = TaskDelta(
            task_id=task_id,
            baseline_status=baseline.status,
            candidate_status=candidate.status,
            baseline_score=baseline.normalized_score,
            candidate_score=candidate.normalized_score,
            score_delta=candidate.normalized_score - baseline.normalized_score,
        )
        if (
            (baseline.status == "success" and candidate.status != "success")
            or delta.score_delta < -SCORE_DELTA_THRESHOLD
        ):
            regressions.append(delta)
        elif (
            (baseline.status != "success" and candidate.status == "success")
            or delta.score_delta > SCORE_DELTA_THRESHOLD
        ):
            improvements.append(delta)

    baseline_common_records = [baseline_by_task[task_id] for task_id in common_task_ids]
    candidate_common_records = [candidate_by_task[task_id] for task_id in common_task_ids]
    baseline_metrics = compute_metrics(baseline_common_records)
    candidate_metrics = compute_metrics(candidate_common_records)
    delta_metrics = {
        "success_rate": candidate_metrics.success_rate - baseline_metrics.success_rate,
        "avg_normalized_score": candidate_metrics.avg_normalized_score
        - baseline_metrics.avg_normalized_score,
        "avg_step_count": candidate_metrics.avg_step_count - baseline_metrics.avg_step_count,
        "avg_latency_sec": candidate_metrics.avg_latency_sec - baseline_metrics.avg_latency_sec,
        "avg_input_tokens": candidate_metrics.avg_input_tokens - baseline_metrics.avg_input_tokens,
        "avg_output_tokens": candidate_metrics.avg_output_tokens - baseline_metrics.avg_output_tokens,
        "avg_llm_call_count": candidate_metrics.avg_llm_call_count
        - baseline_metrics.avg_llm_call_count,
        "avg_agent_retry_count": candidate_metrics.avg_agent_retry_count
        - baseline_metrics.avg_agent_retry_count,
        "avg_busted_retry_count": candidate_metrics.avg_busted_retry_count
        - baseline_metrics.avg_busted_retry_count,
        "avg_action_policy_interventions": candidate_metrics.avg_action_policy_interventions
        - baseline_metrics.avg_action_policy_interventions,
    }
    return ComparisonReport(
        baseline_config_id=baseline_config_id,
        candidate_config_id=candidate_config_id,
        taskset_id=taskset_id,
        compared_task_count=len(common_task_ids),
        missing_in_baseline=missing_in_baseline,
        missing_in_candidate=missing_in_candidate,
        metrics={
            "baseline": baseline_metrics,
            "candidate": candidate_metrics,
            "delta": delta_metrics,
        },
        regression_count=len(regressions),
        regressions=regressions,
        improvements=improvements,
        failure_summary={
            "baseline": baseline_metrics.failure_taxonomy,
            "candidate": candidate_metrics.failure_taxonomy,
        },
        failure_evidence={
            "baseline": collect_failure_evidence(baseline_common_records),
            "candidate": collect_failure_evidence(candidate_common_records),
        },
    )


def render_markdown(report: ComparisonReport) -> str:
    baseline = report.metrics["baseline"]
    candidate = report.metrics["candidate"]
    delta = report.metrics["delta"]
    assert isinstance(baseline, MetricSummary)
    assert isinstance(candidate, MetricSummary)
    assert isinstance(delta, dict)

    lines = [
        f"# Compare Report: {report.baseline_config_id} vs {report.candidate_config_id}",
        "",
        f"- Task set: `{report.taskset_id}`",
        f"- Compared tasks: `{report.compared_task_count}`",
        f"- Regression count: `{report.regression_count}`",
        f"- Improvement count: `{len(report.improvements)}`",
        "",
        "## Metrics",
        "",
        "| Metric | Baseline | Candidate | Delta |",
        "|---|---:|---:|---:|",
        f"| success_rate | {baseline.success_rate:.3f} | {candidate.success_rate:.3f} | {delta['success_rate']:.3f} |",
        f"| avg_normalized_score | {baseline.avg_normalized_score:.3f} | {candidate.avg_normalized_score:.3f} | {delta['avg_normalized_score']:.3f} |",
        f"| avg_step_count | {baseline.avg_step_count:.2f} | {candidate.avg_step_count:.2f} | {delta['avg_step_count']:.2f} |",
        f"| avg_latency_sec | {baseline.avg_latency_sec:.2f} | {candidate.avg_latency_sec:.2f} | {delta['avg_latency_sec']:.2f} |",
        f"| avg_input_tokens | {baseline.avg_input_tokens:.2f} | {candidate.avg_input_tokens:.2f} | {delta['avg_input_tokens']:.2f} |",
        f"| avg_output_tokens | {baseline.avg_output_tokens:.2f} | {candidate.avg_output_tokens:.2f} | {delta['avg_output_tokens']:.2f} |",
        f"| avg_llm_call_count | {baseline.avg_llm_call_count:.2f} | {candidate.avg_llm_call_count:.2f} | {delta['avg_llm_call_count']:.2f} |",
        f"| avg_agent_retry_count | {baseline.avg_agent_retry_count:.2f} | {candidate.avg_agent_retry_count:.2f} | {delta['avg_agent_retry_count']:.2f} |",
        f"| avg_busted_retry_count | {baseline.avg_busted_retry_count:.2f} | {candidate.avg_busted_retry_count:.2f} | {delta['avg_busted_retry_count']:.2f} |",
        f"| avg_action_policy_interventions | {baseline.avg_action_policy_interventions:.2f} | {candidate.avg_action_policy_interventions:.2f} | {delta['avg_action_policy_interventions']:.2f} |",
        "",
        "## Failure Taxonomy",
        "",
    ]
    baseline_failures = report.failure_summary.get("baseline", {})
    candidate_failures = report.failure_summary.get("candidate", {})
    failure_types = sorted(set(baseline_failures) | set(candidate_failures))
    if failure_types:
        lines.extend(
            [
                "| Failure Type | Baseline | Candidate |",
                "|---|---:|---:|",
            ]
        )
        for failure_type in failure_types:
            lines.append(
                f"| `{failure_type}` | {baseline_failures.get(failure_type, 0)} | {candidate_failures.get(failure_type, 0)} |"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Failure Evidence", ""])
    evidence_rows = _failure_evidence_rows(report)
    if evidence_rows:
        lines.extend(
            [
                "| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |",
                "|---|---|---|---|---|---|",
            ]
        )
        lines.extend(evidence_rows)
    else:
        lines.append("- None")

    lines.extend(["", "## Missing Tasks", ""])
    if report.missing_in_baseline:
        missing = ", ".join(f"`{task_id}`" for task_id in report.missing_in_baseline)
        lines.append(f"- Missing in baseline: {missing}")
    else:
        lines.append("- Missing in baseline: None")
    if report.missing_in_candidate:
        missing = ", ".join(f"`{task_id}`" for task_id in report.missing_in_candidate)
        lines.append(f"- Missing in candidate: {missing}")
    else:
        lines.append("- Missing in candidate: None")

    lines.extend(["", "## Regressions", ""])
    if report.regressions:
        for regression in report.regressions:
            lines.append(
                f"- `{regression.task_id}`: {regression.baseline_score:.2f} -> {regression.candidate_score:.2f}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Improvements", ""])
    if report.improvements:
        for improvement in report.improvements:
            lines.append(
                f"- `{improvement.task_id}`: {improvement.baseline_score:.2f} -> {improvement.candidate_score:.2f}"
            )
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _failure_evidence_rows(report: ComparisonReport) -> list[str]:
    rows: list[str] = []
    for side in ("baseline", "candidate"):
        for evidence in report.failure_evidence.get(side, []):
            rows.append(_format_failure_evidence_row(side, evidence))
    return rows


def _format_failure_evidence_row(side: str, evidence: FailureEvidence) -> str:
    signals = "<br>".join(_escape_table_cell(item) for item in evidence.evidence[:3])
    return (
        f"| {side} | `{evidence.task_id}` | `{evidence.root_cause}` | "
        f"{evidence.confidence} | {signals} | {_escape_table_cell(evidence.suggested_action)} |"
    )


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|")
