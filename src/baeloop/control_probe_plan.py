from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from baeloop.models import ComparisonReport, FailureEvidence


class ControlProbePrimitiveSpec(BaseModel):
    id: str
    priority: int
    root_causes: list[str]
    probe_goal: str
    probe_inputs: list[str]
    candidate_sequences: list[str]
    success_criteria: list[str]
    policy_gate: list[str]


class ControlProbePrimitivePlan(BaseModel):
    id: str
    priority: int
    target_root_causes: list[str]
    affected_tasks: list[str]
    probe_goal: str
    probe_inputs: list[str]
    candidate_sequences: list[str]
    success_criteria: list[str]
    policy_gate: list[str]
    ready_for_policy: bool = False
    blockers: list[str] = Field(default_factory=list)


class ControlProbePlanReport(BaseModel):
    source_report: str
    baseline_config_id: str
    candidate_config_id: str
    taskset_id: str
    control_failure_count: int
    affected_task_count: int
    ready_for_policy: bool
    primitive_plans: list[ControlProbePrimitivePlan]
    no_task_specific_handcode_boundary: list[str]
    next_steps: list[str]


CONTROL_PROBE_SPECS = [
    ControlProbePrimitiveSpec(
        id="coordinate_click_surface_probe",
        priority=10,
        root_causes=["coordinate_click_surface_mismatch"],
        probe_goal="Test whether coordinate clicks can solve SVG-internal controls that are not reliable bid targets.",
        probe_inputs=[
            "goal text",
            "pruned HTML",
            "element bounding boxes",
            "SVG geometry or target element geometry",
        ],
        candidate_sequences=[
            "bid click on exposed SVG/control root as the negative baseline",
            "coordinate click on parsed target center",
            "two-step coordinate click when the control needs opening plus target selection",
        ],
        success_criteria=[
            "A coordinate sequence reaches reward >= 1.0 or strictly beats the bid baseline.",
            "Coordinates are derived from DOM geometry or goal text, not fixed seed pixels.",
            "The same extraction logic works across at least two seeds or related tasks before becoming policy.",
        ],
        policy_gate=[
            "Fire only when target geometry is parsed with finite coordinates.",
            "Keep max interventions low and task-family gated.",
            "Do not alter unrelated click tasks in broad validation.",
        ],
    ),
    ControlProbePrimitiveSpec(
        id="coordinate_drag_vector_probe",
        priority=20,
        root_causes=[
            "coordinate_drag_surface_mismatch",
            "directional_drag_control_mismatch",
            "multi_slider_control_loop",
        ],
        probe_goal="Test whether coordinate drag vectors solve sliders, resize handles, shape drags, and directional controls.",
        probe_inputs=[
            "goal text",
            "source/target element bounding boxes",
            "control orientation",
            "candidate drag distances",
        ],
        candidate_sequences=[
            "bid drag or repeated bid clicks as the negative baseline",
            "mouse drag from source center to target center",
            "directional drag by bounded vector lengths in both axes",
            "compressed slider drag from handle center toward parsed target value",
        ],
        success_criteria=[
            "At least one coordinate drag sequence improves reward over bid-level actions.",
            "The drag vector is computed from geometry, orientation, or target value rather than exact task id.",
            "The probe records distance, start point, end point, reward, and action errors.",
        ],
        policy_gate=[
            "Fire only on controls with detected draggable geometry.",
            "Limit attempts per control and stop after positive reward or no movement.",
            "Do not hard-code per-seed distances.",
        ],
    ),
    ControlProbePrimitiveSpec(
        id="coordinate_draw_stroke_probe",
        priority=30,
        root_causes=["coordinate_draw_surface_mismatch"],
        probe_goal="Test whether a small set of coordinate strokes can solve SVG drawing tasks.",
        probe_inputs=[
            "goal text",
            "SVG canvas bounding box",
            "shape hints from task name or page geometry",
            "normalized stroke templates",
        ],
        candidate_sequences=[
            "bid action baseline if any drawing bid is exposed",
            "single straight mouse drag for line tasks",
            "multi-point stroke template mapped into the SVG canvas for simple shape tasks",
        ],
        success_criteria=[
            "A generic stroke template solves or strictly improves at least one drawing task.",
            "Stroke points are normalized to the canvas box rather than fixed pixels.",
            "The probe reports enough geometry to explain why the stroke succeeded or failed.",
        ],
        policy_gate=[
            "Only propose a policy after line and shape probes have separate evidence.",
            "Keep stroke templates bounded and inspectable.",
            "Do not encode per-task answer shapes beyond generic line/circle templates.",
        ],
    ),
    ControlProbePrimitiveSpec(
        id="list_drag_semantics_probe",
        priority=40,
        root_causes=["list_drag_semantics_mismatch"],
        probe_goal="Test source/target/drop semantics for list and grid reordering tasks.",
        probe_inputs=[
            "goal text",
            "source item bbox",
            "target item bbox",
            "list slot geometry",
            "post-action DOM order",
        ],
        candidate_sequences=[
            "bid drag source to target as the negative baseline",
            "coordinate drag source center to target center",
            "coordinate drag source center to drop slot before or after target",
            "reverse-direction drag when task semantics indicate swapping",
        ],
        success_criteria=[
            "A coordinate sequence changes DOM order in the intended direction or improves reward.",
            "The report distinguishes no movement, wrong order, and action execution errors.",
            "The same semantic rule applies to list and grid variants before becoming policy.",
        ],
        policy_gate=[
            "Fire only when source and target items are parsed unambiguously.",
            "Require post-action order evidence before claiming maturity.",
            "Do not special-case item labels or seed-specific positions.",
        ],
    ),
]

NO_TASK_SPECIFIC_HANDCODE_BOUNDARY = [
    "Do not store seed-specific pixel coordinates.",
    "Do not branch on exact MiniWoB task id inside an action policy except for coarse task-family gating.",
    "Do not use LLM-as-judge for probe success; use reward, DOM state, or action errors.",
    "Do not turn a probe into a policy until at least one generic primitive has browser evidence.",
    "Do not increase prompt or step budget to hide missing control primitives.",
]


def build_control_probe_plan(
    report: ComparisonReport,
    *,
    source_report: str = "",
) -> ControlProbePlanReport:
    control_evidence = _candidate_control_evidence(report)
    tasks_by_root: dict[str, set[str]] = defaultdict(set)
    for item in control_evidence:
        tasks_by_root[item.root_cause].add(item.task_id)

    primitive_plans = [
        _build_primitive_plan(spec, tasks_by_root)
        for spec in CONTROL_PROBE_SPECS
        if any(root in tasks_by_root for root in spec.root_causes)
    ]

    affected_tasks = sorted({item.task_id for item in control_evidence})
    return ControlProbePlanReport(
        source_report=source_report,
        baseline_config_id=report.baseline_config_id,
        candidate_config_id=report.candidate_config_id,
        taskset_id=report.taskset_id,
        control_failure_count=len(control_evidence),
        affected_task_count=len(affected_tasks),
        ready_for_policy=False,
        primitive_plans=primitive_plans,
        no_task_specific_handcode_boundary=NO_TASK_SPECIFIC_HANDCODE_BOUNDARY,
        next_steps=[
            "Implement the highest-priority live probe first; do not create an action policy yet.",
            "Persist probe JSON and Markdown with action sequence, geometry, reward, and action-error evidence.",
            "Only feed the probe artifact back into tool-agent after the probe has browser evidence.",
        ],
    )


def render_control_probe_plan_markdown(report: ControlProbePlanReport) -> str:
    lines = [
        "# Coordinate/Control Probe Plan",
        "",
        f"- Source report: `{report.source_report or '-'}`",
        f"- Task set: `{report.taskset_id}`",
        f"- Baseline config: `{report.baseline_config_id}`",
        f"- Candidate config: `{report.candidate_config_id}`",
        f"- Control failure records: `{report.control_failure_count}`",
        f"- Affected tasks: `{report.affected_task_count}`",
        f"- Ready for policy: `{str(report.ready_for_policy).lower()}`",
        "",
        "## Primitive Plan",
        "",
        "| Priority | Primitive | Root Causes | Tasks | Ready |",
        "|---:|---|---|---:|---|",
    ]
    for item in report.primitive_plans:
        lines.append(
            f"| {item.priority} | `{item.id}` | "
            f"{_inline_code_list(item.target_root_causes)} | {len(item.affected_tasks)} | "
            f"`{str(item.ready_for_policy).lower()}` |"
        )

    for item in report.primitive_plans:
        lines.extend(
            [
                "",
                f"## {item.id}",
                "",
                f"- Goal: {item.probe_goal}",
                f"- Affected tasks: {_inline_code_list(item.affected_tasks)}",
                "",
                "Probe inputs:",
                "",
                *[f"- {entry}" for entry in item.probe_inputs],
                "",
                "Candidate action sequences:",
                "",
                *[f"- {entry}" for entry in item.candidate_sequences],
                "",
                "Success criteria:",
                "",
                *[f"- {entry}" for entry in item.success_criteria],
                "",
                "Policy gate:",
                "",
                *[f"- {entry}" for entry in item.policy_gate],
                "",
                "Current blockers:",
                "",
                *[f"- {entry}" for entry in item.blockers],
            ]
        )

    lines.extend(
        [
            "",
            "## No Task-Specific Hand-Code Boundary",
            "",
            *[f"- {entry}" for entry in report.no_task_specific_handcode_boundary],
            "",
            "## Next Steps",
            "",
            *[f"- {entry}" for entry in report.next_steps],
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_control_evidence(report: ComparisonReport) -> list[FailureEvidence]:
    known_roots = {
        root
        for spec in CONTROL_PROBE_SPECS
        for root in spec.root_causes
    }
    return [
        item
        for item in report.failure_evidence.get("candidate", [])
        if item.root_cause in known_roots
    ]


def _build_primitive_plan(
    spec: ControlProbePrimitiveSpec,
    tasks_by_root: dict[str, set[str]],
) -> ControlProbePrimitivePlan:
    matched_roots = [root for root in spec.root_causes if root in tasks_by_root]
    affected_tasks = sorted(
        task for root in matched_roots for task in tasks_by_root[root]
    )
    return ControlProbePrimitivePlan(
        id=spec.id,
        priority=spec.priority,
        target_root_causes=matched_roots,
        affected_tasks=affected_tasks,
        probe_goal=spec.probe_goal,
        probe_inputs=spec.probe_inputs,
        candidate_sequences=spec.candidate_sequences,
        success_criteria=spec.success_criteria,
        policy_gate=spec.policy_gate,
        ready_for_policy=False,
        blockers=[
            "No live browser probe artifact has been generated for this primitive yet.",
            "No bounded action policy should be emitted until reward or DOM evidence exists.",
        ],
    )


def _inline_code_list(items: list[str]) -> str:
    if not items:
        return "-"
    return ", ".join(f"`{item}`" for item in items)
