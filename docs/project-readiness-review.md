# 项目实习标准 Review

日期：2026-04-28

## 结论

当前 BAELOOP 已经达到“可以认真投递 agent 方向日常实习”的项目雏形标准，但还没有到“非常稳、很难被质疑”的最终展示标准。

如果现在面试，项目最强的卖点不是 MiniWoB 分数本身，而是：

- 有真实 BrowserGym / AgentLab benchmark 结果。
- 有从失败证据到 bounded intervention 的闭环。
- 有非 prompt 的 action-surface probe 和 action-policy。
- 有 LLM advisor 与 deterministic advisor 的对照实验。
- 有 10-case holdout advisor-eval，证明 `llm-v2` 不只是刷 8 个已知 case。

当前最大短板是：

- benchmark 覆盖仍主要集中在 MiniWoB++。
- holdout case 已扩到 10 个，但仍主要来自 MiniWoB++ 和既有实验族。
- 已补两个 advisor 输入/输出讲解样例，但还需要把它们用于最终 demo 讲稿。
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
- Advisor holdout eval：`llm-v2 0.983` vs deterministic `0.933`

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
- 10-case holdout eval 已经初步证明它不是只刷最初 8 个 case。
- expanded holdout 不是完美满分：`llm-v2` 在一个 ambiguous mock retry case 上方向不匹配，这反而说明 eval 没有只保留满分样例。

### 3. 还需要把输入/输出例子纳入最终讲稿

目前已经补了 `docs/advisor-examples.md`，包含两个清楚的例子：

- 一个成功 patch 例子：terminal failure -> `terminal_keyboard_type`
- 一个拒绝 patch 例子：coordinate-control failure -> `hyp_probe_before_action_policy`

最终 demo 讲稿里还应该压缩展示：

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
| 实验可信度 | 8/10 | 有真实 benchmark 和 10-case holdout eval，但 benchmark 范围还偏 MiniWoB++ |
| 非 prompt 能力 | 8/10 | 有 probe-backed action policies |
| 面试可讲性 | 8/10 | 主线清楚，已有 advisor 输入/输出样例，还需要最终讲稿压缩 |
| 开源观感 | 8/10 | README/architecture/demo summary 已经能快速解释项目，还可继续打磨 |

综合判断：当前是接近 `8/10` 的实习项目。继续补充 fresh benchmark / fresh holdout、最终 demo 讲稿后，可以冲到 `8.5/10`。

## 下一步最高收益工作

优先级从高到低：

1. 选择一个更真实的 benchmark 迁移路线。
   原因：MiniWoB++ 足够证明 loop，但不够证明真实网页泛化。

2. 增加 fresh holdout case，而不是只从现有 run 重新组合。
   原因：10-case holdout 已经更可信，但 fresh task distribution 更能降低过拟合质疑。

3. 做最终 demo 讲稿。
   原因：现在材料已经有了，下一步要把 hard ladder、holdout eval、advisor examples 压成 3 到 5 分钟可讲版本。

4. 修复或解释 ambiguous mock retry case。
   原因：expanded holdout 中 `llm-v2` 唯一失分来自这个 case，需要决定它是评测标签问题，还是 selector 应该增加 regression-aware 分支。

5. 暂时不要做 dashboard。
   原因：dashboard 对 agent 能力没有直接帮助，容易分散两周 MVP 的重点。
