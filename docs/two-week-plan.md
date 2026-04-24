# Two-Week Delivery Plan

## Objective

Finish a two-week MVP for a browser-agent optimization project whose core value is an optimization advisor on top of a baseline browser agent.

The baseline browser agent is not the main innovation. The main innovation is the advisor layer that turns benchmark outcomes into the next configuration hypothesis.

## Product statement

This project is:

- a benchmark runner for browser-agent configurations
- a structured compare and failure-analysis layer
- an optimization advisor that proposes the next browser-agent config patch

This project is not:

- a new general-purpose browser agent
- a generic evaluation platform for all agents
- a dashboard-heavy product in the first two weeks

## Two-week MVP

By the end of week 2, the system should support this loop:

`task set -> baseline config -> variant config -> compare report -> advisor suggestion -> generated config patch -> rerun`

## Architecture

```text
configs/agents/*.yaml
datasets/miniwob/*.yaml
        |
        v
  Browser benchmark runner
        |
        +--> AgentLab generic_agent adapter
        +--> BrowserGym launcher
        |
        v
 normalized run records
        |
        v
 compare + failure analysis
        |
        v
 optimization advisor
        |
        v
 candidate config patch
```

## Modules

### `runner`

- run one config on one task set
- collect normalized outputs

### `compare`

- compare two experiment outputs
- compute deltas and regressions

### `failure_analysis`

- aggregate failure types
- identify dominant failure clusters

### `advisor`

- read a structured compare report
- produce bounded optimization hypotheses
- emit a candidate config patch

### `patcher`

- take advisor output and generate a concrete next config file

## Advisor design

The advisor is the key part of the project.

### Preferred long-term multi-agent design

- `Analyst Agent`
- `Hypothesis Agent`
- `Critic Agent`

### Two-week implementation rule

Use the lightest version that can close the loop:

- start with one advisor agent if needed
- keep inputs and outputs explicitly structured
- ensure the output is a bounded patch, not an essay

## Advisor input schema

```json
{
  "baseline_config_id": "baseline",
  "candidate_config_id": "variant_retry",
  "taskset_id": "miniwob_smoke",
  "metrics": {
    "baseline": {},
    "candidate": {},
    "delta": {}
  },
  "regressions": [],
  "improvements": [],
  "failure_summary": {}
}
```

## Advisor output schema

```json
{
  "hypothesis_id": "hyp_001",
  "summary": "Enable one retry after invalid action for click-heavy tasks",
  "rationale": "Invalid-action failures dominate regressions",
  "expected_effect": "higher success rate with small latency increase",
  "risk": "may increase looping on long tasks",
  "patch": {
    "retry_policy": {
      "enabled": true,
      "max_retries": 1
    }
  }
}
```

## Week 1 deliverables

- repository skeleton
- `AgentLab` adapter
- `MiniWoB++` smoke task set
- baseline and variant config files
- experiment runner
- compare report

## Week 2 deliverables

- first advisor implementation
- bounded patch generation
- patch-to-config materialization
- one closed-loop before/after experiment report

## MVP success criteria

- at least one `MiniWoB++` task set can run end to end
- two configs can be compared reproducibly
- compare report includes regressions and failure summary
- advisor can generate at least one valid next-step config patch
- rerunning the advisor-generated patch completes successfully
