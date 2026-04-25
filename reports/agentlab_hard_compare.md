# Compare Report: relay_gpt54_hard vs relay_gpt54_hard_retry

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `0`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.500 | 0.500 | 0.000 |
| avg_normalized_score | 0.500 | 0.500 | 0.000 |
| avg_step_count | 7.38 | 7.75 | 0.38 |
| avg_latency_sec | 28.98 | 28.96 | -0.02 |
| avg_input_tokens | 21168.75 | 22730.62 | 1561.88 |
| avg_output_tokens | 608.50 | 628.00 | 19.50 |
| avg_llm_call_count | 7.38 | 7.75 | 0.38 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.00 | 0.00 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 2 | 2 |
| `zero_score` | 2 | 2 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.book-flight#seed=21` | `autocomplete_validation_loop` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Prefer autocomplete-selection checks or a higher step budget only if trace evidence shows near-completion. |
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=6 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |
| candidate | `browsergym/miniwob.book-flight#seed=21` | `autocomplete_validation_loop` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Prefer autocomplete-selection checks or a higher step budget only if trace evidence shows near-completion. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| candidate | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=9 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| candidate | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- None
