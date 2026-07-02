---
migrated: 2026-07-02
implemented_in:
  - skills/research/extract-url/experiment/two-phase-tagging/  # 两阶段打标实验分支，主路径尚未切换
---

# extract-url tag 重构设计：固定集与候选集分离

**日期**：2026-07-01
**状态**：待实验验证后实现

---

## 背景

当前 extract-url skill 的 `tags` 字段完全由 Subagent 2（翻译阶段）的 LLM 从文章内容自由推断，无固定词表，导致：
- 同一主题的标签表述不一致
- 核心关键词（如 `loop-engineering`）词汇不稳定，同一概念可能出现多种表述
- 候选标签与确定标签混在一起，难以 review 和管理

---

## 目标

将 tag 拆为两类：

- **`tags`**：来自用户维护的固定词表，LLM 从中选出与文章相关的条目；可为空
- **`candidate_tags`**：LLM 从文章内容自由提取，模糊/候选性质，定期 review 决定是否升入固定集；可为空

---

## Schema

```yaml
tags:
  - loop-engineering
  - ai
candidate_tags:
  - productivity
  - mental-model
```

两者均可为空列表。`tags` 优先，`candidate_tags` 待 review。

---

## Section 1：总体架构

### 变更范围

| 改动 | 位置 |
|------|------|
| 新增词表（用户数据） | `~/.hskill/url-extract/fixed_tags.txt` |
| 初始化时自动创建词表模板 | SKILL.md 初始化流程（`NOT_FOUND` 分支） |
| 修改 Subagent 2 任务模板 | `skills/research/extract-url/SKILL.md` 步骤 3 |
| 修改校验逻辑 | `scripts/validate_article.py` + `references/article_utils.py` |
| 更新文档 | `references/file-format.md` |

### 不动的部分

Subagent 1（抓取）流程、SQLite schema、批量流程、平台补丁、历史文章（只影响新抓取）。

---

## Section 2：Subagent 2 两阶段任务

### 流程结构

Subagent 2 在同一 session 内顺序执行：

```
阶段 1：翻译
  - 读 origin_path 文件
  - 翻译正文为简体中文，结果保留在上下文中（不写文件）

阶段 2：打标（基于阶段 1 上下文）
  - 读 fixed_tags.txt 词表
  - 对 translated_body 执行打标，产出 tags + candidate_tags
  - 打标 variant 见下方实验设计

阶段 3：写文件（一次性）
  - 构建完整 frontmatter（含 tags、candidate_tags）
  - 写入 vault_path/<文件名>.md

阶段 4：validate（格式校验 + 兜底移位）
  - 调用 validate_article.py
```

### 打标实验（三种 variant，实验后确定正式方案）

**V1 — 统一生成，优先固定词表**
LLM 单次输出所有 tag，要求优先从 `fixed_tags.txt` 中选取，额外生成的作为 `candidate_tags`。

- 风险：单次生成两类 tag，注意力分散，边界模糊

**V2 — 自由生成 → 字符串匹配分类**
LLM 自由生成所有 tag，再与词表做字符串匹配：命中 → `tags`，未命中 → `candidate_tags`。

- 风险：LLM 可能生成词表词条的近义词，字面匹配失败导致固定 tag 落入候选集

**V3 — 两步分离（有界选择 + 开放生成）**
```
步骤 1：给定 fixed_tags.txt + 译文，从词表中选出适用于本文的条目 → tags
步骤 2：自由从译文提取额外标签，不与步骤 1 重复 → candidate_tags
```
- 优点：步骤 1 是有界选择题（准确率高），步骤 2 是开放生成题，职责不重叠

实验同时验证两个假设：
1. 同一 Subagent 内两阶段机制是否可行（阶段 1 译文上下文能否有效用于阶段 2）
2. 三种 variant 哪种打标质量最优

---

## Section 3：词表与校验

### `fixed_tags.txt` 格式

路径：`~/.hskill/url-extract/fixed_tags.txt`

格式（分组注释平铺文本）：
```
# topic
loop-engineering
ai

# language
english
chinese

# source
substack
twitter
```

`#` 开头行为注释，脚本读取时跳过。

### 初始化

若 `~/.hskill/url-extract/fixed_tags.txt` 不存在，SKILL.md 初始化流程（`NOT_FOUND` 分支）在创建 `config.json` 后，自动生成带分组注释的空模板，提示用户填入初始词条。

### `validate_article.py` 职责

退出 tag 注入角色，改为：

1. **格式校验**：`tags` 和 `candidate_tags` 若存在则必须为合法 YAML 列表
2. **兜底移位**（唯一业务规则）：
   ```
   读取 ~/.hskill/url-extract/fixed_tags.txt 词表
   遍历 candidate_tags：
     若某条目出现在词表中 → 移入 tags，从 candidate_tags 删除
   写回文件
   ```
   保证"固定词不残留在候选集"这一不变式，无论 Subagent 2 使用哪种 variant。

原有格式修复逻辑（大写转小写、逗号分隔转 YAML 列表等）保留。

---

## 实施顺序

1. 写实验脚本，验证两阶段 Subagent 机制 + 三种打标 variant
2. 实验结果确定打标 variant
3. 按本 spec 实现完整改动
4. 更新 `references/file-format.md` 文档
