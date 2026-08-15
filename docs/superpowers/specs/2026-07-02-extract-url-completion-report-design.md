---
title: extract-url 完成回报格式设计
date: 2026-07-02
status: approved
migrated: 2026-07-09
implemented_in:
  - skills/research/extract-url/SKILL.md  # 完成/失败/部分完成/已跳过卡片格式、批量汇总行
  - skills/research/extract-url/scripts/count_article_stats.py  # CHARS/CODE_BLOCKS/IMAGES 统计脚本
---

## 背景

extract-url skill 完成任务后，主 session 向用户展示的回报格式尚未统一。本设计约定最终报告的字段、格式和统计方式。

## 设计目标

- 用户可读性优先：一眼看出结果
- 覆盖范围：主 agent 向用户展示的最终卡片（不约束 subagent 内部输出格式）
- 批量模式：每篇完成立即报告，全部完成后追加汇总行

## 卡片格式

### 成功

```
── 完成 ──────────────────────────────
标题  《文章标题》
路径  /Vault/Reading/article.md
字符  12,345
代码  3 段
图片  8 张
摘要  一句话描述文章核心内容
──────────────────────────────────────
```

### 失败

```
── 失败 ──────────────────────────────
标题  《文章标题》（未知则填原始 URL）
原因  抓取超时（Playwright timeout 300s）
──────────────────────────────────────
```

### 部分完成（抓取成功，翻译失败）

```
── 部分完成 ───────────────────────────
标题  《文章标题》
路径  /Vault/Origin/article.md（仅原文）
原因  翻译超时，原文已保存
──────────────────────────────────────
```

### 已跳过（dedup）

```
── 已跳过 ────────────────────────────
标题  《文章标题》（或原始 URL）
原因  已抓取（dedup）
──────────────────────────────────────
```

### 批量汇总行（所有篇完成后追加）

```
共 5 篇 | 完成 4  失败 1  跳过 0
```

## 字段说明

| 字段 | 出现时机 | 说明 |
|------|----------|------|
| 标题 | 始终 | 文章标题；未知时填原始 URL |
| 路径 | 成功 / 部分完成 | 译文文件绝对路径；部分完成时为 Origin 路径并注明 |
| 字符 | 成功 | 译文正文字符数（跳过 frontmatter） |
| 代码 | 成功 | 译文中 ``` 代码块数量 |
| 图片 | 成功 | 译文中 `![...]` 引用数量 |
| 摘要 | 成功 | 一句话内容摘要（由 Subagent 2 生成并写入 frontmatter，主 agent 从文件读取） |
| 原因 | 失败 / 部分完成 / 跳过 | 一句话说明原因 |

## 执行流程

```
主 agent
  ├─ 派发 Subagent 1（抓取）
  ├─ 等待完成，取 origin_path
  ├─ 派发 Subagent 2（翻译，写入 frontmatter 含 description 字段）
  ├─ 等待完成，取 article_path
  ├─ 运行 scripts/count_article_stats.py <article_path>
  │    → 输出 CHARS: N  CODE_BLOCKS: N  IMAGES: N
  └─ 从 frontmatter 读取 description
  └─ 拼出卡片，展示给用户
```

统计脚本放于：`skills/research/extract-url/scripts/count_article_stats.py`

脚本输出格式（供主 agent 解析）：

```
CHARS: 12345
CODE_BLOCKS: 3
IMAGES: 8
```

## 脚本实现要点

- 跳过 frontmatter（`---` 到第二个 `---` 之间的内容不计入字符数）
- 字符数：正文字符总数（含空格、标点）
- 代码块：统计成对的 ` ``` ` 数量（奇数对视为 0）
- 图片：统计 `![` 出现次数

## 扩展约定（通用卡片壳）

卡片框架（`── 状态 ──` + 字段行 + `────` 分隔线）可作为其他 skill 的通用格式壳，各 skill 自行定义字段列表。本文件仅约定 extract-url 的具体字段。
