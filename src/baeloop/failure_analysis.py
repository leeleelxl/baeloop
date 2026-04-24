from __future__ import annotations

from collections import Counter

from baeloop.models import RunRecord


def infer_failure_type(record: RunRecord) -> str | None:
    if record.status == "success":
        return None
    if record.failure_type:
        return record.failure_type
    if record.status in {"timeout", "max_steps", "error"}:
        return record.status
    if record.step_count <= 1 and record.normalized_score == 0:
        return "early_stop"
    if record.normalized_score == 0:
        return "zero_score"
    return "partial_score"


def summarize_failures(records: list[RunRecord]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for record in records:
        failure_type = infer_failure_type(record)
        if failure_type:
            counter[failure_type] += 1
    return dict(counter)
