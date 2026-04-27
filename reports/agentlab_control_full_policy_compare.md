# Compare Report: relay_gpt54_hard_retry vs relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click

- Task set: `miniwob_agentlab_control`
- Compared tasks: `16`
- Regression count: `0`
- Improvement count: `1`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| success_rate | 0.438 | 0.500 | 0.062 |
| avg_normalized_score | 0.438 | 0.500 | 0.062 |
| avg_step_count | 6.94 | 5.12 | -1.81 |
| avg_latency_sec | 31.09 | 22.56 | -8.53 |
| avg_input_tokens | 12486.44 | 9334.38 | -3152.06 |
| avg_output_tokens | 776.50 | 568.31 | -208.19 |
| avg_llm_call_count | 6.94 | 5.12 | -1.81 |
| avg_agent_retry_count | 0.00 | 0.00 | 0.00 |
| avg_busted_retry_count | 0.00 | 0.00 | 0.00 |
| avg_action_policy_interventions | 0.00 | 0.00 | 0.00 |

## Failure Taxonomy

| Failure Type | Baseline | Candidate |
|---|---:|---:|
| `max_steps` | 3 | 1 |
| `zero_score` | 6 | 7 |

## Failure Evidence

| Side | Task | Root Cause | Confidence | Evidence | Suggested Action |
|---|---|---|---|---|---|
| baseline | `browsergym/miniwob.click-pie#seed=49` | `coordinate_click_surface_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Probe coordinate clicks on the spreader and target slice before proposing another budget patch. |
| baseline | `browsergym/miniwob.drag-circle#seed=40` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=8 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |
| baseline | `browsergym/miniwob.drag-cube#seed=41` | `directional_drag_control_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Probe directional coordinate drags for cube rotation before increasing budget. |
| baseline | `browsergym/miniwob.drag-items#seed=42` | `list_drag_semantics_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Probe whether list reorder expects source-to-target, target-to-source, or coordinate drop semantics. |
| baseline | `browsergym/miniwob.drag-items-grid#seed=43` | `list_drag_semantics_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Probe whether list reorder expects source-to-target, target-to-source, or coordinate drop semantics. |
| baseline | `browsergym/miniwob.drag-single-shape#seed=45` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=3 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |
| baseline | `browsergym/miniwob.draw-circle#seed=48` | `coordinate_draw_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=3 | Probe coordinate drag/drawing primitives before changing prompt or step budget. |
| baseline | `browsergym/miniwob.resize-textarea#seed=46` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=11 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |
| baseline | `browsergym/miniwob.use-slider-2#seed=35` | `multi_slider_control_loop` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Probe slider handle targeting and action compression before increasing the generic step budget. |
| candidate | `browsergym/miniwob.click-pie#seed=49` | `coordinate_click_surface_mismatch` | medium | status=max_steps<br>failure_type=max_steps<br>step_count=20 | Probe coordinate clicks on the spreader and target slice before proposing another budget patch. |
| candidate | `browsergym/miniwob.drag-circle#seed=40` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=2 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |
| candidate | `browsergym/miniwob.drag-cube#seed=41` | `directional_drag_control_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=9 | Probe directional coordinate drags for cube rotation before increasing budget. |
| candidate | `browsergym/miniwob.drag-items#seed=42` | `list_drag_semantics_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Probe whether list reorder expects source-to-target, target-to-source, or coordinate drop semantics. |
| candidate | `browsergym/miniwob.drag-items-grid#seed=43` | `list_drag_semantics_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=1 | Probe whether list reorder expects source-to-target, target-to-source, or coordinate drop semantics. |
| candidate | `browsergym/miniwob.drag-single-shape#seed=45` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=3 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |
| candidate | `browsergym/miniwob.draw-circle#seed=48` | `coordinate_draw_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=6 | Probe coordinate drag/drawing primitives before changing prompt or step budget. |
| candidate | `browsergym/miniwob.resize-textarea#seed=46` | `coordinate_drag_surface_mismatch` | medium | status=failed<br>failure_type=zero_score<br>step_count=9 | Probe coordinate drag actions and add a bounded coordinate-drag policy only after the probe succeeds. |

## Missing Tasks

- Missing in baseline: None
- Missing in candidate: None

## Regressions

- None

## Improvements

- `browsergym/miniwob.use-slider-2#seed=35`: 0.00 -> 1.00
