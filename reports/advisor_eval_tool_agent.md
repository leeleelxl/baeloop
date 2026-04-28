# Advisor Evaluation

- Case suite: `tool`
- Cases: `4`
- Include LLM: `False`
- Include LLM v2: `False`
- Include Tool Agent: `True`
- Include Tool Pretool: `True`

## Summary

| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `tool-agent` | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `tool-agent-pretool` | 4 | 0.833 | 0.000 | 1.000 | 1.000 | 1.000 |

## Cases

| Case | Advisor | Mode | Source | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| `tool_terminal_probe_to_policy` | `deterministic` | `deterministic` | `-` | `hyp_terminal_keyboard_type` | 1.000 | yes | yes | yes | yes | expected=terminal_policy<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `tool_terminal_probe_to_policy` | `tool-agent-pretool` | `tool-agent-pretool` | `pretool_investigation` | `hyp_tool_investigate_before_patch` | 0.833 | no | yes | yes | yes | expected=terminal_policy<br>mode=tool-agent-pretool<br>failed_direction_match<br>uses 2 candidate failure evidence records |
| `tool_terminal_probe_to_policy` | `tool-agent` | `tool-agent` | `tool_agent` | `hyp_terminal_keyboard_type` | 1.000 | yes | yes | yes | yes | expected=terminal_policy<br>mode=tool-agent<br>uses 2 candidate failure evidence records |
| `tool_compose_scroll_terminal` | `deterministic` | `deterministic` | `-` | `hyp_combine_scroll_and_terminal_policies` | 1.000 | yes | yes | yes | yes | expected=compose_policies<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `tool_compose_scroll_terminal` | `tool-agent-pretool` | `tool-agent-pretool` | `pretool_investigation` | `hyp_tool_investigate_before_patch` | 0.833 | no | yes | yes | yes | expected=compose_policies<br>mode=tool-agent-pretool<br>failed_direction_match<br>uses 2 candidate failure evidence records |
| `tool_compose_scroll_terminal` | `tool-agent` | `tool-agent` | `tool_agent` | `hyp_combine_scroll_and_terminal_policies` | 1.000 | yes | yes | yes | yes | expected=compose_policies<br>mode=tool-agent<br>uses 2 candidate failure evidence records |
| `tool_grid_probe_to_policy` | `deterministic` | `deterministic` | `-` | `hyp_grid_coordinate_click` | 1.000 | yes | yes | yes | yes | expected=grid_policy<br>mode=deterministic<br>uses 1 candidate failure evidence records |
| `tool_grid_probe_to_policy` | `tool-agent-pretool` | `tool-agent-pretool` | `pretool_investigation` | `hyp_tool_investigate_before_patch` | 0.833 | no | yes | yes | yes | expected=grid_policy<br>mode=tool-agent-pretool<br>failed_direction_match<br>uses 1 candidate failure evidence records |
| `tool_grid_probe_to_policy` | `tool-agent` | `tool-agent` | `tool_agent` | `hyp_grid_coordinate_click` | 1.000 | yes | yes | yes | yes | expected=grid_policy<br>mode=tool-agent<br>uses 1 candidate failure evidence records |
| `tool_control_boundary_probe` | `deterministic` | `deterministic` | `-` | `hyp_probe_coordinate_control` | 1.000 | yes | yes | yes | yes | expected=probe_coordinate_control<br>mode=deterministic<br>uses 8 candidate failure evidence records |
| `tool_control_boundary_probe` | `tool-agent-pretool` | `tool-agent-pretool` | `pretool_investigation` | `hyp_tool_investigate_before_patch` | 0.833 | no | yes | yes | yes | expected=probe_coordinate_control<br>mode=tool-agent-pretool<br>failed_direction_match<br>uses 8 candidate failure evidence records |
| `tool_control_boundary_probe` | `tool-agent` | `tool-agent` | `tool_agent` | `hyp_probe_coordinate_control` | 1.000 | yes | yes | yes | yes | expected=probe_coordinate_control<br>mode=tool-agent<br>uses 8 candidate failure evidence records |
