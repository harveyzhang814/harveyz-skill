---
name: add-todo
version: "2.0.0"
user_invocable: true
description: "Add a new requirement, task, or feature request to the project TODO list and SQLite task database. Triggers whenever the user wants to capture a new need — even phrased casually like 'we should do X later', 'add this to the backlog', 'note this down', 'remember to build X', or 'we need to do Y at some point'."
---

# 写入 TODO

快速捕获需求：用 2-4 个问题确认**需要做什么**（不是怎么做），然后写入 SQLite 任务库，再同步到项目 TODO.md。

## 核心原则

**问题只聚焦需求本身，不聚焦方案。** 问"是什么"和"为什么"，不问"怎么做"、"怎么验收"、"影响哪些文件"。够写一条清晰的任务条目就停，不要拖长。

---

## 阶段一 — 需求确认（2-4 轮）

**先浏览相关代码或文档**，了解背景，避免问自己能推断出的问题。

**按需提问，已从上下文明确的直接跳过：**

1. **需求** — 要解决什么问题、实现什么功能？（用户已清晰描述则复述确认即可）
2. **项目** — 属于哪个项目？（当前目录名通常即是，不明确时再问）
3. **紧急程度** — 有多急？（默认 P2，只在用户暗示紧急或不重要时调整）
4. **背景** — 为什么现在提出来？（可选，有助于写出有上下文的描述）

**提问方式：**
- 每次只问一个问题
- 优先给选项而非开放题："这个更像 (A) 缺失功能 还是 (B) 现有功能的问题？"
- 2 轮够用时不要凑到 4 轮

完成后展示一句摘要等用户确认：
> "记录为：**[项目名]** — [任务标题]，[优先级]。确认吗？"

---

## 阶段二 — 写入 SQLite

用户确认后立即执行：

```bash
command -v todo >/dev/null 2>&1 \
  && todo add "[任务标题]" --project "[项目名]" --priority "[P0/P1/P2/P3]" \
  || echo "⚠️ todo CLI 未安装，跳过（安装：cd tools/todo-tool && pipx install -e .）"
```

写入成功后记录返回的任务 ID，用于确认消息引用。

---

## 阶段三 — 写入本地 TODO.md

### 确定文件路径

项目根目录下的 `TODO.md`。不存在则直接创建，初始结构：

```markdown
# TODO / Backlog

## 🚧 待开发

## ✅ 已完成
```

### 重复检查

加载文件，扫描是否有语义重叠的已有条目。若有：
> "发现可能重叠的条目：**[已有标题]**。这是同一件事还是独立需求？"

由用户决定：跳过、替换或独立写入。

### 写入格式

追加到 `## 🚧 待开发` 末尾：

```markdown
### [任务标题]（祈使句，≤25 字）
**优先级**: P? | **项目**: [项目名] | **日期**: YYYY-MM-DD

[1-3 句描述：做什么、为什么。不写怎么做。]

---
```

写入后确认："✅ 已将 **[任务标题]** 写入 `TODO.md`（SQLite ID: [id]）。"
