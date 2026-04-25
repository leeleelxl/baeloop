# Compare Report: relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_combined

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.750 | 0.875 | 0.125 |
| avg_normalized_score | 0.750 | 0.875 | 0.125 |
| avg_step_count | 4.00 | 6.12 | 2.12 |
| avg_latency_sec | 14.05 | 23.34 | 9.29 |
| avg_input_tokens | 11431.25 | 21063.00 | 9631.75 |
| avg_output_tokens | 301.38 | 511.25 | 209.88 |
| avg_llm_call_count | 4.00 | 6.12 | 2.12 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.25 | 0.38 | 0.12 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `zero_score` | 2 | 1 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=4 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.social-media-all#seed=26`: 0.00 -> 1.00
