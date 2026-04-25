# BAELOOP

Browser Agent Evaluation and Optimization Loop.

BAELOOP is an optimization layer for browser-agent experiments. It is not a replacement for AgentLab or BrowserGym. The first milestone is a reproducible loop over structured run records:

```text
run records -> compare report -> advisor proposal -> config patch -> rerun
```

## Current MVP

This repository currently implements the current dependency-light MVP:

- deterministic `mock` run adapter for smoke testing
- AgentLab/BrowserGym environment probe and executable MiniWoB smoke adapter
- normalized run-record schema
- compare report generation
- rule-based advisor proposal
- bounded config patch materialization
- sample configs and run records

AgentLab and BrowserGym integration is available behind the optional benchmark dependencies. The `mock` adapter is not a benchmark result; it exists to keep the optimization loop executable without browser dependencies.

Check whether the local environment has the real browser-agent dependencies:

```bash
uv run baeloop doctor --adapter agentlab --json-out reports/agentlab_doctor.json
```

By default, `doctor` imports the Python modules, checks whether Playwright Chromium is installed, and checks `MINIWOB_URL`. Use `--no-strict` for a lighter import-spec-only probe, `--skip-playwright-browser` when browser installation is intentionally deferred, or `--skip-miniwob-url` before MiniWoB++ static files are configured.

`agentlab` adapter execution now supports the built-in MiniWoB smoke model and OpenAI-compatible chat completion endpoints.

## Agent Architecture

BAELOOP is an upper-layer optimization agent system. It does not replace the browser agent; it uses a browser agent as the execution substrate and optimizes configurations around benchmark evidence.

Current architecture:

```text
AgentLab generic_agent -> RunRecord JSONL -> Compare Report -> Advisor -> Config Patch
```

The current advisor is a deterministic single-agent decision layer. It already has bounded inputs and outputs, but it is intentionally not a full multi-agent system yet.

Target architecture:

```text
Compare Report
  -> Analyst Agent      factual deltas, regressions, failure taxonomy
  -> Hypothesis Agent   bounded optimization hypotheses
  -> Critic Agent       reject weak or unsupported hypotheses
  -> Patch Generator    materialize approved config patches
```

The next milestone is better evidence for this advisor layer: broader tasksets and richer run diagnostics, not a dashboard or a new browser agent. The compare layer now tracks diagnostics such as average input tokens, output tokens, LLM calls, agent retries, and busted retries, so the advisor can reason about efficiency when success rates are saturated.

## MiniWoB++ Assets

Real AgentLab/BrowserGym runs use the optional benchmark dependencies:

```bash
uv sync --extra benchmark
uv run playwright install chromium
```

BrowserGym MiniWoB++ also needs local static HTML files:

```bash
git clone https://github.com/Farama-Foundation/miniwob-plusplus.git external/miniwob-plusplus
git -C external/miniwob-plusplus reset --hard 7fd85d71a4b60325c6585396ec4f48377d049838
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"
uv run baeloop doctor --adapter agentlab
```

The `external/miniwob-plusplus/` directory is intentionally ignored by git.

Run the real AgentLab adapter without an API key using AgentLab's built-in MiniWoB smoke model:

```bash
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"
uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/agentlab_cheat.yaml \
  --taskset datasets/miniwob/taskset_agentlab_smoke.yaml \
  --out runs/agentlab_cheat.jsonl
```

Running `configs/agents/baseline.yaml` with `--adapter agentlab` requires `OPENAI_API_KEY` because it uses an OpenAI-backed AgentLab generic agent.

For an OpenAI-compatible relay, use `configs/agents/relay_gpt54.yaml` and set `OHFI_API_KEY`:

```bash
export OHFI_API_KEY="sk-..."
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"
uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54.yaml \
  --taskset datasets/miniwob/taskset_agentlab_smoke.yaml \
  --out runs/agentlab_relay_gpt54.jsonl
```

Run a small real MiniWoB core loop with the relay-backed AgentLab adapter:

```bash
export OHFI_API_KEY="sk-..."
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_core.yaml \
  --taskset datasets/miniwob/taskset_agentlab_core.yaml \
  --out runs/agentlab_core_relay_gpt54.jsonl

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_core_retry.yaml \
  --taskset datasets/miniwob/taskset_agentlab_core.yaml \
  --out runs/agentlab_core_relay_gpt54_retry.jsonl

uv run baeloop compare \
  --base runs/agentlab_core_relay_gpt54.jsonl \
  --new runs/agentlab_core_relay_gpt54_retry.jsonl \
  --taskset-id miniwob_agentlab_core \
  --json-out reports/agentlab_core_compare.json \
  --markdown-out reports/agentlab_core_compare.md

uv run baeloop advise \
  --report reports/agentlab_core_compare.json \
  --out reports/agentlab_core_proposal.json

uv run baeloop patch \
  --base-config configs/agents/relay_gpt54_core_retry.yaml \
  --proposal reports/agentlab_core_proposal.json \
  --out configs/agents/generated_agentlab_core_advisor.yaml
```

The committed core report is intentionally small: both relay configs solve the three selected tasks, so the advisor emits a no-op patch and recommends expanding task coverage before changing the config again. This is expected behavior for a saturated task set and helps avoid unsupported optimization claims.

Run the next challenge task set when you want less saturated data:

```bash
export OHFI_API_KEY="sk-..."
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_challenge.yaml \
  --taskset datasets/miniwob/taskset_agentlab_challenge.yaml \
  --out runs/agentlab_challenge_relay_gpt54.jsonl

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_challenge_budget.yaml \
  --taskset datasets/miniwob/taskset_agentlab_challenge.yaml \
  --out runs/agentlab_challenge_relay_gpt54_budget.jsonl

uv run baeloop compare \
  --base runs/agentlab_challenge_relay_gpt54.jsonl \
  --new runs/agentlab_challenge_relay_gpt54_budget.jsonl \
  --taskset-id miniwob_agentlab_challenge \
  --json-out reports/agentlab_challenge_compare.json \
  --markdown-out reports/agentlab_challenge_compare.md
```

If the challenge set is still saturated, use the harder MiniWoB slice:

```bash
export OHFI_API_KEY="sk-..."
export MINIWOB_URL="file://$(pwd)/external/miniwob-plusplus/miniwob/html/miniwob/"

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_hard.yaml \
  --taskset datasets/miniwob/taskset_agentlab_hard.yaml \
  --out runs/agentlab_hard_relay_gpt54.jsonl

uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/relay_gpt54_hard_retry.yaml \
  --taskset datasets/miniwob/taskset_agentlab_hard.yaml \
  --out runs/agentlab_hard_relay_gpt54_retry.jsonl

uv run baeloop compare \
  --base runs/agentlab_hard_relay_gpt54.jsonl \
  --new runs/agentlab_hard_relay_gpt54_retry.jsonl \
  --taskset-id miniwob_agentlab_hard \
  --json-out reports/agentlab_hard_compare.json \
  --markdown-out reports/agentlab_hard_compare.md
```

## Quickstart

```bash
uv run baeloop run \
  --config configs/agents/baseline.yaml \
  --taskset datasets/miniwob/taskset_smoke.yaml \
  --out runs/mock_baseline.jsonl

uv run baeloop run \
  --config configs/agents/variant_retry.yaml \
  --taskset datasets/miniwob/taskset_smoke.yaml \
  --out runs/mock_variant_retry.jsonl

uv run baeloop compare \
  --base runs/mock_baseline.jsonl \
  --new runs/mock_variant_retry.jsonl \
  --taskset-id miniwob_smoke \
  --json-out reports/mock_compare.json \
  --markdown-out reports/mock_compare.md

uv run baeloop advise \
  --report reports/mock_compare.json \
  --out reports/mock_proposal.json

uv run baeloop patch \
  --base-config configs/agents/variant_retry.yaml \
  --proposal reports/mock_proposal.json \
  --out configs/agents/generated_advisor.yaml

uv run baeloop run \
  --config configs/agents/generated_advisor.yaml \
  --taskset datasets/miniwob/taskset_smoke.yaml \
  --out runs/mock_generated_advisor.jsonl

uv run baeloop compare \
  --base runs/mock_variant_retry.jsonl \
  --new runs/mock_generated_advisor.jsonl \
  --taskset-id miniwob_smoke \
  --json-out reports/mock_advisor_compare.json \
  --markdown-out reports/mock_advisor_compare.md
```

Run tests:

```bash
uv run pytest
```
