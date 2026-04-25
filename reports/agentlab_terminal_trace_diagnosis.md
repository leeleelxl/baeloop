# Terminal Trace Diagnosis

- Trace: `runs/agentlab_traces/2026-04-25_16-43-57_GenericAgent-gpt-5.4-scroll_before_submit_on_miniwob.terminal_27`
- Task: `browsergym/miniwob.terminal#seed=27`
- Outcome: `max_steps`, score `0.0`
- Diagnosis: `terminal_input_action_mismatch`

## Evidence

The agent repeatedly attempted plausible shell commands:

| Step | Action |
|---:|---|
| 0 | `fill('25', 'ls *.gpg')` |
| 1 | `press('25', 'Enter')` |
| 3 | `fill('25', 'rm *.gpg')` |
| 4 | `press('25', 'Enter')` |
| 7 | `fill('25', 'find . -name "*.gpg"')` |
| 10 | `fill('25', 'find . -name "*.gpg" -delete')` |
| 26 | `fill('25', 'rm -f ./*.gpg')` |

But the visible terminal state did not reflect those commands. Across inspected observations after Enter, the terminal still showed only the welcome/login text and repeated prompts; the visible `command` spans were empty.

This makes another step-budget increase weakly supported. The failure is more likely an interaction mismatch between BrowserGym's `fill` action and MiniWoB's custom terminal input handling than a planning failure.

## Next Bounded Experiment

Do not change prompts or add more budget. The next terminal-specific experiment should first test which browser action actually mutates the terminal command buffer, then wrap only terminal-task command entry behind a bounded action policy.

Acceptance criteria:

- command text becomes visible in the terminal trace after the input action
- the policy is scoped to `miniwob.terminal`
- the policy emits structured diagnostics
- the hard task rerun shows terminal outcome change or a documented no-effect result
