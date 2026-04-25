# Compare Report: variant_retry vs variant_retry_hyp_extend_step_budget

- Task set: `miniwob_smoke`
- Compared tasks: `5`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.800 | 1.000 | 0.200 |
| avg_normalized_score | 0.800 | 1.000 | 0.200 |
| avg_step_count | 8.80 | 9.40 | 0.60 |
| avg_latency_sec | 5.98 | 6.28 | 0.30 |
| avg_input_tokens | 0.00 | 0.00 | 0.00 |
| avg_output_tokens | 0.00 | 0.00 | 0.00 |
| avg_llm_call_count | 0.00 | 0.00 | 0.00 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `timeout` | 1 | 0 |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.click-checkboxes#seed=5`: 0.00 -> 1.00
