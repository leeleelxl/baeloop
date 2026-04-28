# Advisor Evaluation

- Case suite: `holdout`
- Cases: `10`
- Include LLM: `False`
- Include LLM v2: `False`

## Summary

| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 10 | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |

## Cases

| Case | Advisor | Mode | Source | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| `holdout_core_saturated` | `deterministic` | `deterministic` | `-` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_challenge_efficiency_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_hard_repeat_efficiency_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_combined_vs_terminal_remaining_coordinate` | `deterministic` | `deterministic` | `-` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `holdout_mock_timeout_budget` | `deterministic` | `deterministic` | `-` | `hyp_extend_step_budget` | 1.000 | yes | yes | yes | yes | expected=extend_step_budget<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_agentlab_smoke_saturated` | `deterministic` | `deterministic` | `-` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_mock_advisor_quality_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_sample_retry_invalid_or_noop` | `deterministic` | `deterministic` | `-` | `hyp_retry_invalid_or_noop` | 1.000 | yes | yes | yes | yes | expected=retry_invalid_or_noop<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_budget30_to_combined_remaining_coordinate` | `deterministic` | `deterministic` | `-` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `holdout_hard_retry_to_full_quality_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
