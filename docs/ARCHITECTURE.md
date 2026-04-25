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

Inputs:

- `AdvisorAnalysis`

Outputs:

- `Intervention`

### Critic Agent

The critic checks whether a proposed intervention is supported and bounded. It rejects patch-bearing interventions that do not contain an executable patch and records critique notes.

Current implementation:

- `src/baeloop/advisor_critic.py`
- adds `critic_decision` and `critic_notes` to proposals

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

## Intervention Model

`Intervention` is the structured unit of optimization. It records:

- `kind`: config patch, retry policy, action policy, observation policy, hold, or investigation
- `patch`: bounded executable patch when applicable
- `target_root_causes`: evidence targets such as `missed_scroll_target`
- `supported_by`: compact evidence references
- expected effect and risk

The current patch materializer handles config-level interventions and a bounded `action_policy` patch. The AgentLab adapter currently implements one action policy, `scroll_before_submit`. Observation-policy interventions are still planned and should be implemented only when they can be verified with a rerun.

## Current Evidence

The hard MiniWoB run currently shows:

- `relay_gpt54_hard_retry`: 0.500 success rate
- `generated_agentlab_hard_advisor` with `max_steps: 30`: 0.625 success rate
- improvement: `book-flight` moved from 0.0 to 1.0
- remaining root causes:
  - `coordinate_click_miss`
  - `missed_scroll_target`
  - `terminal_input_action_mismatch`

## Next Engineering Milestone

The first non-prompt experiment targets `missed_scroll_target` with an action-policy intervention: `scroll-before-submit`.

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
