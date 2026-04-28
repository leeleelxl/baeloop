# Compare Report: relay_gpt54_hard_retry vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `4`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.500 | 1.000 | 0.500 |
| avg_normalized_score | 0.500 | 1.000 | 0.500 |
| avg_step_count | 7.75 | 6.25 | -1.50 |
| avg_latency_sec | 28.96 | 35.98 | 7.02 |
| avg_input_tokens | 22730.62 | 20464.12 | -2266.50 |
| avg_output_tokens | 628.00 | 503.25 | -124.75 |
| avg_llm_call_count | 7.75 | 6.25 | -1.50 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.62 | 0.62 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 2 | 0 |
| `zero_score` | 2 | 0 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.book-flight#seed=21` | `autocomplete_validation_loop` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Prefer autocomplete-selection checks or a higher step budget only if trace evidence shows near-completion. |
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=9 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_input_action_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Inspect terminal traces and test a terminal-specific input action policy before increasing budget again. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.book-flight#seed=21`: 0.00 -> 1.00
- `browsergym/miniwob.grid-coordinate#seed=25`: 0.00 -> 1.00
- `browsergym/miniwob.social-media-all#seed=26`: 0.00 -> 1.00
- `browsergym/miniwob.terminal#seed=27`: 0.00 -> 1.00
