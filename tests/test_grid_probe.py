from baeloop.grid_probe import (
    GridCoordinateProbeReport,
    GridCoordinateProbeResult,
    GridCoordinateState,
    map_svg_point_to_screen,
    render_grid_coordinate_probe_markdown,
)


def test_map_svg_point_to_screen_scales_svg_coordinates_to_bbox() -> None:
    assert map_svg_point_to_screen(
        svg_point=[105.0, 15.0],
        svg_extent=[0.0, 0.0, 150.0, 150.0],
        svg_bbox=[12.0, 162.0, 450.0, 450.0],
        bbox_scale=2.0,
    ) == [164, 104]


def test_grid_coordinate_probe_report_identifies_working_sequences() -> None:
    state = GridCoordinateState(
        goal="Click on the grid coordinate (1,2).",
        target_coordinate=(1, 2),
        target_click_point=[327, 207],
    )
    report = GridCoordinateProbeReport(
        task_name="browsergym/miniwob.grid-coordinate",
        seed=25,
        base_url="file:///tmp/miniwob/",
        results=[
            GridCoordinateProbeResult(
                name="svg_root_bid_click",
                action='click("13")',
                action_error="",
                initial_state=state,
                final_state=state,
                reward=0.0,
                terminated=True,
            ),
            GridCoordinateProbeResult(
                name="mapped_mouse_click",
                action="mouse_click(327, 207)",
                action_error="",
                initial_state=state,
                final_state=state,
                reward=1.0,
                terminated=True,
            ),
        ],
    )

    assert [result.name for result in report.working_results] == ["mapped_mouse_click"]


def test_render_grid_coordinate_probe_markdown_summarizes_geometry() -> None:
    state = GridCoordinateState(
        goal="Click on the grid coordinate (1,2).",
        target_coordinate=(1, 2),
        svg_bid="13",
        svg_bbox=[12.0, 162.0, 450.0, 450.0],
        svg_extent=[0.0, 0.0, 150.0, 150.0],
        target_svg_point=[105.0, 15.0],
        target_click_point=[327, 207],
    )
    report = GridCoordinateProbeReport(
        task_name="browsergym/miniwob.grid-coordinate",
        seed=25,
        base_url="file:///tmp/miniwob/",
        results=[
            GridCoordinateProbeResult(
                name="mapped_mouse_click",
                action="mouse_click(327, 207)",
                action_error="",
                initial_state=state,
                final_state=state,
                reward=1.0,
                terminated=True,
            )
        ],
    )

    markdown = render_grid_coordinate_probe_markdown(report)

    assert "| `mapped_mouse_click` | `mouse_click(327, 207)` | `-` | 1.00 | true |" in markdown
    assert "- SVG bid: `13`" in markdown
    assert "- Mapped click point: `[327, 207]`" in markdown
