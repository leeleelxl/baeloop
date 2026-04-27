from __future__ import annotations

from collections import Counter

from baeloop.models import FailureEvidence, RunRecord


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


def collect_failure_evidence(records: list[RunRecord]) -> list[FailureEvidence]:
    evidence: list[FailureEvidence] = []
    for record in records:
        item = infer_failure_evidence(record)
        if item:
            evidence.append(item)
    return evidence


def infer_failure_evidence(record: RunRecord) -> FailureEvidence | None:
    failure_type = infer_failure_type(record)
    if not failure_type:
        return None

    task_id = record.task_id.lower()
    base_evidence = [
        f"status={record.status}",
        f"failure_type={failure_type}",
        f"step_count={record.step_count}",
        f"score={record.normalized_score:.2f}",
    ]

    if "grid-coordinate" in task_id and failure_type in {"zero_score", "early_stop"}:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="coordinate_click_miss",
            confidence="medium",
            evidence=[
                *base_evidence,
                "coordinate task failed after an SVG/grid click attempt",
            ],
            suggested_action="Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings.",
        )

    if "social-media-all" in task_id and failure_type == "zero_score":
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="missed_scroll_target",
            confidence="medium",
            evidence=[
                *base_evidence,
                "multi-item social task failed after several visible interactions",
            ],
            suggested_action="Test a scroll-before-submit policy or trace check for hidden remaining targets.",
        )

    if "terminal" in task_id and failure_type == "max_steps":
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="terminal_input_action_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "terminal task exhausted step budget while commands did not drive visible terminal state changes",
            ],
            suggested_action="Inspect terminal traces and test a terminal-specific input action policy before increasing budget again.",
        )

    if "book-flight" in task_id and failure_type == "max_steps":
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="autocomplete_validation_loop",
            confidence="medium",
            evidence=[
                *base_evidence,
                "flight form task exhausted budget while resolving autocomplete-backed fields",
            ],
            suggested_action="Prefer autocomplete-selection checks or a higher step budget only if trace evidence shows near-completion.",
        )

    if "use-slider-2" in task_id and failure_type in {"max_steps", "zero_score"}:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="multi_slider_control_loop",
            confidence="medium",
            evidence=[
                *base_evidence,
                "multi-slider task failed while repeatedly selecting or adjusting slider handles",
            ],
            suggested_action="Probe slider handle targeting and action compression before increasing the generic step budget.",
        )

    if "click-pie" in task_id and failure_type in {"max_steps", "zero_score"}:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="coordinate_click_surface_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "pie-menu target is inside an SVG control without a reliable bid-level click target",
            ],
            suggested_action="Probe coordinate clicks on the spreader and target slice before proposing another budget patch.",
        )

    if any(task in task_id for task in ("draw-line", "draw-circle")) and failure_type in {
        "zero_score",
        "max_steps",
    }:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="coordinate_draw_surface_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "drawing task needs a coordinate-level stroke inside the SVG canvas",
            ],
            suggested_action="Probe coordinate drag/drawing primitives before changing prompt or step budget.",
        )

    if any(
        task in task_id
        for task in ("drag-circle", "drag-single-shape", "resize-textarea")
    ) and failure_type in {"zero_score", "max_steps"}:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="coordinate_drag_surface_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "task requires a directional drag with distance, but bid-level drag lacks precise coordinates",
            ],
            suggested_action="Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds.",
        )

    if "drag-cube" in task_id and failure_type in {"zero_score", "max_steps"}:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="directional_drag_control_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "cube rotation needs directional drag magnitude rather than repeated element-to-element drags",
            ],
            suggested_action="Probe directional coordinate drags for cube rotation before increasing budget.",
        )

    if any(task in task_id for task in ("drag-items", "drag-items-grid")) and failure_type in {
        "zero_score",
        "max_steps",
    }:
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="list_drag_semantics_mismatch",
            confidence="medium",
            evidence=[
                *base_evidence,
                "list drag task failed despite exposed source and target items",
            ],
            suggested_action="Probe whether list reorder expects source-to-target, target-to-source, or coordinate drop semantics.",
        )

    if failure_type == "max_steps":
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="step_budget_exhausted",
            confidence="low",
            evidence=base_evidence,
            suggested_action="Inspect trace proximity to success before increasing step budget.",
        )

    if failure_type == "zero_score":
        return FailureEvidence(
            task_id=record.task_id,
            failure_type=failure_type,
            root_cause="unclassified_zero_score",
            confidence="low",
            evidence=base_evidence,
            suggested_action="Collect trace-level evidence before proposing another config patch.",
        )

    return FailureEvidence(
        task_id=record.task_id,
        failure_type=failure_type,
        root_cause=failure_type,
        confidence="low",
        evidence=base_evidence,
        suggested_action="Inspect task trace before selecting an optimization patch.",
    )
