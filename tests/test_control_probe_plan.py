from pathlib import Path

from baeloop.control_probe_plan import (
    build_control_probe_plan,
    render_control_probe_plan_markdown,
)
from baeloop.io import read_model_json
from baeloop.models import ComparisonReport


def test_control_probe_plan_groups_candidate_control_failures() -> None:
    report = read_model_json(
        Path("reports/agentlab_control_full_policy_compare.json"),
        ComparisonReport,
    )

    plan = build_control_probe_plan(
        report,
        source_report="reports/agentlab_control_full_policy_compare.json",
    )

    assert plan.ready_for_policy is False
    assert plan.control_failure_count == 8
    assert plan.affected_task_count == 8
    assert [item.id for item in plan.primitive_plans] == [
        "coordinate_click_surface_probe",
        "coordinate_drag_vector_probe",
        "coordinate_draw_stroke_probe",
        "list_drag_semantics_probe",
    ]
    assert plan.primitive_plans[1].target_root_causes == [
        "coordinate_drag_surface_mismatch",
        "directional_drag_control_mismatch",
    ]
    assert all(not item.ready_for_policy for item in plan.primitive_plans)


def test_render_control_probe_plan_markdown_exposes_boundaries() -> None:
    report = read_model_json(
        Path("reports/agentlab_control_full_policy_compare.json"),
        ComparisonReport,
    )
    plan = build_control_probe_plan(report)

    markdown = render_control_probe_plan_markdown(plan)

    assert "# Coordinate/Control Probe Plan" in markdown
    assert "`coordinate_drag_vector_probe`" in markdown
    assert "No Task-Specific Hand-Code Boundary" in markdown
    assert "Do not store seed-specific pixel coordinates." in markdown
    assert "Ready for policy: `false`" in markdown
