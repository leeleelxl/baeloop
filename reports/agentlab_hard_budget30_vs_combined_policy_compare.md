# Compare Report: relay_gpt54_hard_retry_hyp_extend_step_budget vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_combined

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `2`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.625 | 0.875 | 0.250 |
| avg_normalized_score | 0.625 | 0.875 | 0.250 |
| avg_step_count | 7.88 | 6.12 | -1.75 |
| avg_latency_sec | 33.72 | 23.34 | -10.37 |
| avg_input_tokens | 20784.50 | 21063.00 | 278.50 |
| avg_output_tokens | 632.12 | 511.25 | -120.88 |
| avg_llm_call_count | 7.88 | 6.12 | -1.75 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.38 | 0.38 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 1 | 0 |
| `zero_score` | 2 | 1 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=8 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_input_action_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=30 | Inspect terminal traces and test a terminal-specific input action policy before increasing budget again. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.social-media-all#seed=26`: 0.00 -> 1.00
- `browsergym/miniwob.terminal#seed=27`: 0.00 -> 1.00
