# Advisor Evaluation

- Cases: `8`
- Include LLM: `True`

## Summary

| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 8 | 0.896 | 0.750 | 1.000 | 0.875 | 0.750 |
| `llm` | 8 | 0.875 | 0.625 | 0.875 | 1.000 | 0.875 |

## Cases

| Case | Advisor | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| `hard_retry_no_gain` | `deterministic` | `hyp_extend_step_budget` | 0.833 | yes | yes | no | yes | expected=extend_step_budget<br>mode=deterministic<br>failed_uses_failure_evidence<br>uses 4 candidate failure evidence records |
| `hard_retry_no_gain` | `llm` | `investigate_unchanged_failure_modes_after_retry` | 0.833 | no | yes | yes | yes | expected=extend_step_budget<br>mode=llm<br>failed_direction_match<br>llm critic: Investigation-only intervention is appropriately bounded given current evidence. |
| `hard_budget_needs_evidence` | `deterministic` | `hyp_scroll_before_submit` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `hard_budget_needs_evidence` | `llm` | `hyp_scroll_before_submit` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=llm<br>failed_direction_match<br>failed_boundary_awareness |
| `hard_scroll_to_terminal` | `deterministic` | `hyp_terminal_keyboard_type` | 1.000 | yes | yes | yes | yes | expected=terminal_policy<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `hard_scroll_to_terminal` | `llm` | `hyp_terminal_keyboard_type` | 1.000 | yes | yes | yes | yes | expected=terminal_policy<br>mode=llm<br>llm critic: Targeted terminal-specific action policy is appropriately narrow given limited evidence and avoids unsupported broad changes. |
| `hard_terminal_regresses_scroll` | `deterministic` | `hyp_combine_scroll_and_terminal_policies` | 1.000 | yes | yes | yes | yes | expected=compose_policies<br>mode=deterministic<br>uses 2 candidate failure evidence records |
| `hard_terminal_regresses_scroll` | `llm` | `hyp_combine_scroll_and_terminal_policies` | 1.000 | yes | yes | yes | yes | expected=compose_policies<br>mode=llm<br>llm critic: risk is moderate due to composite policy interaction and only 8 compared tasks, but rejection is not warranted because intervention scope is constrained and evidence-aligned |
| `hard_combined_remaining_coordinate` | `deterministic` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `hard_combined_remaining_coordinate` | `llm` | `hyp_grid_coordinate_click` | 0.500 | no | no | yes | yes | expected=investigate<br>mode=llm<br>failed_critic_ok<br>failed_safe_patch |
| `hard_full_quality_winner` | `deterministic` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `hard_full_quality_winner` | `llm` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=llm<br>llm critic: No rejection condition triggered because there is no patch-bearing proposal to validate against allowed_patch_keys. |
| `broad_full_quality_winner` | `deterministic` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `broad_full_quality_winner` | `llm` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=llm<br>llm critic: No candidate-side failure evidence is present, so rejecting further patch-bearing changes is appropriate at this stage. |
| `control_boundary` | `deterministic` | `hyp_probe_coordinate_control` | 1.000 | yes | yes | yes | yes | expected=probe_coordinate_control<br>mode=deterministic<br>uses 8 candidate failure evidence records |
| `control_boundary` | `llm` | `hyp_probe_coordinate_control` | 1.000 | yes | yes | yes | yes | expected=probe_coordinate_control<br>mode=llm<br>llm critic: No regressions were observed on the evaluated slice, so holding current config while probing bounded coordinate-control hypotheses is reasonable. |
