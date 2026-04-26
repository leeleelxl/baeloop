# Grid Coordinate Action Probe

- Task: `browsergym/miniwob.grid-coordinate`
- Seed: `25`
- Base URL: `file:///Users/lxl/lxl_code/hermes_lxl/external/miniwob-plusplus/miniwob/html/miniwob/`
- Working sequences: `1`

## Summary

| Sequence | Action | Error | Reward | Terminated | Target | Click Point |
|---|---|---|---:|---|---|---|
| `svg_root_bid_click` | `click("13")` | `-` | 0.00 | true | `(1, 2)` | `[164, 104]` |
| `mapped_mouse_click` | `mouse_click(164, 104)` | `-` | 1.00 | true | `(1, 2)` | `[164, 104]` |
| `circle_center_mouse_click` | `mouse_click(109, 69)` | `-` | 0.00 | false | `(1, 2)` | `[164, 104]` |

## Initial Geometry

- Goal: `Click on the grid coordinate (1,2).`
- SVG bid: `13`
- SVG bbox: `[12.0, 162.0, 450.0, 450.0]`
- SVG extent: `[0.0, 0.0, 150.0, 150.0]`
- Target SVG point: `[105.0, 15.0]`
- Target circle bbox: `[105.0, 65.0, 8.0, 8.0]`
- Mapped click point: `[164, 104]`