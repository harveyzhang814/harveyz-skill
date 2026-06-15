---
name: manage-dir
version: "1.0.0"
user_invocable: true
description: Use when creating, modifying, or deleting files in any directory that is governed by an explicit organization methodology. Triggers when the user mentions managing files in a directory, adding a document, reorganizing content, or when a target directory contains a DIR_METHOD.md file. Also use when the user asks to "set up a methodology" for a directory or migrate existing files to a new structure.
---

# 目录管理（方法论无关）

本 skill 按目标目录声明的方法论管理其中的文件，操作范围与 diataxis-docs 一致：新建、修改、删除文档，以及维护索引。

---

## 第一步：读取索引与方法论

**任何操作之前**，先读取目标目录的 `INDEX.md`。

**若 INDEX.md 存在：**

解析文件顶部的 YAML frontmatter，查找 `methodology` 字段：

- `methodology: diataxis` → 读取 skill 的 `references/built-in/diataxis.md`
- `methodology: role-based` → 读取 skill 的 `references/built-in/role-based.md`
- 无 `methodology` 字段 → 查找目标目录根目录下的 `DIR_METHOD.md`：
  - 存在 → 读取自定义方法论定义
  - 不存在 → 询问用户选择方法论，确认后写入 INDEX.md frontmatter

**若 INDEX.md 不存在：**

- 查找 `DIR_METHOD.md`：存在 → 按其定义新建 INDEX.md（带 frontmatter）
- 两者都没有 → 引导用户选择方法论，新建 INDEX.md（带 frontmatter），再继续

---

## 第二步：按操作类型执行

### 删除文档

1. 从索引文件中移除对应行。
2. 删除文件。

---

### 修改文档

1. 对照索引确认文件当前分类是否正确（若错误，先迁移文件）。
2. 检查文件名是否符合方法论命名规则；若不符合，向用户提议重命名，并询问确认。重命名时同步更新索引中的路径引用。
3. 修改内容，遵循该分类的职责边界（定义在已加载的方法论中）。
4. 若文档描述变化，同步更新索引对应行。

---

### 新建文档

按顺序完成以下步骤：

#### 1. 分类

按已加载的方法论中的 `classification` 决策流程，判断文档属于哪个分类。

- **内容跨越多个分类**：先拆成独立文档，对每篇重新走分类流程。

#### 2. 检查重叠

扫描索引中**同分类**的现有条目：

- 主题已被覆盖 → **更新已有文件**（切换到「修改文档」流程）
- 角度不同 → 继续新建，并在两篇中互相注明关联

#### 3. 命名文件

按已加载的方法论中 `naming` 字段的规则命名，提议一个文件名，并询问用户是否接受或希望改用其他名称。若用户提供了具体名称，直接使用。

通用默认规则（`naming` 未定义时使用）：

| 场景 | 规则 |
|------|------|
| 长期文档 | `kebab-case.md`，不带日期 |
| 有时间意义的文档 | `YYYY-MM-DD-topic.md` |
| 根目录索引 | `SCREAMING_SNAKE.md` |

#### 4. 写文档

遵循该分类的职责边界（见已加载的方法论中 `categories[*].includes` / `excludes`）。

#### 5. 更新索引

在索引文件的对应分类章节中追加一行：

```
| [路径/文件.md](路径/文件.md) | 一句话说明这篇文档的用途 |
```

描述要简洁、对 Agent 友好——它是判断是否需要读全文的主要依据。

---

## 内置方法论

| 文件 | 方法论 | 适用场景 |
|------|--------|---------|
| `references/built-in/diataxis.md` | Diátaxis | 软件项目的技术文档（tutorials/how-to/reference/explanation） |
| `references/built-in/role-based.md` | 角色分类法 | 知识型项目（研究/写作/竞赛），按 source/analysis/output/working 组织 |

---

## 参考文件（按需读取）

| 文件 | 何时读 |
|------|--------|
| `references/methodology-spec.md` | 需要为目录新建或定义 `DIR_METHOD.md` 时 |
| `references/built-in/diataxis.md` | 目标目录使用 Diátaxis 方法论时 |
| `references/built-in/role-based.md` | 目标目录使用角色分类法时 |
