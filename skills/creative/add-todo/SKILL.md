---
name: add-todo
version: "3.0.0"
user_invocable: true
description: "Add a new requirement, task, or feature request to any project's TODO list and SQLite task database — from any working directory. Triggers whenever the user wants to capture a new need — even phrased casually like 'we should do X later', 'add this to the backlog', 'note this down', 'remember to build X', or 'we need to do Y at some point'."
---

# 写入 TODO

快速捕获需求：先确认归属项目，再用 2-3 个问题确认**需要做什么**（不是怎么做），生成标题，写入 SQLite，再同步到项目 TODO.md。

## 核心原则

**先定项目，再谈需求。** 问题只聚焦需求本身，不聚焦方案。够写一条清晰的任务条目就停，不要拖长。

---

## 阶段零 — 确认项目归属

### 获取项目列表

```bash
command -v todo >/dev/null 2>&1 \
  && todo project list \
  || python3 -m todo.cli project list
```

输出格式：`  [id] repo_name  /local/path`

### 匹配逻辑

综合以下信号推断候选项目：

1. **当前目录**：`pwd` 是否在某个项目的 `local_path` 内（前缀匹配）→ 强信号
2. **用户描述关键词**：描述中出现的名词、技术词是否与项目名匹配 → 中信号
3. **语义推断**：需求内容在哪个项目的业务范围内 → 弱信号

### 确认策略

| 情况 | 行动 |
|------|------|
| 唯一高置信匹配 | 直接告知并进入阶段一："这是 **[项目名]** 的需求，对吗？" |
| 2-3 个候选 | 列出候选，请用户选择 |
| 无匹配或不确定 | 展示完整项目列表，让用户选 |

> **谨慎原则**：宁可多问一次，不写入错误项目。

---

## 阶段一 — 需求确认（2-3 轮）

**按需提问，已从上下文明确的直接跳过：**

1. **需求** — 要解决什么问题、实现什么功能？（用户已清晰描述则复述确认即可）
2. **紧急程度** — 有多急？（默认 P2，只在用户暗示紧急或不重要时调整）
3. **背景** — 为什么现在提出来？（可选，有助于写出有上下文的描述）

**提问方式：**
- 每次只问一个问题
- 优先给选项而非开放题："这个更像 (A) 缺失功能 还是 (B) 现有功能的问题？"
- 2 轮够用时不要凑到 3 轮

### 生成标题

需求信息收集完毕后，生成任务标题：

- 祈使句，动词开头，直接说明要做什么
- ≤20 字，超出则提炼核心、去掉修饰语
- 足够具体，让人一眼看出任务核心，避免泛泛的"优化"、"修复"
- 不堆砌细节，只抓最关键的区分点

**示例：**
- ✗ "优化系统" → ✓ "重构视频解析模块以支持多格式输入"
- ✗ "修复 bug" → ✓ "修复字幕导出时 UTF-8 编码乱码"
- ✗ "添加功能" → ✓ "为 add-todo skill 添加 SQLite 持久化层"

展示摘要等用户确认：
> "记录为：**[项目名]** — [生成的标题]，[优先级]。确认吗？"

---

## 阶段二 — 写入 SQLite

用户确认后立即执行：

```bash
command -v todo >/dev/null 2>&1 \
  && todo add "[任务标题]" --project "[项目名]" --priority "[P0/P1/P2/P3]" \
  || python3 -m todo.cli add "[任务标题]" --project "[项目名]" --priority "[P0/P1/P2/P3]"
```

写入成功后记录返回的任务 ID。

---

## 阶段三 — 写入本地 TODO.md

### 确定文件路径

从阶段零的 `project list` 输出中取出该项目的 `local_path`，TODO.md 路径为 `{local_path}/TODO.md`。

若该项目无 `local_path`，询问用户本地目录，写入后提示注册：
```bash
todo project set-path [项目名] [本地路径]
```

### 重复检查

加载文件，扫描是否有语义重叠的已有条目。若有：
> "发现可能重叠的条目：**[已有标题]**。这是同一件事还是独立需求？"

由用户决定：跳过、替换或独立写入。

### 写入格式

追加到 `## 🚧 待开发` 末尾：

```markdown
### [任务标题（≤20 字）]
**优先级**: P? | **项目**: [项目名] | **日期**: YYYY-MM-DD

[描述：做什么、为什么。不写怎么做。篇幅以说清楚为准，不限长短。]

---
```

文件不存在则创建，初始结构：

```markdown
# TODO / Backlog

## 🚧 待开发

## ✅ 已完成
```

写入后确认："✅ 已将 **[任务标题]** 写入 `{local_path}/TODO.md`（SQLite ID: [id]）。"
