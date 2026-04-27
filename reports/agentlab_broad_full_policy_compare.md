# Compare Report: relay_gpt54_hard_retry vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click

- Task set: `miniwob_agentlab_broad`
- Compared tasks: `20`
- Regression count: `0`
- Improvement count: `4`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.800 | 1.000 | 0.200 |
| avg_normalized_score | 0.800 | 1.000 | 0.200 |
| avg_step_count | 4.45 | 4.35 | -0.10 |
| avg_latency_sec | 22.11 | 18.22 | -3.89 |
| avg_input_tokens | 11198.50 | 10311.30 | -887.20 |
| avg_output_tokens | 338.25 | 324.75 | -13.50 |
| avg_llm_call_count | 4.45 | 4.35 | -0.10 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.20 | 0.20 |

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
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=8 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
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
