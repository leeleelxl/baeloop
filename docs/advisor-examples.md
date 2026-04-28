# Advisor 输入输出样例

这个文档用于解释 BAELOOP 的 advisor agent 到底做了什么。

核心判断标准不是“LLM 给了一段建议”，而是：

- 输入必须是结构化 benchmark 对比结果，而不是自由聊天上下文。
- 输出必须是有边界的 `AdvisorProposal`，只能给出允许的 config patch、investigation 或 hold。
- `llm-v2` 不是单层 prompt，它包含 LLM Analyst、LLM Hypothesis、LLM Critic、deterministic reference 和 evidence-maturity selector。
- 当证据足够成熟时，advisor 可以输出 patch；当证据不足时，advisor 应该拒绝 patch，转成 investigation。

## 输入和输出边界

```text
ComparisonReport
  - baseline / candidate metrics
  - improvements / regressions
  - failure taxonomy
  - failure evidence with root causes
        |
        v
Advisor Layer
  - Analyst: 总结指标变化、失败分布、风险
  - Hypothesis: 生成一个候选 intervention
  - Critic: 检查证据、patch 边界、回归风险
  - Selector: 在 patch / investigation / hold 之间做最终选择
        |
        v
AdvisorProposal
  - hypothesis_id
  - summary / rationale / expected_effect / risk
  - bounded patch or empty patch
```

## 样例 1：成功输出 patch

### 场景

Advisor 看到一个 8 题 hard-slice 对比：

- 输入报告：`reports/agentlab_hard_scroll_policy_compare.json`
- 可读报告：`reports/agentlab_hard_scroll_policy_compare.md`
- advisor 输出：`reports/agentlab_hard_scroll_policy_proposal.json`
- eval case：`hard_scroll_to_terminal` in `reports/advisor_eval_llm_v2.json`

这轮 candidate 已经通过 `scroll_before_submit` 修复了 `social-media-all`，但 `terminal` 仍然失败。

### 压缩后的输入

```json
{
  "taskset_id": "miniwob_agentlab_hard",
  "baseline_config_id": "relay_gpt54_hard_retry_hyp_extend_step_budget",
  "candidate_config_id": "relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit",
  "metrics": {
    "baseline_success_rate": 0.625,
    "candidate_success_rate": 0.75,
    "delta_success_rate": 0.125,
    "regression_count": 0
  },
  "improvements": [
    "browsergym/miniwob.social-media-all#seed=26: 0.00 -> 1.00"
  ],
  "candidate_failures": [
    {
      "task_id": "browsergym/miniwob.grid-coordinate#seed=25",
      "root_cause": "coordinate_click_miss",
      "failure_type": "zero_score"
    },
    {
      "task_id": "browsergym/miniwob.terminal#seed=27",
      "root_cause": "terminal_input_action_mismatch",
      "failure_type": "max_steps",
      "step_count": 30
    }
  ]
}
```

### Agent 阶段判断

`Analyst Agent` 判断：

- candidate 比 baseline 好，成功率 `0.625 -> 0.750`。
- 没有 regression。
- scroll 相关失败已经被修复，剩余主要失败包含 `terminal_input_action_mismatch`。
- terminal 失败耗尽 30 步，说明继续加 step budget 不是优先方向。

`Hypothesis Agent` 判断：

- terminal 失败不是模型完全不会规划，而是动作接口不匹配。
- MiniWoB custom terminal 对 `fill(...)` 不更新可见 terminal state，需要 keyboard event。
- 因此候选 intervention 应该是 action policy，不应该是改 prompt。

`Critic Agent` 判断：

- patch 只修改允许的 `action_policy` key。
- patch 有明确 `max_interventions` 上限。
- 这轮比较没有 regression。
- 证据直接来自 `terminal_input_action_mismatch`，不是凭空猜测。

`Evidence-Maturity Selector` 判断：

- deterministic reference 已经是证据成熟的 bounded patch。
- 最终选择 `deterministic_reference`，而不是让 LLM 自由扩写方案。

### 最终输出

```json
{
  "advisor_mode": "llm-v2",
  "hypothesis_id": "hyp_terminal_keyboard_type",
  "summary": "Enable a terminal keyboard-type action policy for custom terminal input.",
  "rationale": "Candidate failure evidence shows terminal commands were attempted with fill, but MiniWoB custom terminal only updates command state from keyboard events.",
  "expected_effect": "Let the agent terminal commands actually reach the MiniWoB terminal without changing the prompt.",
  "risk": "This fixes input delivery, not command planning.",
  "patch": {
    "action_policy": {
      "enabled": true,
      "max_interventions": 20,
      "name": "terminal_keyboard_type"
    }
  },
  "critic_decision": "accepted",
  "advisor_stage_notes": {
    "selector": {
      "selected_source": "deterministic_reference"
    }
  }
}
```

### 为什么这个样例重要

这个例子说明 advisor 的输出不是泛泛的“试着优化 terminal prompt”。它把 benchmark failure evidence 转成了一个可执行、可回滚、有上限的 action-policy patch。后续 closed loop 也证明这个方向能继续推动 hard slice 从 `0.750` 往上走。

## 样例 2：拒绝 patch，转 investigation

### 场景

Advisor 看到另一个 hard-slice 对比：

- 输入报告：`reports/agentlab_hard_combined_vs_terminal_policy_compare.json`
- 可读报告：`reports/agentlab_hard_combined_vs_terminal_policy_compare.md`
- eval 报告：`reports/advisor_eval_holdout_llm_v2.json`
- eval case：`holdout_combined_vs_terminal_remaining_coordinate`

candidate 成功率继续提升，但剩余失败只剩 `coordinate_click_miss`。直觉上可以马上加 `grid_coordinate_click` patch，但这正是容易过拟合的地方。

### 压缩后的输入

```json
{
  "taskset_id": "miniwob_agentlab_hard",
  "baseline_config_id": "relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type",
  "candidate_config_id": "relay_gpt54_hard_retry_hyp_extend_step_budget_hyp_scroll_before_submit_hyp_terminal_keyboard_type_combined",
  "metrics": {
    "baseline_success_rate": 0.75,
    "candidate_success_rate": 0.875,
    "delta_success_rate": 0.125,
    "avg_latency_delta_sec": 9.29,
    "avg_input_tokens_delta": 9631.75,
    "regression_count": 0
  },
  "improvements": [
    "browsergym/miniwob.social-media-all#seed=26: 0.00 -> 1.00"
  ],
  "candidate_failures": [
    {
      "task_id": "browsergym/miniwob.grid-coordinate#seed=25",
      "root_cause": "coordinate_click_miss",
      "failure_type": "zero_score",
      "step_count": 1
    }
  ]
}
```

### Agent 阶段判断

`Analyst Agent` 判断：

- candidate 成功率 `0.750 -> 0.875`，没有 regression。
- 但成本明显上升：latency、input tokens、LLM calls 都增加。
- 剩余 coordinate failure 只有一个样本，且是一类 action-surface 问题。

`Hypothesis Agent` 初步候选：

- LLM candidate 和 deterministic reference 都倾向于输出 `grid_coordinate_click` action policy。
- 这是一个看似合理的 patch，因为 root cause 是 `coordinate_click_miss`。

`Critic Agent` 和 `Selector` 的关键作用：

- `llm-v2` 没有直接接受 patch-bearing action policy。
- selector 判断这个 action policy 缺少 probe-backed maturity。
- 因此最终输出 investigation，而不是 patch。

### 最终输出

```json
{
  "advisor_mode": "llm-v2",
  "hypothesis_id": "hyp_probe_before_action_policy",
  "summary": "Probe the action surface before adding another action-policy patch.",
  "rationale": "Failure evidence points to action-surface root causes, but the report does not yet prove that a bounded rewrite primitive will solve them.",
  "expected_effect": "Collect trace or environment evidence before deciding whether the next candidate should be a patch-bearing action policy.",
  "risk": "Does not immediately improve success rate, but avoids overfitting a patch to weak evidence.",
  "patch": {},
  "critic_decision": "accepted",
  "advisor_stage_notes": {
    "selector": {
      "selected_source": "investigation_fallback",
      "notes": [
        "patch-bearing action policy lacks probe-backed maturity"
      ]
    }
  }
}
```

### 为什么这个样例重要

这个例子是 BAELOOP 区分“agent optimization”与“简单 prompt 工程”的关键证据。一个弱 advisor 会看到 `coordinate_click_miss` 就直接给 patch；`llm-v2` 会识别证据成熟度不足，先要求 probe。这个行为更像真实工程中的优化 agent：不是永远改配置，而是在证据不足时主动限制自己。

## 面试时可以这样解释

如果面试官质疑“这是不是只是 prompt engineering”，可以直接用这两个样例回答：

- 成功 patch 样例说明 advisor 能把失败证据转成 bounded action-policy patch。
- investigation 样例说明 advisor 不会无脑 patch，会根据 evidence maturity 拒绝风险方案。
- 两个样例都来自已提交 benchmark report 和 advisor eval report，不是手写故事。
- 输出被 schema 和 allowed patch keys 限制，能进入后续 rerun 或 probe，而不是停在自然语言建议。
