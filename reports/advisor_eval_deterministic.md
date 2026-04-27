# Advisor Evaluation

- Cases: `8`
- Include LLM: `False`

## Summary

| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 8 | 0.896 | 0.750 | 1.000 | 0.875 | 0.750 |

## Cases

| Case | Advisor | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| `hard_retry_no_gain` | `deterministic` | `hyp_extend_step_budget` | 0.833 | yes | yes | no | yes | expected=extend_step_budget<br>mode=deterministic<br>failed_uses_failure_evidence<br>uses 4 candidate failure evidence records |
| `hard_budget_needs_evidence` | `deterministic` | `hyp_scroll_before_submit` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `hard_scroll_to_terminal` | `deterministic` | `hyp_terminal_keyboard_type` | 1.000 | yes | yes | yes | yes | expected=terminal_policy<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `hard_terminal_regresses_scroll` | `deterministic` | `hyp_combine_scroll_and_terminal_policies` | 1.000 | yes | yes | yes | yes | expected=compose_policies<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `hard_combined_remaining_coordinate` | `deterministic` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `hard_full_quality_winner` | `deterministic` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `broad_full_quality_winner` | `deterministic` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `control_boundary` | `deterministic` | `hyp_probe_coordinate_control` | 1.000 | yes | yes | yes | yes | expected=probe_coordinate_control<br>mode=deterministic<br>uses 8 candidate failure evidence records |
