---
name: diataxis-docs
version: "1.0.0"
description: Use when creating, updating, or deleting any file under docs/ — including writing a new guide, updating reference content, adding an ADR, or removing an outdated page. Also use when searching docs before writing, to avoid duplicating existing content.
user_invocable: true
---

# Diataxis 文档管理

本项目 `docs/` 目录遵循 **Diátaxis** 文档方法论。根据操作类型走对应流程。

---

## 先读索引

**任何操作之前**，先读 `docs/INDEX.md`，它列出了所有文件及一句话说明。

- 若 `docs/INDEX.md` 不存在：读 skill 目录下的 `references/index-template.md` 新建它，再继续。

---

## 按操作类型选择流程

### 删除文档

只需一步：从 `docs/INDEX.md` 中移除对应行，然后删除文件。

---

### 修改文档

1. 对照索引确认文件位置和分类（如分类错误，先迁移文件）。
2. 修改内容，遵循该分类的职责边界（见下方「各类型职责」）。
3. 若文档描述变化，同步更新 `docs/INDEX.md` 中对应行。

---

### 新建文档

按顺序完成以下步骤：

#### 1. 内容分类

问自己：**读者到达这篇文档时处于什么状态？**

```
                 学习导向          ←→          工作导向
实践性    │  tutorials/          │  how-to/
          │  （跟着做，学原理）    │  （解决具体问题）
──────────┼──────────────────────┼──────────────────
理论性    │  explanation/        │  reference/
          │  （理解为什么）        │  （查找信息）
```

**判断流程：**

```
内容包含从零开始的引导式练习？
  是 → tutorials/
  否 → 包含完成某个具体任务的操作步骤？
          是 → how-to/
          否 → 包含稳定的事实、规范或 API 定义？
                  是 → reference/
                  否 → explanation/
```

> 项目可能有额外目录（如 `adr/`、`rfcs/`）。需要新建此类目录时，先读 skill 目录下的 `references/custom-categories.md`。

**内容跨越多个分类？** 先拆成独立文档，再对每篇从「内容分类」重新开始走一遍完整流程。

#### 2. 检查已有文档重叠

扫描 INDEX.md 中**同类目录**的条目：

- 已有文件覆盖相同主题 → **更新已有文件**（切换到「修改文档」流程），不要新建。
- 角度不同 → 继续新建，并在两篇文章中互相注明关联。

#### 3. 命名文件

| 类型 | 规则 | 示例 |
|------|------|------|
| 长期文档（tutorials/how-to/reference/explanation） | `kebab-case.md`，不带日期 | `api.md`、`deploy.md` |
| 有时间意义的文档（adr/rfcs/归档等） | `YYYY-MM-DD-topic.md` | `2026-04-23-dag-rewrite.md` |
| 根目录文档 | `SCREAMING_SNAKE.md` | `INDEX.md`、`GUIDE.md` |

#### 4. 写文档

遵循该分类的职责边界（见下方「各类型职责」）。

#### 5. 更新索引

在 `docs/INDEX.md` 对应分类的表格中添加一行：

```
| [路径/文件.md](路径/文件.md) | 一句话说明这篇文档的用途 |
```

描述要简洁、对 Agent 友好——它是判断是否需要读全文的主要依据。

---

## 各类型职责边界

| 类型 | 只包含 | 不包含 |
|------|--------|--------|
| **tutorials** | 引导式步骤，目标是完成一个具体成果 | 原理解释、完整参考信息 |
| **how-to** | 完成具体任务的最短路径 | 为什么这样做的解释 |
| **reference** | 稳定的事实、规范、API 定义 | 操作步骤、设计原理 |
| **explanation** | 背景、原理、设计原因 | 操作步骤、完整参考信息 |

---

## 常见错误

| 错误 | 正确做法 |
|------|---------|
| 在 reference 里写操作步骤 | 步骤移到 `how-to/`，reference 只保留事实 |
| 在 how-to 里解释设计原因 | 原理移到 `explanation/`，how-to 只保留步骤 |
| 跨分类内容不拆分直接新建 | 先拆，对每篇独立走完整流程 |
| 写完文档忘记更新 `docs/INDEX.md` | 最后一步必须更新索引 |
| 长期文档文件名带日期前缀 | 日期前缀只用于有时间意义的文档 |

---

## 参考文件（skill 内置，按需读取）

| 文件 | 何时读 |
|------|--------|
| `references/index-template.md` | `docs/INDEX.md` 不存在，需要初始化时 |
| `references/custom-categories.md` | 需要在四类之外新建额外目录时 |
