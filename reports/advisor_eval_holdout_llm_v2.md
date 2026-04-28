# Advisor Evaluation

- Case suite: `holdout`
- Cases: `10`
- Include LLM: `False`
- Include LLM v2: `True`

## Summary

| Advisor | Rows | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic` | 10 | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |
| `llm-v2` | 10 | 0.983 | 0.900 | 1.000 | 1.000 | 1.000 |

## Cases

| Case | Advisor | Mode | Source | Hypothesis | Score | Direction | Safe Patch | Evidence | Boundary | Notes |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| `holdout_core_saturated` | `deterministic` | `deterministic` | `-` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_core_saturated` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_challenge_efficiency_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_challenge_efficiency_winner` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_hard_repeat_efficiency_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_hard_repeat_efficiency_winner` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_keep_efficiency_winner` | 1.000 | yes | yes | yes | yes | expected=efficiency_winner<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_combined_vs_terminal_remaining_coordinate` | `deterministic` | `deterministic` | `-` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `holdout_combined_vs_terminal_remaining_coordinate` | `llm-v2` | `llm-v2` | `investigation_fallback` | `hyp_probe_before_action_policy` | 1.000 | yes | yes | yes | yes | expected=investigate<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_mock_timeout_budget` | `deterministic` | `deterministic` | `-` | `hyp_extend_step_budget` | 1.000 | yes | yes | yes | yes | expected=extend_step_budget<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_mock_timeout_budget` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_extend_step_budget` | 1.000 | yes | yes | yes | yes | expected=extend_step_budget<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_agentlab_smoke_saturated` | `deterministic` | `deterministic` | `-` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_agentlab_smoke_saturated` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_hold_config_expand_taskset` | 1.000 | yes | yes | yes | yes | expected=hold_expand_taskset<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_mock_advisor_quality_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_mock_advisor_quality_winner` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_sample_retry_invalid_or_noop` | `deterministic` | `deterministic` | `-` | `hyp_retry_invalid_or_noop` | 1.000 | yes | yes | yes | yes | expected=retry_invalid_or_noop<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_sample_retry_invalid_or_noop` | `llm-v2` | `llm-v2` | `llm_candidate` | `hold_variant_retry_miniwob_smoke` | 0.833 | no | yes | yes | yes | expected=retry_invalid_or_noop<br>mode=llm-v2<br>failed_direction_match<br>v2 final selector accepted evidence-mature intervention |
| `holdout_budget30_to_combined_remaining_coordinate` | `deterministic` | `deterministic` | `-` | `hyp_grid_coordinate_click` | 0.667 | no | yes | yes | no | expected=investigate<br>mode=deterministic<br>failed_direction_match<br>failed_boundary_awareness |
| `holdout_budget30_to_combined_remaining_coordinate` | `llm-v2` | `llm-v2` | `investigation_fallback` | `hyp_probe_before_action_policy` | 1.000 | yes | yes | yes | yes | expected=investigate<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
| `holdout_hard_retry_to_full_quality_winner` | `deterministic` | `deterministic` | `-` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=deterministic<br>no candidate failure evidence records |
| `holdout_hard_retry_to_full_quality_winner` | `llm-v2` | `llm-v2` | `deterministic_reference` | `hyp_keep_quality_winner` | 1.000 | yes | yes | yes | yes | expected=quality_winner<br>mode=llm-v2<br>v2 final selector accepted evidence-mature intervention |
