# 原文优先 vs 译文优先 打标顺序实验

## 背景

TODO P1 需求：「调整 extract-url 标签生成顺序为先原文后翻译」，假设是"基于译文生成标签不如基于原文准确"。本实验用真实 subagent 独立试验验证这个假设，同时验证一个共享约束：description 用中文、tags/candidate_tags 保留原文技术术语不翻译（这一点在真实 vault 数据中已是既有惯例，参见 `/Users/harveyzhang96/Vault/Product/Reading` 下已保存文章的 frontmatter）。

## 测试文章 / 固定词表

复用 `../two-phase-tagging/fixture-article.txt`（同一篇 "Loop Engineering Works On Memory"，mem0 twitter 英文原文）与 `../two-phase-tagging/expected-output.yaml`（同一份 ground truth）。固定词表内容与 `../two-phase-tagging/fixture-fixed-tags.txt` 一致，但按生产环境 `fixed_tags.txt` 的分类注释格式（`# topic` / `# technology` / `# source` / `# language` / `# domain`）重新排版后嵌入 prompt。

## 三个变体

**变体 A（原顺序 + 回看原文指令）**：阶段 1 翻译全文成中文；阶段 2 打标+摘要时，prompt 明确要求"重新查看原文本身（而不是只依赖刚才生成的译文）"生成 description/tags/candidate_tags。

**变体 B（原文优先重排序）**：阶段 1 仅基于原文（未翻译）生成 description/tags/candidate_tags；阶段 2 才翻译全文。

**对照组 C（单阶段，无顺序/无翻译）**：不分阶段，不涉及翻译，直接一次性基于原文生成 description/tags/candidate_tags。用于排除"A/B 的 Noise 差异是否由顺序本身引起"——C 组与 A/B 使用逐字相同的打标规则文字，但完全没有"阶段""翻译干扰"这些结构性因素。

三个变体共享规则：description 用简体中文；candidate_tags 保留原文技术术语原样，不翻译；`claude`/`llm` 等词条须确认为核心主题才选用（三组规则文字逐字相同）。

各变体独立派发 Agent 工具（general-purpose，无共享上下文，模拟真实 Subagent 2 行为）跑 3 轮。

## 评分方法

复用 `expected-output.yaml` 的 Recall/Noise/Candidate 指标定义，另外人工检查 description 准确性/语言、candidate_tags 是否被误翻译、译文质量。

## 实验结果（2026-07-08）

| Variant | Run | Recall | Noise | Candidate | 命中/误选详情 |
|---------|-----|--------|-------|-----------|----------------|
| A | 1 | 5/6=0.833 | 0 | 1/3=0.333 | 漏 ai；无误选 |
| A | 2 | 5/6=0.833 | 1 | 1/3=0.333 | 漏 ai；误选 claude |
| A | 3 | 5/6=0.833 | 1 | 1/3=0.333 | 漏 ai；误选 claude |
| B | 1 | 5/6=0.833 | 2 | 1/3=0.333 | 漏 ai；误选 claude, productivity |
| B | 2 | 5/6=0.833 | 1 | 1/3=0.333 | 漏 ai；误选 claude |
| B | 3 | 5/6=0.833 | 1 | 1/3=0.333 | 漏 ai；误选 claude |
| C | 1 | 6/6=1.0 | 0 | 1/3=0.333 | 全命中；无误选 |
| C | 2 | 5/6=0.833 | 1 | 1/3=0.333 | 漏 ai；误选 claude |
| C | 3 | 6/6=1.0 | 1 | 1/3=0.333 | 全命中；误选 claude |

**均值**：A → Recall 0.833 / Noise 0.67 / Candidate 0.333；B → Recall 0.833 / Noise 1.33 / Candidate 0.333；C → Recall 0.944 / Noise 0.67 / Candidate 0.333

description（9 轮均为准确中文摘要）、candidate_tags 语言（9 轮均保留原文术语未翻译）、译文质量（A/B 6 轮均自然、专有名词保留英文）三项在有该维度的变体间完全打平，无可区分差异。

## 实验结论

- **顺序（A vs B）本身不是决定性变量**：加入对照组 C 后重新审视——C 组完全没有阶段/顺序/翻译结构，只是复用同一套规则文字单轮打标，其 Noise 均值（0.67）与 A 打平，`claude` 误选率（2/3）也和 A 一致。这说明 A 相对 B 的 Noise 优势（0.67 vs 1.33）更可能是 B 在 Run 1 的一次性 "productivity" 误选带来的样本波动，而不是"先原文后翻译"这个顺序本身有系统性缺陷。TODO 最初"先原文后翻译更准确"的假设，以及后续"保持原顺序更准确"的反向假设，在 9 轮数据里都没有得到稳健支持——顺序对 Recall/Noise/Candidate 三项核心指标均无法拉开有意义的差距。
- **真正需要修的是打标规则文字**：`claude` 误选在 A（2/3）、B（3/3）、C（2/3）三组里出现频率相近，且 C 组在完全没有"阶段"结构的情况下依然复现，证实这是"须确认核心主题"这条规则措辞强度不够导致的，与顺序、与是否存在翻译阶段都无关。
- **意外发现（与本次顺序议题正交）**：C 组 Recall（0.944）明显高于 A/B（均 0.833）——C 组 3 轮里 2 轮命中了 `ai`，而 A/B 六轮全部漏掉。提示"两阶段结构"（不论顺序）本身可能稀释模型对固定词表的注意力；样本量小（n=3），仅作后续参考线索，不纳入本次结论。
- **对 SKILL.md 改动的建议**：既然顺序不是决定性变量，可优先选改动更小的方案（保持现有翻译→打标顺序，仅为打标阶段加"回看原文"指令 + 显式 description 生成指令 + candidate_tags 不翻译规则），把"须确认核心主题"这条规则的措辞收紧（如要求"至少两次提及"或给出反例）留作独立后续优化项。最终顺序选择留给用户按改动成本 / 架构简洁性偏好决定。
