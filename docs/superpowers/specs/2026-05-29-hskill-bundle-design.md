---
migrated: 2026-05-29
docs:
  - reference/agent-cli-guide.md        # Bundle management — 命令接口、TTY/JSON 输出格式、bundle list/info/add/rename
  - explanation/hskill-architecture.md  # 为什么 bundle 操作放在 bundles.js、bundle add 非幂等性设计原因
---

# hskill bundle 管理设计

**日期:** 2026-05-29
**状态:** 已批准

## 背景

当前 `skills-index.json` 中的 bundle 元数据（`bundleMeta`）只能通过手动编辑 JSON 维护，没有 CLI 命令可以查看、新建或重命名 bundle。`contribute-skill` skill 在引导用户选 bundle 时需要实时读取 `bundleMeta`，但 hskill 本身对 bundle 的管理是盲区。

## 为什么需要 bundle 子命令

bundle 是 skill 的逻辑分组单位，直接影响 `hskill install --bundle <name>` 的可用性和 `hskill list` 的展示结构。随着 skill 数量增加，bundle 列表需要能被 CLI 直接查询和维护，原因：

- Agent 和 CI 脚本需要通过 `--json` 机器可读地列出所有 bundle 及其 skill
- 用户在 `hskill install` 时常常不知道某个 skill 属于哪个 bundle
- 新增 bundle 目前需要手动编辑 JSON，容易漏掉 `bundleMeta` 或格式出错

## 命令接口

```bash
hskill bundle list [--json]          # 列出所有 bundle 及其包含的 skill
hskill bundle info <name> [--json]   # 查询单个 bundle 详情
hskill bundle add <name> --desc <description>   # 新建 bundle
hskill bundle rename <old> <new>     # 重命名 bundle
```

## 输出格式

### `bundle list --json`

```json
{
  "bundles": {
    "analysis": {
      "description": "分析工具（skill-analyzer + git-cleanup）",
      "skills": ["analysis/skill-analyzer", "analysis/git-cleanup"]
    },
    "meta": {
      "description": "元操作工具（对 harveyz-skill 仓库本身的管理）",
      "skills": ["meta/contribute-skill", "meta/migrate-specs"]
    }
  }
}
```

### `bundle list`（TTY）

```
BUNDLE        SKILLS  DESCRIPTION
────────────────────────────────────────────────────────
analysis      2       分析工具（skill-analyzer + git-cleanup）
brainstorming 2       设计与规划工具
meta          2       元操作工具（对 harveyz-skill 仓库本身的管理）
```

### `bundle info <name> --json`

```json
{
  "name": "analysis",
  "description": "分析工具（skill-analyzer + git-cleanup）",
  "skills": [
    { "path": "analysis/skill-analyzer", "name": "skill-analyzer" },
    { "path": "analysis/git-cleanup",    "name": "git-cleanup" }
  ]
}
```

## 架构设计

### 为什么 bundle 操作放在 bundles.js 而不是 installer.js

`installer.js` 负责文件系统写操作（安装、卸载 skill/tool/hook），与 bundle 元数据无关。bundle 管理只涉及 `skills-index.json` 的读写，属于元数据层操作，与 `bundles.js` 现有职责（解析 skills-index.json）天然对齐。引入 `installer.js` 会打破其单一职责，且制造不必要的双向依赖。

### bundle add 的幂等性

`hskill bundle add` 若 bundle 已存在，报错退出而非静默覆盖。原因：bundle 描述是人工维护的语义标签，覆盖操作可能导致已有 skill 归属语义丢失，应强制用户使用 `bundle rename` 或手动编辑。

## 代码变动范围

| 文件 | 变动 |
|------|------|
| `bin/cli.js` | 新增 `bundle` 子命令分支（list / info / add / rename） |
| `lib/bundles.js` | 新增 `listBundles()`、`addBundle()`、`renameBundle()` |
| `skills-index.json` | 无结构变更，`bundleMeta` 字段已存在 |

## 不在范围内

- `bundle delete`（删除 bundle 需先处理其下所有 skill，交互复杂，独立设计）
- bundle 级别的 install/uninstall（已有 `--bundle` flag）
