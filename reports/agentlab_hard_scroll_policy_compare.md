# Compare Report: relay_gpt54_hard_retry_hyp_extend_step_budget vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit

- Task set: `miniwob_agentlab_hard`
- Compared tasks: `8`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.625 | 0.750 | 0.125 |
| avg_normalized_score | 0.625 | 0.750 | 0.125 |
| avg_step_count | 7.88 | 7.88 | 0.00 |
| avg_latency_sec | 33.72 | 32.24 | -1.48 |
| avg_input_tokens | 20784.50 | 20514.25 | -270.25 |
| avg_output_tokens | 632.12 | 635.75 | 3.62 |
| avg_llm_call_count | 7.88 | 7.88 | 0.00 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.00 | 0.00 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 1 | 1 |
| `zero_score` | 2 | 1 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| baseline | `browsergym/miniwob.social-media-all#seed=26` | `missed_scroll_target` | medium | status=failed<br>failure_type=zero_score<br>step_count=8 | Test a scroll-before-submit policy or trace check for hidden remaining targets. |
| baseline | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=30 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |
| candidate | `browsergym/miniwob.grid-coordinate#seed=25` | `coordinate_click_miss` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Add coordinate-aware click evidence or a point-targeting policy before changing generic retry settings. |
| candidate | `browsergym/miniwob.terminal#seed=27` | `terminal_output_blindness` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=30 | Inspect terminal traces and add an observation policy for command output before increasing budget again. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.social-media-all#seed=26`: 0.00 -> 1.00
