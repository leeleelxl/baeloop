# Coordinate/Control Probe Plan

- Source report: `reports/agentlab_control_full_policy_compare.json`
- Task set: `miniwob_agentlab_control`
- Baseline config: `relay_gpt54_hard_retry`
- Candidate config: `relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_hyp_grid_coordinate_click`
- Control failure records: `8`
- Affected tasks: `8`
- Ready for policy: `false`

## Primitive Plan

| Priority | Primitive | Root Causes | Tasks | Ready |
|---:|---|---|---:|---|
| 10 | `coordinate_click_surface_probe` | `coordinate_click_surface_mismatch` | 1 | `false` |
| 20 | `coordinate_drag_vector_probe` | `coordinate_drag_surface_mismatch`, `directional_drag_control_mismatch` | 4 | `false` |
| 30 | `coordinate_draw_stroke_probe` | `coordinate_draw_surface_mismatch` | 1 | `false` |
| 40 | `list_drag_semantics_probe` | `list_drag_semantics_mismatch` | 2 | `false` |

## coordinate_click_surface_probe

- Goal: Test whether coordinate clicks can solve SVG-internal controls that are not reliable bid targets.
- Affected tasks: `browsergym/miniwob.click-pie#seed=49`

Probe inputs:

- goal text
- pruned HTML
- element bounding boxes
- SVG geometry or target element geometry

Candidate action sequences:

- bid click on exposed SVG/control root as the negative baseline
- coordinate click on parsed target center
- two-step coordinate click when the control needs opening plus target selection

Success criteria:

- A coordinate sequence reaches reward >= 1.0 or strictly beats the bid baseline.
- Coordinates are derived from DOM geometry or goal text, not fixed seed pixels.
- The same extraction logic works across at least two seeds or related tasks before becoming policy.

Policy gate:

- Fire only when target geometry is parsed with finite coordinates.
- Keep max interventions low and task-family gated.
- Do not alter unrelated click tasks in broad validation.

Current blockers:

- No live browser probe artifact has been generated for this primitive yet.
- No bounded action policy should be emitted until reward or DOM evidence exists.

## coordinate_drag_vector_probe

- Goal: Test whether coordinate drag vectors solve sliders, resize handles, shape drags, and directional controls.
- Affected tasks: `browsergym/miniwob.drag-circle#seed=40`, `browsergym/miniwob.drag-cube#seed=41`, `browsergym/miniwob.drag-single-shape#seed=45`, `browsergym/miniwob.resize-textarea#seed=46`

Probe inputs:

- goal text
- source/target element bounding boxes
- control orientation
- candidate drag distances

Candidate action sequences:

- bid drag or repeated bid clicks as the negative baseline
- mouse drag from source center to target center
- directional drag by bounded vector lengths in both axes
- compressed slider drag from handle center toward parsed target value

Success criteria:

- At least one coordinate drag sequence improves reward over bid-level actions.
- The drag vector is computed from geometry, orientation, or target value rather than exact task id.
- The probe records distance, start point, end point, reward, and action errors.

Policy gate:

- Fire only on controls with detected draggable geometry.
- Limit attempts per control and stop after positive reward or no movement.
- Do not hard-code per-seed distances.

Current blockers:

- No live browser probe artifact has been generated for this primitive yet.
- No bounded action policy should be emitted until reward or DOM evidence exists.

## coordinate_draw_stroke_probe

- Goal: Test whether a small set of coordinate strokes can solve SVG drawing tasks.
- Affected tasks: `browsergym/miniwob.draw-circle#seed=48`

Probe inputs:

- goal text
- SVG canvas bounding box
- shape hints from task name or page geometry
- normalized stroke templates

Candidate action sequences:

- bid action baseline if any drawing bid is exposed
- single straight mouse drag for line tasks
- multi-point stroke template mapped into the SVG canvas for simple shape tasks

Success criteria:

- A generic stroke template solves or strictly improves at least one drawing task.
- Stroke points are normalized to the canvas box rather than fixed pixels.
- The probe reports enough geometry to explain why the stroke succeeded or failed.

Policy gate:

- Only propose a policy after line and shape probes have separate evidence.
- Keep stroke templates bounded and inspectable.
- Do not encode per-task answer shapes beyond generic line/circle templates.

Current blockers:

- No live browser probe artifact has been generated for this primitive yet.
- No bounded action policy should be emitted until reward or DOM evidence exists.

## list_drag_semantics_probe

- Goal: Test source/target/drop semantics for list and grid reordering tasks.
- Affected tasks: `browsergym/miniwob.drag-items#seed=42`, `browsergym/miniwob.drag-items-grid#seed=43`

Probe inputs:

- goal text
- source item bbox
- target item bbox
- list slot geometry
- post-action DOM order

Candidate action sequences:

- bid drag source to target as the negative baseline
- coordinate drag source center to target center
- coordinate drag source center to drop slot before or after target
- reverse-direction drag when task semantics indicate swapping

Success criteria:

- A coordinate sequence changes DOM order in the intended direction or improves reward.
- The report distinguishes no movement, wrong order, and action execution errors.
- The same semantic rule applies to list and grid variants before becoming policy.

Policy gate:

- Fire only when source and target items are parsed unambiguously.
- Require post-action order evidence before claiming maturity.
- Do not special-case item labels or seed-specific positions.

Current blockers:

- No live browser probe artifact has been generated for this primitive yet.
- No bounded action policy should be emitted until reward or DOM evidence exists.

## No Task-Specific Hand-Code Boundary

- Do not store seed-specific pixel coordinates.
- Do not branch on exact MiniWoB task id inside an action policy except for coarse task-family gating.
- Do not use LLM-as-judge for probe success; use reward, DOM state, or action errors.
- Do not turn a probe into a policy until at least one generic primitive has browser evidence.
- Do not increase prompt or step budget to hide missing control primitives.

## Next Steps

- Implement the highest-priority live probe first; do not create an action policy yet.
- Persist probe JSON and Markdown with action sequence, geometry, reward, and action-error evidence.
- Only feed the probe artifact back into tool-agent after the probe has browser evidence.
