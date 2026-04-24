# Compare Report: baseline vs variant_retry

- Task set: `miniwob_smoke`
- Compared tasks: `5`
- Regression count: `0`
- Improvement count: `2`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.400 | 0.800 | 0.400 |
| avg_normalized_score | 0.400 | 0.800 | 0.400 |
| avg_step_count | 9.00 | 8.80 | -0.20 |
| avg_latency_sec | 5.88 | 5.98 | 0.10 |

## Candidate Failures

- `timeout`: 1

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.drag-box#seed=4`: 0.00 -> 1.00
- `browsergym/miniwob.enter-text#seed=2`: 0.00 -> 1.00
