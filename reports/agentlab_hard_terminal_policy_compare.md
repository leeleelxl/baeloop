# Compare Report: relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `1`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.750 | 0.750 | 0.000 |
| avg_normalized_score | 0.750 | 0.750 | 0.000 |
| avg_step_count | 7.88 | 4.00 | -3.88 |
| avg_latency_sec | 32.24 | 14.05 | -18.19 |
| avg_input_tokens | 20514.25 | 11431.25 | -9083.00 |
| avg_output_tokens | 635.75 | 301.38 | -334.38 |
| avg_llm_call_count | 7.88 | 4.00 | -3.88 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.25 | 0.25 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 1 | 0 |
| `zero_score` | 1 | 2 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_input_action_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=30 | Inspect terminal traces and test a terminal-specific input action policy before increasing budget again. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| candidate | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=4 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- `browsergym/miniwob.social-media-all#seed=26`: 1.00 -> 0.00

## Improvements

- `browsergym/miniwob.terminal#seed=27`: 0.00 -> 1.00
