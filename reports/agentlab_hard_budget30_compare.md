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

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 2 | 1 |
| `zero_score` | 2 | 2 |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.book-flight#seed=21`: 0.00 -> 1.00
