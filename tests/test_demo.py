from __future__ import annotations

from pathlib import Path

from baeloop.demo import render_demo_summary


def test_demo_summary_renders_current_project_story() -> None:
    summary = render_demo_summary(Path("reports"))

    assert "# BAELOOP Demo Summary" in summary
    assert "Hard-Slice Optimization Ladder" in summary
    assert "`llm-v2`" in summary
    assert "remaining failures are coordinate/control capability boundaries" in summary
