# BAELOOP Architecture

BAELOOP is an agent optimization system for browser agents. It does not try to replace the browser agent. It treats the browser agent as an execution substrate and builds a reproducible optimization loop around benchmark evidence.

## Goal

Given a browser-agent configuration and a fixed benchmark task set, BAELOOP should:

1. Run the agent and persist normalized records.
2. Compare two configurations on the same tasks.
3. Extract task-level failure evidence.
4. Propose a bounded intervention.
5. Critique the intervention before materializing it.
6. Rerun and validate whether the intervention improves results without regressions.

This is intentionally broader than prompt engineering. Prompt changes are only one possible intervention type. The system is designed to support config, retry, action-policy, observation-policy, and investigation interventions.

## Closed Loop

```text
Browser Agent
  -> Benchmark Runner
  -> RunRecord JSONL
  -> Compare Report
  -> Failure Evidence
  -> Analyst Agent
  -> Hypothesis Agent
  -> Critic Agent
  -> Patch Generator
  -> Rerun and Compare
```

## Agent Roles

### Browser Agent

The browser agent acts in the environment. In the current implementation this is AgentLab's `generic_agent` running on BrowserGym/MiniWoB++.

Inputs:

- BrowserGym observation
- agent config
- task seed and task budget

Outputs:

- browser actions such as `click`, `fill`, `scroll`, and `noop`
- benchmark summary records

### Analyst Agent

The analyst runs after benchmark execution. It does not operate the browser. It reads compare reports and extracts factual deltas.

Current implementation:

- `src/baeloop/advisor_analysis.py`
- computes quality deltas, efficiency deltas, dominant failure types, and dominant root causes
- optional LLM-backed stage in `src/baeloop/llm_advisor.py` summarizes the same structured report with schema validation

Inputs:

- `ComparisonReport`
- failure taxonomy
- `FailureEvidence`

Outputs:

- `AdvisorAnalysis`

### Hypothesis Agent

The hypothesis agent maps evidence to candidate interventions. It should not emit free-form advice; it emits structured interventions.

Current implementation:

- `src/baeloop/advisor_hypothesis.py`
- maps failure evidence such as `autocomplete_validation_loop` or `terminal_input_action_mismatch` to bounded next steps
- optional LLM-backed stage in `src/baeloop/llm_advisor.py` emits an `Intervention` JSON object and must stay within allowed patch keys

Inputs:

- `AdvisorAnalysis`

Outputs:

- `Intervention`

### Critic Agent

The critic checks whether a proposed intervention is supported and bounded. It rejects patch-bearing interventions that do not contain an executable patch and records critique notes.

Current implementation:

- `src/baeloop/advisor_critic.py`
- adds `critic_decision` and `critic_notes` to proposals
- optional LLM-backed critic in `src/baeloop/llm_advisor.py` can reject proposals, but deterministic guardrails still validate patch boundaries

Inputs:

- `AdvisorAnalysis`
- `Intervention`

Outputs:

- `AdvisorProposal`

### Patch Generator

The patch generator materializes approved config patches.

Current implementation:

- `src/baeloop/patcher.py`
- validates allowed patch keys
- rejects non-empty no-op patches

Inputs:

- base agent config
- `AdvisorProposal`

Outputs:

- generated agent config

## Advisor Modes

BAELOOP currently supports three advisor modes through the same CLI command:

- `deterministic`: reproducible Python Analyst/Hypothesis/Critic stages used for tests and baseline behavior.
- `llm`: OpenAI-compatible streaming chat completions for Analyst, Hypothesis, and Critic roles.
- `llm-v2`: LLM Analyst/Hypothesis/Critic stages plus a deterministic-reference tool and evidence-maturity selector.

All modes output the same `AdvisorProposal` schema. The LLM modes are not allowed to mutate arbitrary config: they must emit an `Intervention`, pass Pydantic validation, and keep patch keys inside the patcher allowlist. If v1 returns invalid JSON, an unsupported patch, or an invalid critic decision, the system falls back to the deterministic advisor and records `advisor_mode=llm_fallback`. If v2 has a transient LLM failure, it falls back to its local evidence-maturity selector and records `advisor_mode=llm-v2-fallback`.

The v2 selector is the current decision layer that lets the agent beat the deterministic baseline:

- preserve deterministic proposals that are already evidence-mature, such as quality winners, terminal input fixes, composite policy fixes, and first non-terminal max-step budget patches
- force weak action-policy ideas such as `missed_scroll_target` or `coordinate_click_miss` into a probe/investigation when the report has not yet proven a bounded rewrite primitive
- keep control-heavy failures as capability-boundary probes rather than prompt or budget patches

## Advisor Evaluation Harness

The advisor layer is evaluated separately from browser execution through committed historical compare reports. This avoids claiming that a single generated patch is useful just because it sounds plausible.

Current implementation:

- `src/baeloop/advisor_eval.py`
- CLI: `baeloop eval-advisor`
- inputs: historical `ComparisonReport` JSON files
- outputs: `reports/advisor_eval_deterministic.*`, `reports/advisor_eval_llm.*`, and `reports/advisor_eval_llm_v2.*`

Each case scores whether the advisor output is schema-valid, critic-accepted, patch-safe, directionally aligned with the expected next step, grounded in failure evidence, and aware of capability boundaries. This is a decision-quality evaluation, not an LLM-as-judge benchmark.

Current 8-case result:

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.896 | 0.750 | 1.000 | 0.875 | 0.750 |
| `llm` | 0.875 | 0.625 | 0.875 | 1.000 | 0.875 |
| `llm-v2` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The v1 result is deliberately mixed: deterministic is more stable and patch-safe, while plain LLM uses evidence and boundary reasoning more consistently. The v2 result is the current target architecture working on the historical suite: it combines model-backed analysis with deterministic-reference and evidence-maturity selection, so it avoids over-patching when the evidence only justifies a probe.

Current 5-case holdout result:

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |
| `llm-v2` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The holdout suite includes saturated tasksets, efficiency winners, a remaining coordinate-action failure, and a timeout-budget mock case. The Markdown reports now expose `Mode` and `Source`, so a reviewer can see whether the final decision came from `deterministic_reference` or `investigation_fallback`.

## Intervention Model

`Intervention` is the structured unit of optimization. It records:

- `kind`: config patch, retry policy, action policy, observation policy, hold, or investigation
- `patch`: bounded executable patch when applicable
- `target_root_causes`: evidence targets such as `missed_scroll_target`
- `supported_by`: compact evidence references
- expected effect and risk

The current patch materializer handles config-level interventions and bounded `action_policy` patches. The AgentLab adapter implements three evidence-scoped policies:

- `scroll_before_submit`
- `terminal_keyboard_type`
- `grid_coordinate_click`

Observation-policy interventions are still planned and should be implemented only when they can be verified with a rerun.

## Current Evidence

The hard MiniWoB run currently shows:

- `relay_gpt54_hard_retry`: 0.500 success rate
- `generated_agentlab_hard_advisor` with `max_steps: 30`: 0.625 success rate
- `generated_agentlab_hard_scroll_policy`: 0.750 success rate
- `generated_agentlab_hard_combined_policy`: 0.875 success rate
- `generated_agentlab_hard_full_policy`: 1.000 success rate
- `generated_agentlab_hard_full_policy_repeat`: 1.000 success rate on a same-slice repeat run

The broader 20-task MiniWoB validation currently shows:

- `relay_gpt54_hard_retry`: 0.800 success rate
- `generated_agentlab_hard_full_policy`: 1.000 success rate
- broad comparison: 4 improvements, 0 regressions
- improved root causes: `autocomplete_validation_loop`, `coordinate_click_miss`, `missed_scroll_target`, and `terminal_input_action_mismatch`
- advisor output: `hyp_keep_quality_winner`, meaning the next optimization should expand coverage or target new evidence rather than mutate the saturated config

The 16-task control stress slice currently shows:

- `relay_gpt54_hard_retry`: 0.438 success rate
- `generated_agentlab_hard_full_policy`: 0.500 success rate
- control comparison: 1 improvement, 0 regressions
- improved task: `use-slider-2`
- remaining root causes: `coordinate_click_surface_mismatch`, `coordinate_drag_surface_mismatch`, `coordinate_draw_surface_mismatch`, `directional_drag_control_mismatch`, and `list_drag_semantics_mismatch`
- advisor output: `hyp_probe_coordinate_control`, meaning the next implementation should be a probe-backed coordinate control policy rather than another budget patch
- LLM advisor validation: `reports/agentlab_control_full_policy_llm_proposal.json` was generated with `--advisor-mode llm`, using the same report and preserving the bounded investigation recommendation

## Completed Non-Prompt Milestone

The current non-prompt experiments target three concrete action-surface failures:

- `missed_scroll_target`: submit was attempted before all hidden social targets were selected.
- `terminal_input_action_mismatch`: `fill(...)` did not mutate MiniWoB's custom terminal state.
- `coordinate_click_miss`: the agent identified the SVG point but could only bid-click the SVG root.

Acceptance criteria:

- intervention is represented as structured data
- prompt stays unchanged
- policy behavior is bounded and task/evidence scoped
- hard taskset rerun completes
- compare report shows whether success improves and whether regressions occur

Current result:

- `configs/agents/generated_agentlab_hard_scroll_policy.yaml` reached 0.750 success rate on the hard task set
- `social-media-all` improved from 0.0 to 1.0
- `avg_action_policy_interventions` was 0.0, so this run is evidence that the policy wrapper is safe on the hard slice, not causal proof that the rewrite caused the improvement
- `reports/agentlab_social_scroll_policy_replay.*` shows a counterfactual policy-fire check on the earlier failing `social-media-all` trace: step 7 would be rewritten from `click('104')` to `scroll(0, 621)`
- `reports/agentlab_terminal_trace_diagnosis.md` refines the remaining terminal failure as `terminal_input_action_mismatch`, making another step-budget increase weakly supported
- `reports/agentlab_terminal_action_probe.*` verifies the terminal fix surface: `fill(...)` does not populate the custom terminal, while `focus(...)` plus `keyboard_type(...)` does; the oracle check solves seed 27 with reward 1.0
- `reports/agentlab_grid_coordinate_probe.*` verifies the grid-coordinate action surface: bid-clicking the SVG root fails, while mapped `mouse_click(164, 104)` solves seed 25 with reward 1.0
- `configs/agents/generated_agentlab_hard_full_policy.yaml` combines all three bounded policies and solves 8/8 hard-slice tasks
- `reports/agentlab_hard_full_policy_repeat_compare.*` confirms a same-slice repeat run stayed at 1.000 success rate with no regressions
- `datasets/miniwob/taskset_agentlab_broad.yaml` expands validation to 20 tasks
- `reports/agentlab_broad_full_policy_compare.*` shows the full policy improves 0.800 -> 1.000 against the reference config on the broader slice with 0 regressions
