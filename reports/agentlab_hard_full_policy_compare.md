# Compare Report: relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_combined vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.875 | 1.000 | 0.125 |
| avg_normalized_score | 0.875 | 1.000 | 0.125 |
| avg_step_count | 6.12 | 6.25 | 0.12 |
| avg_latency_sec | 23.34 | 35.98 | 12.63 |
| avg_input_tokens | 21063.00 | 20464.12 | -598.88 |
| avg_output_tokens | 511.25 | 503.25 | -8.00 |
| avg_llm_call_count | 6.12 | 6.25 | 0.12 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.38 | 0.62 | 0.25 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `zero_score` | 1 | 0 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.grid-coordinate#seed=25`: 0.00 -> 1.00
