# Compare Report: relay_gpt54_hard_retry vs relay_gpt54_hard_retry_hyp_extend_step_budget

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.500 | 0.625 | 0.125 |
| avg_normalized_score | 0.500 | 0.625 | 0.125 |
| avg_step_count | 7.75 | 7.88 | 0.12 |
| avg_latency_sec | 28.96 | 33.72 | 4.76 |
| avg_input_tokens | 22730.62 | 20784.50 | -1946.12 |
| avg_output_tokens | 628.00 | 632.12 | 4.12 |
| avg_llm_call_count | 7.75 | 7.88 | 0.12 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.00 | 0.00 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 2 | 1 |
| `zero_score` | 2 | 2 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.book-flight#seed=21` | `autocomplete_validation_loop` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Prefer autocomplete-selection checks or a higher step budget only if trace evidence shows near-completion. |
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=9 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| candidate | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=8 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| candidate | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=30 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.book-flight#seed=21`: 0.00 -> 1.00
