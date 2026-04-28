# BAELOOP 项目进展记录

这个文件是项目的长期进度账本。之后每天推进项目时都要维护它，用来回答三个问题：

- 今天项目做到哪一步了？
- 当前系统架构是什么，每个模块负责什么？
- 下一阶段要做什么，之前计划完成了吗？

## 维护规则

- 每个有效工作日都在 `每日记录` 里新增或更新一条记录，最新日期放最上面。
- 每天都必须写 `当日架构图`，即使架构没有变化，也要标明“架构未变”。
- 每天都必须写 `模块职责`，方便复盘和面试时解释项目。
- 每天都必须写 `今日改动`，说明代码、报告、实验、文档分别变了什么。
- 每天都必须写 `验证证据`，例如测试结果、报告路径、commit hash、真实实验指标。
- 如果前一天计划完成了，把对应 `[ ]` 改成 `[x]`，并补充证据。
- 如果计划被放弃，不删除，标记为 `已废弃` 并写原因。
- 不记录 API key、GitHub token、私密凭证。

## 项目目标

目标是在六月前完成一个能打动大厂 agent 岗位面试官的开源项目。

项目不是重新造一个浏览器 agent，而是做一个浏览器 agent 的上层优化系统：

```text
浏览器 agent 运行 benchmark
  -> 记录结构化结果
  -> 对比两个配置
  -> 分析失败原因和回归
  -> advisor agent 选择下一步优化方向
  -> 生成有边界的 config patch 或 investigation
  -> rerun / eval 验证是否真的变好
```

## 当前项目快照

- 项目名：`BAELOOP` / Browser Agent Evaluation and Optimization Loop
- 仓库：`https://github.com/leeleelxl/baeloop`
- 当前基线浏览器 agent：AgentLab `generic_agent`
- 当前 benchmark：BrowserGym MiniWoB++
- 当前重点：上层 advisor agent 的决策质量，而不是继续堆 MiniWoB 控制任务
- 当前主要 advisor 模式：`deterministic`、`llm`、`llm-v2`
- 最新 commit 以 `git log --oneline -1` 为准；关键 commit 在每日记录中单独记录。

关键证据：

- Hard slice：成功率 `0.500 -> 1.000`，通过 advisor 驱动的有边界 action-policy 逐步提升。
- Broad slice：20 个 MiniWoB++ 任务上 `0.800 -> 1.000`，4 个 improvement，0 个 regression。
- Control slice：`0.438 -> 0.500`，说明剩余问题主要是 coordinate/control 能力边界，不是继续 prompt 或预算能解决。
- Advisor eval：`llm-v2` 在 8 个历史 advisor 决策 case 上打败 deterministic。
- Holdout advisor eval：`llm-v2` 在 10 个 holdout case 上继续打败 deterministic，但不是满分，保留了一个 ambiguous mock retry 失分。

Advisor eval 当前结果：

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.896 | 0.750 | 1.000 | 0.875 | 0.750 |
| `llm` | 0.875 | 0.625 | 0.875 | 1.000 | 0.875 |
| `llm-v2` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

Holdout advisor eval 当前结果：

| Advisor | Avg Score | Direction Match | Safe Patch | Evidence Use | Boundary Awareness |
|---|---:|---:|---:|---:|---:|
| `deterministic` | 0.933 | 0.800 | 1.000 | 1.000 | 0.800 |
| `llm-v2` | 0.983 | 0.900 | 1.000 | 1.000 | 1.000 |

## 当前总体架构

```text
BrowserGym / MiniWoB++
        |
        v
AgentLab generic_agent
        |
        v
RunRecord JSONL
        |
        v
ComparisonReport
        |
        v
Failure Evidence / Failure Taxonomy
        |
        v
Advisor Layer
  +-------------------+-------------------+-------------------+
  | Analyst Agent     | Hypothesis Agent  | Critic Agent      |
  | 分析指标和失败分布 | 生成候选优化假设   | 拒绝弱证据或越界方案 |
  +-------------------+-------------------+-------------------+
        |
        v
Evidence-Maturity Selector
        |
        v
AdvisorProposal
        |
        v
Config Patch / Investigation / Hold
        |
        v
Rerun 或 Advisor Eval
```

## 当前模块职责

- `src/baeloop/adapters/agentlab.py`：把本项目的 config 接到 AgentLab `generic_agent`，执行真实 BrowserGym/MiniWoB++ 任务，并收集 diagnostics。
- `src/baeloop/runner.py`：统一运行 taskset，输出标准化 `RunRecord`。
- `src/baeloop/compare.py`：比较 baseline 和 candidate，生成 `ComparisonReport`，包含 success rate、score、latency、token、failure taxonomy、regression/improvement。
- `src/baeloop/failure_analysis.py`：从失败任务中抽取 root cause，例如 `missed_scroll_target`、`terminal_input_action_mismatch`、`coordinate_click_miss`。
- `src/baeloop/advisor_analysis.py`：Analyst 的 deterministic 版本，汇总质量、效率、失败类型和 root cause。
- `src/baeloop/advisor_hypothesis.py`：Hypothesis 的 deterministic 版本，把失败证据映射成 bounded intervention。
- `src/baeloop/advisor_critic.py`：Critic 的 deterministic 版本，检查 intervention 是否有 patch、是否有证据、是否存在明显风险。
- `src/baeloop/llm_advisor.py`：LLM advisor，包括 `llm` 和 `llm-v2`。`llm-v2` 使用 LLM stage + deterministic reference + evidence-maturity selector。
- `src/baeloop/advisor_eval.py`：advisor 决策质量评估，不重新跑浏览器，而是用历史 compare report 测 advisor 是否做出正确下一步。
- `src/baeloop/patcher.py`：把 `AdvisorProposal` 转成实际 config patch，并限制允许修改的 key。
- `src/baeloop/action_policy.py`：有边界的 action rewrite 策略，例如 scroll、terminal keyboard type、grid coordinate click。
- `src/baeloop/policy_replay.py`：对历史 trace 做 counterfactual replay，验证某个 action policy 是否会触发。
- `src/baeloop/terminal_probe.py`：验证 MiniWoB terminal 的真实输入机制。
- `src/baeloop/grid_probe.py`：验证 SVG grid coordinate 的真实点击机制。
- `src/baeloop/cli.py`：统一 CLI 入口，包括 run、compare、advise、eval-advisor、patch、probe、replay。

## 每日记录

### 2026-04-28

#### 当日架构图

今天的核心架构没有改变，主要补强了评估可信度、展示链路和 advisor 决策可解释性。

```text
ComparisonReport
        |
        v
Advisor Eval Suite
  +-------------------+-------------------+
  | default cases     | holdout cases     |
  | 已知历史决策集     | 未参与 v2 调整集   |
  +-------------------+-------------------+
        |
        v
deterministic / llm-v2 对比
        |
        v
Transparent Report
  - Mode
  - Source: deterministic_reference / investigation_fallback
        |
        v
Demo Summary + Readiness Review
        |
        v
Advisor Input/Output Examples
```

#### 当日模块职责

- `advisor_eval.py`：holdout suite 从 5 个 case 扩到 10 个 case，并在报告中暴露 `proposal_mode`、`selected_source`、`used_fallback`。
- `cli.py`：新增 `eval-advisor --case-suite holdout` 和 `demo-summary`。
- `demo.py`：从已提交报告生成一页 demo summary，不跑浏览器、不调用 API。
- `tests/test_advisor_eval.py`：验证 holdout suite 暴露正常，并覆盖 10 个 case 的 deterministic 评分。
- `tests/test_demo.py`：验证 demo summary 能输出项目主线。
- `README.md`、`docs/ARCHITECTURE.md`、`project.md`：补充 holdout eval、demo summary、readiness review。
- `docs/advisor-examples.md`：用两个真实 advisor case 展示输入、阶段判断和最终输出，覆盖成功 patch 与拒绝 patch 转 investigation。
- `README.md`：新增顶部 “60-Second Demo”，让读者 1 分钟内理解项目目标、关键结果和报告入口。

#### 今日改动

- [x] 增加 holdout advisor-eval case，避免只在已调过的 8 个 case 上证明 v2。
  证据：commit `1ade6ba add holdout advisor eval`；报告 `reports/advisor_eval_holdout_deterministic.md`、`reports/advisor_eval_holdout_llm_v2.md`。
- [x] 提升 advisor eval 报告透明度。
  证据：holdout Markdown 表格新增 `Mode` 和 `Source`，能看到最终决策来自 `deterministic_reference` 还是 `investigation_fallback`。
- [x] 增加一键 demo summary 命令。
  证据：commit `a8ade24 add project demo summary`；命令 `uv run baeloop demo-summary --out reports/demo_summary.md`。
- [x] 重新评估项目是否达到大厂 agent 日常实习标准。
  证据：`docs/project-readiness-review.md`。
- [x] 补两个 advisor 输入/输出样例。
  证据：`docs/advisor-examples.md`；包含 `terminal_keyboard_type` 成功 patch，以及 `coordinate_click_miss` 被 `llm-v2` 拒绝 patch 转 investigation。
- [x] 在 README 顶部增加 “60 秒 Demo”。
  证据：`README.md` 的 `60-Second Demo` 小节；包含 hard slice、broad slice、control slice、holdout advisor eval 四个关键指标。
- [x] 扩大 holdout advisor-eval 到 10 个 case。
  证据：`reports/advisor_eval_holdout_deterministic.md`、`reports/advisor_eval_holdout_llm_v2.md`；新增 `reports/agentlab_hard_budget30_vs_combined_policy_compare.*` 和 `reports/agentlab_hard_retry_vs_full_policy_compare.*`。
- [x] 验证当前代码库。
  证据：`uv run pytest` 通过，结果为 `80 passed`。

#### 今日验证证据

- `reports/advisor_eval_holdout_llm_v2.md` 显示 `llm-v2` 在 10 个 holdout case 上平均分 `0.983`，deterministic 为 `0.933`。
- holdout 中 `holdout_combined_vs_terminal_remaining_coordinate` 和 `holdout_budget30_to_combined_remaining_coordinate` 证明 v2 会把弱 coordinate patch 转成 `hyp_probe_before_action_policy`，来源为 `investigation_fallback`。
- expanded holdout 中 `holdout_sample_retry_invalid_or_noop` 是 `llm-v2` 唯一方向失分：LLM 倾向 hold，而 expected label 是 retry invalid/no-op。
- `reports/demo_summary.md` 可以一页展示 hard-slice ladder、broad validation、control boundary、advisor holdout eval。
- `docs/project-readiness-review.md` 给出当前诚实评分：接近 `8/10`，继续补充 fresh benchmark / fresh holdout 和最终 demo 讲稿后可冲 `8.5/10`。
- `docs/advisor-examples.md` 展示了 advisor 的真实输入和输出，能解释为什么项目不是简单 prompt engineering。
- `README.md` 顶部新增 `60-Second Demo`，把项目主线、关键结果和样例文档入口前置。
- `uv run pytest` 通过，`80 passed`。

#### 今日 Review

- holdout eval 进一步缓解了过拟合质疑：case 数从 5 扩到 10，`llm-v2` 仍高于 deterministic，但不是满分。
- 报告透明度比单纯满分更重要：现在可以解释 agent 是选择 deterministic reference，还是转为 investigation fallback。
- `llm-v2` 唯一失分来自 ambiguous mock retry case，这个失分需要保留，不应该为了满分倒改标签。
- demo summary 已经能讲清项目主线，README 顶部也已经补了更短的 “60 秒 Demo”。
- advisor 样例补上后，可以更直接回答“agent 到底起了什么作用”：它把结构化失败证据转成 bounded patch，或在证据不足时拒绝 patch。
- readiness review 结论仍然克制：当前可以认真投递 agent 日常实习，但还需要 fresh benchmark / fresh holdout 来证明外部泛化。

#### 下一阶段计划

- [x] 补两个 advisor 输入/输出样例。
  完成证据：`docs/advisor-examples.md`，包含一个成功 patch 例子和一个拒绝 patch 转 investigation 例子。
- [x] 扩大 holdout advisor-eval 到 10 到 15 个 case。
  完成证据：holdout suite 已扩到 10 个 case；expected label 先写入代码，再运行 deterministic 和 `llm-v2` eval。
- [x] 在 README 顶部增加 “60 秒 Demo”。
  完成证据：`README.md` 的 `60-Second Demo` 小节，读者 1 分钟内能理解项目目标、架构、关键结果和如何运行 demo。
- [ ] 增加 fresh benchmark / fresh holdout 路线。
  完成标准：明确下一批不从现有 run 重新组合的任务来源，并跑出至少一组新 holdout evidence。
- [ ] 处理 expanded holdout 中的 ambiguous mock retry case。
  完成标准：决定它是评测标签问题、需要 regression-aware expected direction，还是 selector 应该增加 regression-aware 分支。

### 2026-04-27

#### 当日架构图

今天的关键架构变化是：advisor 从普通 LLM 三阶段，升级为 `llm-v2` 决策层。

```text
ComparisonReport
        |
        v
LLM Analyst Agent
  - 读取指标变化
  - 总结 failure distribution
  - 标记风险和能力边界
        |
        v
LLM Hypothesis Agent
  - 生成一个候选 Intervention
  - 必须符合结构化 schema
        |
        v
Deterministic Reference Tool
  - 提供 deterministic advisor 的候选方案
  - 作为强 baseline 和安全参考
        |
        v
Evidence-Maturity Selector
  - 判断证据是否足够 patch
  - 证据不足时转为 probe/investigation
  - 保留已成熟的 deterministic proposal
        |
        v
LLM Critic Agent
  - 给出风险意见
  - 作为 advisory note 记录
        |
        v
AdvisorProposal
```

#### 当日模块职责

- `llm_advisor.py`：新增 `propose_patch_with_llm_v2`，让 agent 不只是输出一个建议，而是经过 deterministic reference 和 evidence-maturity selector 再决策。
- `advisor_eval.py`：新增 `include_llm_v2`，支持在同一套历史 case 上评估 `llm-v2`。
- `cli.py`：新增 `--advisor-mode llm-v2` 和 `eval-advisor --include-llm-v2`。
- `tests/test_llm_advisor.py`：新增 v2 单测，覆盖保留成熟 budget patch、弱 coordinate patch 转 investigation、LLM JSON 失败时走本地 v2 fallback。
- `README.md` 和 `docs/ARCHITECTURE.md`：更新 v2 架构、评估结果和项目叙事。
- `reports/advisor_eval_llm_v2.*`：保存真实 GPT-5.4 中转 API 上的 v2 评估结果。

#### 今日改动

- [x] 加入真实 LLM advisor 模式，包含 Analyst/Hypothesis/Critic 三阶段。
  证据：commit `10df858 add llm advisor mode`；报告 `reports/agentlab_control_full_policy_llm_proposal.json`。
- [x] 加入 advisor evaluation harness，用历史 compare report 评估 advisor 决策质量。
  证据：commit `8cda37e add advisor evaluation`；报告 `reports/advisor_eval_deterministic.*`、`reports/advisor_eval_llm.*`。
- [x] 加入 `llm-v2` advisor：LLM stage + deterministic reference tool + evidence-maturity selector。
  证据：commit `fd17b0c add llm v2 advisor selector`；报告 `reports/advisor_eval_llm_v2.md`。
- [x] 验证当前代码库。
  证据：`uv run pytest` 通过，结果为 `77 passed`。
- [x] 初始化中文项目进度账本。
  证据：`project.md`。

#### 今日验证证据

- `reports/advisor_eval_llm_v2.md` 显示 `llm-v2` 在 8 个历史 case 上平均分 `1.000`。
- `uv run pytest` 通过，`77 passed`。
- `git push` 已推送到 GitHub main，关键项目账本 commit 包含 `d2c4e6e`。

#### 今日 Review

- 普通 LLM advisor 没有天然打败 deterministic。它 evidence use 更好，但 direction match 和 safe patch 较弱。
- `llm-v2` 的优势不是 prompt 更强，而是架构更强：它把 deterministic 作为工具，并用 evidence maturity 判断什么时候应该 patch，什么时候应该 investigation。
- 当前 v2 结果是在 8 个历史 case 上得到的，下一步必须做 holdout advisor eval，避免被质疑“只适配已知 case”。
- Control slice 不应该继续盲目做控制任务。它目前的价值是证明能力边界，并驱动 probe/investigation 决策。

#### 下一阶段计划

- [x] 增加 holdout advisor-eval case，不能用已调过 v2 的 8 个 case。
  完成证据：2026-04-28 已完成。
- [x] 提升 `llm-v2` eval 报告透明度。
  完成证据：2026-04-28 已完成。
- [x] 增加一个 demo 命令或脚本，能一键展示项目主线。
  完成证据：2026-04-28 已完成。
- [x] 重新评估项目是否达到大厂 agent 日常实习标准。
  完成证据：2026-04-28 已完成。

## Backlog

- [ ] 构建 holdout advisor-decision suite。
- [ ] 做 advisor decision ablation：deterministic vs plain LLM vs `llm-v2`。
- [ ] 补两个 advisor 输入/输出例子，用于面试讲解 agent 架构。
- [ ] 决定是否实现 probe-backed coordinate-control policy，或继续把 control slice 作为能力边界证据。
- [ ] 保持 CLI-first。现阶段不做 dashboard，避免偏离 advisor optimization 主线。
