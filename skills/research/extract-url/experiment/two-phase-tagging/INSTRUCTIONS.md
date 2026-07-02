# 两阶段打标实验

## 目的

验证两个假设：
1. 同一 Subagent 内两阶段机制是否可行（阶段 1 译文上下文能否有效用于阶段 2）
2. 三种打标 variant（V1/V2/V3）哪种质量最优

## 测试文章

`fixture-article.txt` — 真实历史文章「Loop Engineering Works On Memory」
来源：https://x.com/mem0ai/status/2067305118891163833（Twitter，英文）

## 固定词表

`fixture-fixed-tags.txt` — 15 个词条，基于 vault 历史词频归一化

## Ground Truth

`expected-output.yaml` — 人工标注期望输出，含 expected_tags（6 个应命中词）和 expected_not_in_tags（8 个不应命中词）

## 运行方式

在 Claude Code 主 session 中，用 Agent 工具分别派发三次 subagent。
各 prompt 文件（v1/v2/v3-prompt.txt）已内嵌 `fixture-article.txt` 全文，可直接使用。

- V1 实验：使用 v1-prompt.txt 作为 Agent prompt
- V2 实验：使用 v2-prompt.txt 作为 Agent prompt
- V3 实验：使用 v3-prompt.txt 作为 Agent prompt

## 评分方法

对每个 variant，将输出与 expected-output.yaml 对比，填入评分表：

| 指标 | 计算方式 | 目标 |
|------|----------|------|
| Recall | `predicted_tags ∩ expected_tags` 的数量 / 6 | ≥ 0.8（命中 ≥5 个） |
| Noise | `predicted_tags ∩ expected_not_in_tags` 的数量 | = 0 |
| Candidate | `expected_candidate_contains` 中出现在 candidate_tags 的数量 / 3 | ≥ 0.67 |

## 记录结果

实验完成后，在本文件末尾追加：

### 实验结果（2026-06-30）

| Variant | Recall | Noise | Candidate | 输出 tags | 输出 candidate_tags |
|---------|--------|-------|-----------|-----------|---------------------|
| V1 | 5/6=0.833 | 2 (claude, llm) | 2/3=0.667 | loop-engineering, context-engineering, agent, claude, twitter, ai, llm | memory, agent-memory, compaction, long-running-agents, token-cost, harness-engineering, mem0 |
| V2 | 4/6=0.667 | 3 (prompt-engineering, llm, claude) | 1/3=0.333 | loop-engineering, context-engineering, prompt-engineering, ai, llm, agent, claude | memory, memory-engineering, long-running-agents |
| V3 | 6/6=1.0 | 3 (prompt-engineering, llm, claude) | 1/3=0.333 | loop-engineering, context-engineering, prompt-engineering, ai, llm, agent, claude, twitter, english | memory-engineering, long-running-agents, context-compaction, multi-agent, agentic-systems |

### 实验结论
- 选用 variant：V1
- 理由：V1 达到最优综合得分。Recall=0.833（≥目标 0.8），Candidate=0.667（达到目标 0.67），Noise=2（三者中最低）。V3 虽然 Recall 满分但 Noise=3 且 Candidate=0.333；V2 三项指标均最差。V1 的两阶段直接选取机制（翻译 → 从固定词表选取）比 V2 的"自由生成再分类"和 V3 的"有释义约束选取"更精准。所有 variant 的共同问题是将 claude/llm 误归入 tags，这可通过在 Task 5 的词表中为各词条加注释说明来改善（参考 V3 prompt 的有界选取写法）。
