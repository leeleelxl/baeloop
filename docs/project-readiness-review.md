# 项目实习标准 Review

日期：2026-04-27

## 结论

当前 BAELOOP 已经达到“可以认真投递 agent 方向日常实习”的项目雏形标准，但还没有到“非常稳、很难被质疑”的最终展示标准。

如果现在面试，项目最强的卖点不是 MiniWoB 分数本身，而是：

- 有真实 BrowserGym / AgentLab benchmark 结果。
- 有从失败证据到 bounded intervention 的闭环。
- 有非 prompt 的 action-surface probe 和 action-policy。
- 有 LLM advisor 与 deterministic advisor 的对照实验。
- 有 holdout advisor-eval，证明 `llm-v2` 不只是刷 8 个已知 case。

当前最大短板是：

- benchmark 覆盖仍主要集中在 MiniWoB++。
- advisor holdout case 数量还偏少。
- 缺少两个清晰的 advisor 输入/输出讲解样例。
- `llm-v2` selector 仍带有项目历史规则，需要更明确地解释为 evidence-maturity policy，而不是纯 LLM 智能。

## 大厂可能喜欢的点

### 1. 不是 prompt-only

项目已经有三类非 prompt 改动：

- `terminal_keyboard_type`：通过 probe 证明 MiniWoB terminal 需要 keyboard event，而不是 `fill(...)`。
- `grid_coordinate_click`：通过 probe 证明 SVG root click 不够，需要映射到坐标点击。
- `scroll_before_submit`：通过 action-policy/replay 针对隐藏目标问题。

这能回答面试官的问题：“你是不是只是调了 prompt？”

答案：不是。项目把 failure evidence 转成 bounded action-policy，并用 rerun 或 probe 验证。

### 2. 有 agent optimization 决策层

当前 advisor 层不是简单输出建议，而是：

```text
ComparisonReport
  -> Analyst Agent
  -> Hypothesis Agent
  -> Deterministic Reference Tool
  -> Evidence-Maturity Selector
  -> Critic Agent
  -> AdvisorProposal
```

这能回答：“你的 agent 在项目中起什么作用？”

答案：agent 不直接操作浏览器，而是做实验结果分析和下一轮优化决策。浏览器 agent 是执行层，BAELOOP 是优化层。

### 3. 有可复现实验链路

核心证据：

- Hard slice：`0.500 -> 1.000`
- Broad slice：`0.800 -> 1.000`，4 improvements，0 regressions
- Control slice：`0.438 -> 0.500`，暴露 coordinate/control 能力边界
- Advisor default eval：`llm-v2 1.000` vs deterministic `0.896`
- Advisor holdout eval：`llm-v2 1.000` vs deterministic `0.933`

这比“我觉得 agent 更好”强很多，因为有报告和指标。

## 仍然会被质疑的点

### 1. MiniWoB++ 是否太小

MiniWoB++ 适合两周 MVP，但大厂面试官可能会问：

- WebArena 呢？
- 真实网页任务呢？
- 更复杂长程任务呢？

当前回答应该诚实：

- 现阶段先用 MiniWoB++ 做可控闭环，因为它能快速验证 optimization loop。
- 下一步可以迁移到 WebArena-Verified 或更大 BrowserGym taskset。
- 架构上 browser agent adapter 和 benchmark runner 是可替换的。

### 2. `llm-v2` 是否过拟合规则

`llm-v2` 中的 evidence-maturity selector 有项目历史规则，例如 coordinate/missed-scroll 先 probe。面试官可能会问这是不是 hardcode。

当前回答：

- 是有 domain policy，但这是 agent optimization 系统的安全边界，不是坏事。
- LLM 负责分析、候选生成和 critic note；selector 负责保证 patch 不越界。
- 这类似 production agent 系统中的 policy guardrail。
- holdout eval 已经初步证明它不是只刷最初 8 个 case。

### 3. 还缺少输入/输出例子

目前报告很多，但面试时需要两个非常清楚的例子：

- 一个成功 patch 例子：terminal failure -> `terminal_keyboard_type`
- 一个拒绝 patch 例子：coordinate-control failure -> `hyp_probe_before_action_policy`

这两个例子应该包含：

- advisor 输入摘要
- Analyst 输出
- Hypothesis 输出
- Selector/Critic 决策
- 最终 proposal

## 当前评分

如果目标是“大厂 agent 日常实习项目”，当前评分：

| 维度 | 评分 | 说明 |
|---|---:|---|
| 工程完整度 | 8/10 | CLI、schema、tests、reports、docs 都比较完整 |
| agent 相关性 | 8/10 | 有 advisor agent 架构和 LLM/deterministic 对照 |
| 实验可信度 | 7/10 | 有真实 benchmark 和 holdout eval，但 benchmark 范围还偏小 |
| 非 prompt 能力 | 8/10 | 有 probe-backed action policies |
| 面试可讲性 | 7/10 | 主线清楚，但还缺两个强输入/输出样例 |
| 开源观感 | 7/10 | README/architecture 已不错，demo summary 刚补上，还可继续打磨 |

综合判断：当前是 `7.5/10` 到 `8/10` 的实习项目。继续补充 holdout、demo examples、README polish 后，可以冲到 `8.5/10`。

## 下一步最高收益工作

优先级从高到低：

1. 补两个 advisor 输入/输出样例。
   原因：这是面试解释 agent 架构最直接的材料。

2. 扩大 holdout advisor-eval 到 10 到 15 个 case。
   原因：降低 `llm-v2` 过拟合质疑。

3. 增加 README 顶部的 “60 秒 Demo”。
   原因：面试官和开源读者先看 README，不会先读所有报告。

4. 选择一个更真实的 benchmark 迁移路线。
   原因：MiniWoB++ 足够证明 loop，但不够证明真实网页泛化。

5. 暂时不要做 dashboard。
   原因：dashboard 对 agent 能力没有直接帮助，容易分散两周 MVP 的重点。
