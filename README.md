# BAELOOP

Browser Agent Evaluation and Optimization Loop.

BAELOOP is an optimization layer for browser-agent experiments. It is not a replacement for AgentLab or BrowserGym. The first milestone is a reproducible loop over structured run records:

```text
run records -> compare report -> advisor proposal -> config patch -> rerun
```

## 60-Second Demo

BAELOOP optimizes a browser agent from benchmark evidence instead of replacing the browser agent or relying on open-ended prompt advice. The demo story is:

```text
AgentLab generic_agent runs MiniWoB++
  -> BAELOOP compares configs
  -> advisor identifies failure root causes
  -> advisor emits a bounded patch or investigation
  -> rerun / eval checks whether the decision improved the loop
```

Print the current one-page demo from committed report artifacts:

```bash
uv run baeloop demo-summary --out reports/demo_summary.md
```

Current headline evidence:

- Hard slice improved from `0.500` to `1.000`.
- Broad 20-task slice improved from `0.800` to `1.000` with 4 improvements and 0 regressions.
- Control slice only improved from `0.438` to `0.500`, which exposes the current capability boundary instead of hiding it.
- Holdout advisor eval on 10 cases: `llm-v2` scored `0.983` vs deterministic `0.933`.

For concrete advisor inputs and outputs, see [`docs/advisor-examples.md`](docs/advisor-examples.md). For the current internship-readiness assessment, see [`docs/project-readiness-review.md`](docs/project-readiness-review.md).

## Current MVP

This repository currently implements the current dependency-light MVP:

- deterministic `mock` run adapter for smoke testing
- AgentLab/BrowserGym environment probe and executable MiniWoB smoke adapter
- normalized run-record schema
- compare report generation
- deterministic Analyst/Hypothesis/Critic advisor stages
- optional LLM-backed Analyst/Hypothesis/Critic advisor mode
- tool-using optimization advisor loop over committed compare/probe/replay artifacts
- bounded config and action-policy patch materialization
- action-surface probes for terminal and SVG grid-coordinate tasks
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

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full agent-stage architecture, intervention model, and current implementation boundaries.

Current implemented architecture:

```text
AgentLab generic_agent -> RunRecord JSONL -> Compare Report -> Analyst -> Hypothesis -> Critic -> Patch
```

The default advisor stages are deterministic and structured, which keeps the closed loop reproducible and testable.
The optional LLM advisor path runs Analyst, Hypothesis, and Critic as model-backed stages while preserving the same structured schemas and deterministic guardrails.
The `llm-v2` path adds a deterministic-reference tool and an evidence-maturity selector, so the agent can choose between patch, hold, and investigation instead of emitting a single unconstrained answer.
The `tool-agent` path makes the optimization layer more agent-like: it inspects a compare report, chooses local diagnostic tools, observes probe/replay artifacts, and then emits a final bounded `AdvisorProposal`.

Target architecture:

```text
Compare Report
  -> Analyst Agent      factual deltas, regressions, failure taxonomy
  -> Hypothesis Agent   bounded optimization hypotheses
  -> Critic Agent       reject weak or unsupported hypotheses
  -> Patch Generator    materialize approved config patches
```

The next milestone is better evidence for this advisor layer: broader tasksets and richer run diagnostics, not a dashboard or a new browser agent. The compare layer now tracks diagnostics such as average input tokens, output tokens, LLM calls, agent retries, and busted retries, so the advisor can reason about efficiency when success rates are saturated.

Run the deterministic advisor:

```bash
uv run baeloop advise \
  --report reports/agentlab_control_full_policy_compare.json \
  --out reports/agentlab_control_full_policy_proposal.json
```

Run the LLM-backed advisor over the same structured report:

```bash
export OHFI_API_KEY="sk-..."
uv run baeloop advise \
  --advisor-mode llm \
  --model gpt-5.4 \
  --report reports/agentlab_control_full_policy_compare.json \
  --out reports/agentlab_control_full_policy_llm_proposal.json
```

Run the v2 advisor with deterministic-reference and evidence-maturity selection:

```bash
export OHFI_API_KEY="sk-..."
uv run baeloop advise \
  --advisor-mode llm-v2 \
  --model gpt-5.4 \
  --report reports/agentlab_control_full_policy_compare.json \
  --out reports/agentlab_control_full_policy_llm_v2_proposal.json
```

The LLM advisor uses streaming OpenAI-compatible chat completions by default. The v1 path falls back to the deterministic advisor if JSON parsing, schema validation, or patch-boundary checks fail. The v2 path falls back to its local evidence-maturity selector, so transient LLM formatting failures do not discard the v2 decision policy.

Run the tool-using optimization agent over local reports and diagnostic artifacts:

```bash
uv run baeloop tool-agent \
  --report reports/agentlab_hard_combined_vs_terminal_policy_compare.json \
  --json-out reports/tool_agent_coordinate_loop.json \
  --markdown-out reports/tool_agent_coordinate_loop.md
```

This command does not rerun the browser and does not call an API. It demonstrates the upper-layer agent loop: `inspect_compare_report -> inspect_grid_probe -> AdvisorProposal`.

Evaluate the advisor layer over committed historical compare reports:

```bash
uv run baeloop eval-advisor \
  --json-out reports/advisor_eval_deterministic.json \
  --markdown-out reports/advisor_eval_deterministic.md

uv run baeloop eval-advisor \
  --include-llm \
  --model gpt-5.4 \
  --json-out reports/advisor_eval_llm.json \
  --markdown-out reports/advisor_eval_llm.md

uv run baeloop eval-advisor \
  --include-llm-v2 \
  --model gpt-5.4 \
  --json-out reports/advisor_eval_llm_v2.json \
  --markdown-out reports/advisor_eval_llm_v2.md
```

Current advisor-eval result on 8 historical cases:

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.896 | 0.750 | 1.000 | 0.875 | 0.750 |
| `llm` | 0.875 | 0.625 | 0.875 | 1.000 | 0.875 |
| `llm-v2` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The useful result is diagnostic: v1 showed that a plain LLM advisor is not automatically better than deterministic rules. The v2 agent beats the deterministic baseline by adding a deterministic-reference tool and an evidence-maturity selector that forces weak action-policy ideas into probe/investigation decisions before patching.

Current holdout advisor-eval result on 10 additional cases:

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |
| `llm-v2` | 0.983 | 0.900 | 1.000 | 1.000 | 1.000 |

The holdout report also shows the final decision source for each case. Most mature cases select `deterministic_reference`; weak coordinate-action cases select `investigation_fallback`, which is the behavior the v2 selector is designed to enforce. The expanded suite is intentionally not perfect: `llm-v2` misses one ambiguous mock retry direction, which keeps the claim honest.

Print the current demo story from committed report artifacts:

```bash
uv run baeloop demo-summary --out reports/demo_summary.md
```

See `docs/project-readiness-review.md` for the current internship-readiness assessment and remaining gaps.

## Current Hard-Slice Result

The current committed MiniWoB++ hard-slice loop shows a full benchmark-driven optimization sequence:

| Config | Success Rate | Main Change |
|---|---:|---|
| `relay_gpt54_hard_retry` | 0.500 | baseline retry config |
| `generated_agentlab_hard_advisor` | 0.625 | larger step budget |
| `generated_agentlab_hard_scroll_policy` | 0.750 | bounded social scroll policy |
| `generated_agentlab_hard_combined_policy` | 0.875 | composed scroll + terminal policies |
| `generated_agentlab_hard_full_policy` | 1.000 | adds coordinate-aware SVG click policy |
| `generated_agentlab_hard_full_policy_repeat` | 1.000 | same-slice repeat check |

The important point is that the final gains are not prompt-only changes. They are bounded action-policy interventions driven by failure evidence:

- `terminal_keyboard_type`: rewrites terminal `fill(...)` actions into keyboard events after the terminal probe showed `fill(...)` did not affect MiniWoB's custom terminal.
- `grid_coordinate_click`: rewrites an SVG-root bid click into `mouse_click(164, 104)` after the grid probe showed the mapped coordinate click solves seed 25.
- `scroll_before_submit`: preserves the social-task fix when policies are composed instead of replacing each other.

The main reports are:

- `reports/agentlab_hard_full_policy_compare.md`
- `reports/agentlab_hard_full_policy_repeat_compare.md`
- `reports/agentlab_grid_coordinate_probe.md`

## Current Broad-Slice Validation

The hard-slice result has now been checked on a broader 20-task MiniWoB++ slice that combines the earlier core, challenge, and hard tasks with additional tab, email, social, and slider tasks:

| Config | Task Count | Success Rate | Regressions |
|---|---:|---:|---:|
| `relay_gpt54_hard_retry` | 20 | 0.800 | - |
| `generated_agentlab_hard_full_policy` | 20 | 1.000 | 0 |

The broad comparison improves four tasks without regressions:

- `book-flight`: recovered by the larger step budget from the advisor loop.
- `grid-coordinate`: recovered by `grid_coordinate_click`.
- `social-media-all`: recovered by `scroll_before_submit`.
- `terminal`: recovered by `terminal_keyboard_type`.

The broad run is stronger evidence than the original 8-task slice because the same full policy also no-ops safely across unrelated click, text, checkbox, autocomplete, tab, email, social-some, spinner, and slider tasks. The main broad-slice artifacts are:

- `datasets/miniwob/taskset_agentlab_broad.yaml`
- `runs/agentlab_broad_relay_gpt54_retry.jsonl`
- `runs/agentlab_broad_full_policy.jsonl`
- `reports/agentlab_broad_full_policy_compare.md`
- `reports/agentlab_broad_full_policy_proposal.json`

## Current Control-Slice Finding

The next stress slice targets continuous and coordinate-heavy controls: sliders, spinners, color wheels, SVG drag/draw tasks, resize handles, and pie menus.

| Config | Task Count | Success Rate | Regressions |
|---|---:|---:|---:|
| `relay_gpt54_hard_retry` | 16 | 0.438 | - |
| `generated_agentlab_hard_full_policy` | 16 | 0.500 | 0 |

The full policy only improves `use-slider-2`, so the remaining value is not another generic prompt or step-budget patch. The dominant unsolved failures are now coordinate-control surfaces:

- `coordinate_drag_surface_mismatch`: SVG/resize tasks need directional drags with distance.
- `coordinate_draw_surface_mismatch`: drawing tasks need coordinate-level strokes inside an SVG canvas.
- `coordinate_click_surface_mismatch`: pie menus expose SVG-internal controls that are not reliable bid targets.
- `directional_drag_control_mismatch`: cube rotation needs controlled drag direction and magnitude.
- `list_drag_semantics_mismatch`: list reordering needs a probe for source/target/drop semantics.

The advisor now emits `hyp_probe_coordinate_control` for this slice, directing the next work toward coordinate drag/click/draw probes before adding another action policy. Main artifacts:
This slice is treated as capability-boundary evidence, not as a mandate to hand-code every control task.

- `datasets/miniwob/taskset_agentlab_control.yaml`
- `reports/agentlab_control_full_policy_compare.md`
- `reports/agentlab_control_full_policy_proposal.json`
- `reports/agentlab_control_full_policy_llm_proposal.json`

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

The current hard-slice loop also includes a non-prompt `scroll_before_submit` action-policy experiment:

```bash
uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/generated_agentlab_hard_scroll_policy.yaml \
  --taskset datasets/miniwob/taskset_agentlab_hard.yaml \
  --out runs/agentlab_hard_scroll_policy.jsonl

uv run baeloop compare \
  --base runs/agentlab_hard_advisor_budget30.jsonl \
  --new runs/agentlab_hard_scroll_policy.jsonl \
  --taskset-id miniwob_agentlab_hard \
  --json-out reports/agentlab_hard_scroll_policy_compare.json \
  --markdown-out reports/agentlab_hard_scroll_policy_compare.md
```

Committed evidence: `configs/agents/generated_agentlab_hard_scroll_policy.yaml` reaches `0.750` success rate versus `0.625` for the step-budget config, with no regressions on the eight-task hard slice. The action policy did not fire in that run (`avg_action_policy_interventions = 0.0`), so this is a safe-wrapper result and not causal proof of the rewrite.

For a counterfactual policy-fire check against a saved AgentLab trace:

```bash
uv run baeloop replay-policy \
  --trace-dir runs/agentlab_traces/2026-04-25_15-13-30_GenericAgent-gpt-5.4_on_miniwob.social-media-all_26 \
  --config configs/agents/generated_agentlab_hard_scroll_policy.yaml \
  --json-out reports/agentlab_social_scroll_policy_replay.json \
  --markdown-out reports/agentlab_social_scroll_policy_replay.md
```

The committed replay report shows that the policy would have intercepted the failing `social-media-all` trace at step 7, rewriting `click('104')` to `scroll(0, 621)`.

Probe the MiniWoB terminal action interface before proposing terminal-specific policies:

```bash
uv run baeloop probe-terminal \
  --seed 27 \
  --json-out reports/agentlab_terminal_action_probe.json \
  --markdown-out reports/agentlab_terminal_action_probe.md
```

The committed probe report shows that `fill(...)` does not mutate MiniWoB's custom terminal command buffer, while `focus(...)` plus `keyboard_type(...)` does. The oracle check solves seed 27 by listing files, selecting `vim.gpg`, and removing it with keyboard events.

Probe the MiniWoB grid-coordinate action interface before proposing coordinate-specific policies:

```bash
uv run baeloop probe-grid-coordinate \
  --seed 25 \
  --json-out reports/agentlab_grid_coordinate_probe.json \
  --markdown-out reports/agentlab_grid_coordinate_probe.md
```

The committed probe report shows that `click("13")` on the SVG root fails, while mapped `mouse_click(164, 104)` solves the target coordinate `(1,2)`.

Run the current full hard-slice policy:

```bash
uv run baeloop run \
  --adapter agentlab \
  --config configs/agents/generated_agentlab_hard_full_policy.yaml \
  --taskset datasets/miniwob/taskset_agentlab_hard.yaml \
  --out runs/agentlab_hard_full_policy.jsonl

uv run baeloop compare \
  --base runs/agentlab_hard_combined_policy.jsonl \
  --new runs/agentlab_hard_full_policy.jsonl \
  --taskset-id miniwob_agentlab_hard \
  --json-out reports/agentlab_hard_full_policy_compare.json \
  --markdown-out reports/agentlab_hard_full_policy_compare.md
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
