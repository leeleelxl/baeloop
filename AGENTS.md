# Project Memory

This repository is for an Alibaba-style agent internship project to be finished in two weeks.

## Current project definition

- Project name: `Browser Agent Optimization Advisor`
- Core idea: the main value is not the browser agent itself, but an upper-layer agent system that analyzes benchmark results and proposes the next browser-agent configuration to try
- Baseline browser agent: `AgentLab` built-in `generic_agent`
- Benchmark environment: `BrowserGym`
- Initial benchmark: `MiniWoB++`
- Optional later benchmark: `WebArena-Verified`

## What the project should do

- Run a baseline browser agent on a fixed browser benchmark task set
- Compare multiple agent configurations on the same tasks
- Produce structured experiment results and failure taxonomy
- Feed those results into an optimization decision layer
- Let the decision layer propose the next candidate configuration

## Real project highlight

The project highlight is the optimization decision layer, not the benchmark runner alone.

The final story should be:

- a browser agent runs benchmark tasks
- an optimization advisor reads structured experiment results
- the advisor identifies likely failure patterns
- the advisor proposes a config patch for the next round

## Decision-layer architecture

The decision layer should evolve toward a multi-agent system.

### Preferred multi-agent roles

- `Analyst Agent`: summarizes experiment deltas and failure distribution
- `Hypothesis Agent`: proposes concrete optimization hypotheses
- `Critic Agent`: rejects weak or risky hypotheses and patches

### MVP policy

- do not build the full multi-agent system on day one
- two-week MVP may start from a single advisor agent if needed
- but the architecture should clearly leave room for `Analyst + Hypothesis + Critic`

## Explicit non-goals

- Do not build a brand-new browser agent first
- Do not build a general-purpose agent eval platform
- Do not make the first version depend on LLM-as-judge
- Do not start with WorkArena, Mind2Web, or OSWorld
- Do not start with a web dashboard; CLI-first is preferred for MVP

## Two-week scope

- Wrap `AgentLab generic_agent` behind a local adapter
- Define a local task registry for a selected `MiniWoB++` subset
- Define a local config registry for browser-agent variants
- Run experiments and persist normalized run records locally
- Generate compare reports between two configs
- Build the first optimization advisor that reads the compare report and emits a candidate config patch

## Metrics to track first

- `success_rate`
- `avg_normalized_score`
- `avg_step_count`
- `avg_latency_sec`
- `regression_count`
- `failure_taxonomy`

## Initial stack decisions

- Language: Python
- Package manager: `uv`
- CLI: `Typer`
- Validation/config: `Pydantic`
- Local persistence for MVP: `SQLite` or structured `JSONL` files
- Reports: Markdown + JSON

## Design principles

- Keep the first version benchmark-driven and reproducible
- Prefer deterministic benchmark checks over free-form judging
- Treat configuration comparison as the optimization substrate
- Keep the system modular so a custom browser agent can replace the baseline later
- Keep the decision layer constrained: it should output bounded config patches, not vague advice

## Two-week delivery target

### Week 1

- benchmark runner on `MiniWoB++`
- config registry
- normalized run records
- compare report

### Week 2

- first optimization advisor
- candidate config patch generation
- one closed-loop experiment:
  - baseline run
  - compare report
  - advisor-generated config patch
  - rerun and compare

## Target final demo

The final demo should show:

1. a baseline browser-agent config running on a fixed task set
2. a compare report that highlights regressions and dominant failures
3. an optimization advisor that proposes the next config patch
4. a rerun showing whether the proposed patch improved the result
