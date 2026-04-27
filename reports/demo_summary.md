# BAELOOP Demo Summary

## 1. Hard-Slice Optimization Ladder

| Stage | Config | Success Rate | Regressions |
|---|---|---:|---:|
| retry baseline | `relay_gpt54_hard_retry` | 0.500 | 0 |
| step budget | `relay_gpt54_hard_retry_hyp_extend_step_budget` | 0.625 | 0 |
| scroll policy | `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit` | 0.750 | 0 |
| scroll + terminal | `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_combined` | 0.875 | 0 |
| full policy | `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click` | 1.000 | 0 |
| same-slice repeat | `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click` | 1.000 | 0 |

## 2. Broad Validation

| Baseline | Candidate | Success Delta | Improvements | Regressions |
|---|---|---:|---:|---:|
| `relay_gpt54_hard_retry` | `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click` | +0.200 | 4 | 0 |

## 3. Control Boundary

| Baseline Success | Candidate Success | Improvements | Regressions | Interpretation |
|---:|---:|---:|---:|---|
| 0.438 | 0.500 | 1 | 0 | remaining failures are coordinate/control capability boundaries |

## 4. Advisor Holdout Eval

| Advisor | Avg Score | Direction | Safe Patch | Evidence | Boundary |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |
| `llm-v2` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## 5. Current Project Claim

- BAELOOP is not a prompt-only browser agent project.
- The browser agent is the execution substrate; the project highlight is the optimization advisor.
- `llm-v2` wins by combining LLM stages, deterministic reference, and evidence-maturity selection.
- The next demo risk to address is broader holdout coverage and clearer advisor input/output examples.
