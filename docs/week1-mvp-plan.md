# Week 1 MVP Plan

## Goal

Build a CLI-first MVP that can run a baseline browser agent on a selected `MiniWoB++` subset, store run results, and compare two agent configurations.

The first week is about proving the optimization loop:

`task set -> baseline config -> variant config -> batch runs -> compare report`

## User story

A developer wants to know whether a new browser-agent config is actually better than the current one.

They should be able to:

1. choose a benchmark task set
2. choose two configs
3. run both configs
4. get a report showing improvements, regressions, and major failure types

## Functional scope

### In scope

- local benchmark task registry
- local agent config registry
- adapter for `AgentLab generic_agent`
- experiment runner
- result persistence
- config comparison report

### Out of scope

- web dashboard
- multi-user support
- distributed scheduling
- custom browser agent implementation
- LLM-as-judge
- WorkArena / Mind2Web / OSWorld integration

## Week-1 architecture

```text
configs/agents/*.yaml
datasets/miniwob/*.yaml
        |
        v
    CLI commands
        |
        v
 Experiment Runner
        |
        +--> Agent adapter (AgentLab generic_agent)
        |
        +--> BrowserGym task launcher
        |
        v
   Run Recorder
        |
        +--> run metadata
        +--> benchmark score
        +--> timing / steps
        +--> failure type
        |
        v
  Compare + Report Generator
```

## Proposed repository structure

```text
AGENTS.md
docs/
  week1-mvp-plan.md
src/
  baeloop/
    __init__.py
    cli.py
    models.py
    config_loader.py
    task_loader.py
    runner.py
    recorder.py
    compare.py
    report.py
    adapters/
      __init__.py
      agentlab.py
configs/
  agents/
    baseline.yaml
    variant_retry.yaml
datasets/
  miniwob/
    taskset_smoke.yaml
runs/
reports/
pyproject.toml
README.md
```

## Core modules

### `adapters/agentlab.py`

Responsibility:

- adapt local config into an `AgentLab generic_agent` run
- launch one benchmark task
- normalize raw outputs into project-level run results

### `runner.py`

Responsibility:

- iterate over tasks in a task set
- run one config over the full task set
- collect per-task run outputs

### `recorder.py`

Responsibility:

- persist experiment metadata
- persist per-task run results
- emit machine-readable JSON for later comparisons

### `compare.py`

Responsibility:

- compare two completed experiment runs
- compute deltas on success rate, score, step count, and latency
- identify regressions and improvements

### `report.py`

Responsibility:

- generate a human-readable markdown summary
- generate a JSON artifact for downstream analysis

## Data model sketch

### Agent config

```yaml
id: baseline
agent: agentlab_generic
model: gpt-4o-mini
prompt_version: v1
max_steps: 15
retry_policy:
  enabled: false
observation_mode: text
```

### Task set

```yaml
id: miniwob_smoke
benchmark: miniwob
tasks:
  - env_id: browsergym/miniwob.click-button
    seed: 1
    max_steps: 10
  - env_id: browsergym/miniwob.enter-text
    seed: 2
    max_steps: 10
```

### Run result

```json
{
  "experiment_id": "exp_2026_04_20_001",
  "config_id": "baseline",
  "task_id": "browsergym/miniwob.click-button#seed=1",
  "status": "success",
  "normalized_score": 1.0,
  "step_count": 4,
  "latency_sec": 8.42,
  "failure_type": null
}
```

## CLI surface

```bash
baeloop run --config configs/agents/baseline.yaml --taskset datasets/miniwob/taskset_smoke.yaml
baeloop run --config configs/agents/variant_retry.yaml --taskset datasets/miniwob/taskset_smoke.yaml
baeloop compare --base runs/exp_base.json --new runs/exp_variant.json
```

## MVP success criteria for week 1

- run at least one `MiniWoB++` smoke task end-to-end
- run a 10-task task set with one baseline config
- run the same task set with one variant config
- produce one markdown compare report
- report at least:
  - success rate
  - average normalized score
  - average step count
  - average latency
  - regression count

## Recommended first config comparison

Use a very small and concrete experiment:

- `baseline`: default config
- `variant_retry`: same config + one simple retry rule after invalid action or no-op behavior

This is a good first experiment because it is easy to explain and likely to produce measurable differences.

## Risks

- `AgentLab` integration details may be heavier than expected
- BrowserGym environment setup may take time
- Different benchmarks may expose different result schemas

## Mitigation

- keep week 1 limited to `MiniWoB++`
- keep the adapter thin and benchmark-specific
- persist a normalized project-level run schema immediately
