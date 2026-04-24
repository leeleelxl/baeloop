# Compare Report: baseline vs variant_retry

- Task set: `miniwob_smoke`
- Compared tasks: `5`
- Regression count: `1`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.400 | 0.400 | 0.000 |
| avg_normalized_score | 0.400 | 0.400 | 0.000 |
| avg_step_count | 9.00 | 9.60 | 0.60 |
| avg_latency_sec | 5.88 | 6.40 | 0.52 |

## Candidate Failures

- `invalid_action`: 1
- `no_op_loop`: 1
- `timeout`: 1

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- `browsergym/miniwob.choose-list#seed=3`: 1.00 -> 0.00

## Improvements

- `browsergym/miniwob.enter-text#seed=2`: 0.00 -> 1.00
