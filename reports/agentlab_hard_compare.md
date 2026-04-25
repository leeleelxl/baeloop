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

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 2 | 2 |
| `zero_score` | 2 | 2 |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- None
