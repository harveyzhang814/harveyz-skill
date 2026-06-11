---
migrated: 2026-05-29
docs:
  - how-to/contribute-skill.md
---

# contribute-skill 设计文档

**日期：** 2026-05-24
**状态：** 已实现（v1.0.0）

---

## 概述

`contribute-skill` 是一个元技能（meta skill），允许用户在**任意其他项目**中调用它，将该项目的某个 skill 目录贡献进 `harveyz-skill` 仓库，完成格式规范化、注册登记、双向同步的完整流程。

---

## 位置与注册

| 字段 | 值 |
|------|-----|
| **Skill 目录** | `skills/meta/contribute-skill/` |
| **Bundle** | `meta`（新建） |
| **skills-index.json 条目** | `{"path": "meta/contribute-skill", "bundle": "meta"}` |
| **bundleMeta 新增** | `"meta": "元操作工具（对 harveyz-skill 仓库本身的管理）"` |
| **用户可调用** | `true` |

---

## 触发场景

用户在**非** harveyz-skill 项目中对 Claude 说：

- "把这个 skill 贡献到 harvey-skill"
- "把 `.claude/skills/my-deploy` 导入到 harveyz-skill"
- "将这个 skill 注册进 harvey-skill 仓库"

---

## 执行协议（9 步）

### Step 1 — 识别源 skill 目录

按优先级：

1. **上下文推断**：从对话中当前提到的 skill、文件路径、`SKILL.md` 内容推断
2. **用户显式指定**：用户直接说明路径或名称
3. **扫描列出**：若上下文不明确，扫描当前项目 `.claude/skills/`，列出候选让用户选择

验证：确认目录存在且包含 `SKILL.md`。

---

### Step 2 — 定位 harveyz-skill 仓库

**路径持久化存储：** `~/.claude/skills/contribute-skill/.config`

```json
{
  "harveyzSkillPath": "/absolute/path/to/harveyz-skill"
}
```

**查找逻辑：**

```
读取 .config
  ├── 存在 且 路径下 skills-index.json 存在 → 直接使用，跳过查找
  └── 不存在 or 路径无效
        ├── 尝试 ~/Projects/harveyz-skill
        ├── find ~ -name "skills-index.json" -path "*/harveyz-skill/*" -maxdepth 6
        ├── 仍找不到 → 询问用户手动输入路径
        └── 找到后写入 .config，后续不再查找
```

`.config` 加入 `.gitignore`，不纳入版本控制。

---

### Step 3 — 确定目标名称

- 从源 `SKILL.md` frontmatter 读取 `name:` 字段作为目标目录名
- 展示给用户确认，可修改
- 目标路径：`<harveyzSkillPath>/skills/<category>/<name>/`（category 在 Step 4 确定）

---

### Step 4 — 交互选 bundle

读取 `skills-index.json` 中的 `bundleMeta`，列出所有现有 bundle 及描述：

```
现有 bundle：
  1. analysis    — 分析工具（skill-analyzer + git-cleanup）
  2. brainstorming — 设计与规划工具
  3. meta        — 元操作工具
  ...
  N. [新建 bundle]

请选择目标 bundle（输入编号或新建）：
```

若新建 bundle，追加询问 bundle 描述，用于写入 `bundleMeta`。

---

### Step 5 — 确认摘要

执行前展示完整操作预览，等待用户确认：

```
即将执行以下操作：

[复制]
  源：~/Projects/my-app/.claude/skills/my-deploy/
        ├── SKILL.md
        ├── references/deploy-guide.md
        └── examples/config.yaml
  目标：~/Projects/harveyz-skill/skills/meta/my-deploy/

[注册]
  skills-index.json 新增：{"path": "meta/my-deploy", "bundle": "meta"}

[同步回源]
  格式化后完整目录 → ~/Projects/my-app/.claude/skills/my-deploy/

确认继续？(y/n)
```

---

### Step 6a — 格式规范化

将源 `SKILL.md` 对照 harveyz-skill 规范检查并修复：

**必检字段：**

| 字段 | 规范 | 缺失时处理 |
|------|------|-----------|
| `name` | 必须存在，与目录名一致 | 补填目录名 |
| `description` | 必须含触发短语，2-3 句 | Claude 根据内容补写，展示 diff 确认 |
| `version` | semver 格式（如 `"1.0.0"`） | 补填 `"1.0.0"` |
| `user_invocable` | 显式声明 `true` 或 `false` | 补填 `true` |
| frontmatter 包裹 | 标准 `---` YAML 块 | 修正格式 |

**修复策略：**
- 可自动确定的字段（`name`、`version`、`user_invocable`）：直接修复，无需确认
- 涉及内容重写的字段（`description`）：展示修改前后 diff，让用户确认后再应用

---

### Step 6b — 执行复制与注册

1. 将源 skill 目录**完整复制**到目标位置
2. 用格式化后的 `SKILL.md` **覆盖**目标目录中的 `SKILL.md`
3. 更新 `skills-index.json`：
   - `skills[]` 数组新增 `{"path": "<category>/<name>", "bundle": "<bundle>"}`
   - 若新建 bundle，`bundleMeta` 新增对应条目
4. 运行 `node scripts/generate-npmignore.js`（重新生成 `package.json files[]` 和 `.npmignore`）

**涉及文件汇总：**

| 文件 | 操作 | 执行方式 |
|------|------|---------|
| `skills/<cat>/<name>/` | 新建目录，复制所有文件 | Claude 执行 |
| `skills-index.json` | 新增 skill 条目（+ 可能的 bundleMeta） | Claude 编辑 |
| `package.json` | 更新 `files[]` | 脚本自动生成 |
| `.npmignore` | 更新排除列表 | 脚本自动生成 |

---

### Step 7 — 同步回源仓库

将 harveyz-skill 中目标 skill 目录的**完整内容**同步回源项目：

```
harveyz-skill/skills/<category>/<name>/   →   源项目/.claude/skills/<name>/
```

- 覆盖模式：目标目录中所有文件被覆盖（含格式化后的 `SKILL.md` 及其他文件）
- **若目录内容与源完全一致（无任何变化），跳过 commit**
- 若有变化，在源项目当前分支 commit：
  ```
  chore: sync skill format from harveyz-skill
  ```

---

### Step 8 — 在 harveyz-skill 创建分支并 commit

1. 创建 feature 分支：`feat/contribute-<skill-name>`
2. `git add` 所有变更（新增 skill 目录 + `skills-index.json` + 生成文件）
3. commit：
   ```
   feat: contribute <skill-name> from <source-project-name>
   ```

---

### Step 9 — 报告

输出两个仓库的操作摘要：

```
✓ harveyz-skill
  - 新增 skill：skills/meta/my-deploy/
  - 已注册到 bundle：meta
  - 分支：feat/contribute-my-deploy
  - 下一步：push 并创建 PR → staging

✓ 源项目（my-app）
  - 已同步格式化内容：.claude/skills/my-deploy/
  - commit：chore: sync skill format from harveyz-skill
  （或：无变化，跳过 commit）
```

---

## 边界情况

| 情况 | 处理 |
|------|------|
| 目标路径已存在同名 skill | 提示用户，询问是否覆盖或重命名 |
| 源 `SKILL.md` 格式严重损坏 | 停止执行，报告具体问题，让用户手动修复后重试 |
| `generate-npmignore.js` 执行失败 | 报告错误，不执行 git commit，保留已复制文件供用户检查 |
| 源项目 `.config` 路径失效 | 清除 `.config`，重新触发路径查找流程 |
| 源项目无 git 仓库 | 跳过源项目 commit，仅提示用户文件已同步 |

---

## 不在范围内

- 批量贡献多个 skill（每次只处理一个）
- 自动 push 或创建 PR（用户手动决定）
- 删除或更新已贡献的 skill（独立功能，不在此 skill 范围内）
