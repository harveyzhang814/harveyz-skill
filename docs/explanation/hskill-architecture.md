# hskill 架构与设计原理

解释 hskill CLI 的整体架构、核心设计决策，以及 skill / tool / hook 三类 item 在安装和版本管理上共享同一套基础设施的原因。

---

## 为什么选择 npm 包方案

hskill 以 npm 包形式发布（`npx harveyz-skill` / 全局安装后的 `hskill` 命令），原因：

- Node.js 是开发者标配，无需额外依赖
- `npx` 支持零安装运行，适合首次体验用户
- `npm publish` 即可分发更新，无需用户手动拉取仓库
- skill 内容直接打包进 `files[]`，安装即可用

---

## 包结构

```
harveyz-skill/
├── bin/
│   └── cli.js              # 入口，解析参数，分发到对应处理器
├── lib/
│   ├── installer.js        # 安装 / 卸载逻辑（installSkills, installTools, installHooks, uninstallTool, uninstallSkill, uninstallHook）
│   └── bundles.js          # 读取 skills-index.json，解析 skill / tool / hook 元数据
├── skills/                 # 所有 skill 目录，随 npm 发布
├── tools/                  # 所有 tool 目录（含 tool.json、.py、zshrc.snippet）
├── scripts/
│   └── hooks/              # hook 脚本（.sh），随 npm 发布
└── skills-index.json       # 单一数据源：skills[]、tools[]、hooks[]、bundleMeta
```

`lib/installer.js` 不依赖 `lib/bundles.js`，保持独立性——installer 在需要元数据时自行用 `fs.readJson` 读取，避免模块间耦合。

---

## skills-index.json 结构

三类 item 在同一文件中声明：

```json
{
  "skills": [
    { "path": "analysis/skill-analyzer", "bundle": "analysis" }
  ],
  "tools": [
    { "path": "tools/p-launch" }
  ],
  "hooks": [
    {
      "name": "check-similar-branch",
      "description": "用 LLM 语义分析检测相似分支",
      "path": "scripts/hooks/check-similar-branch.sh",
      "event": "PreToolUse",
      "matcher": "Bash",
      "timeout": 60,
      "statusMessage": "检查相似分支..."
    }
  ],
  "bundleMeta": {
    "analysis": "分析工具"
  }
}
```

---

## Target 路径映射

`--target` 参数决定 skill 安装到哪个 AI 工具的目录：

| Target | 安装路径（user scope） |
|--------|----------------------|
| `claude` | `~/.claude/skills/` |
| `cursor` | `~/.cursor/skills/` |
| `codex` | `~/.codex/skills/` |
| `openclaw` | `~/.openclaw/skills/` |
| `hermes` | `~/.hermes/skills/` |
| `opencode` | `~/.config/opencode/skills/` |
| `all` | 以上全部 |

目录不存在时跳过并打印警告，不报错退出。

**opencode 路径例外：** opencode 遵循 XDG 约定，user-level 路径为 `~/.config/opencode/skills` 而非常规的 `~/.opencode/skills`。`targets.js` 引入 `USER_DIR_OVERRIDES` 映射表和 `userSkillDir(name)` 函数，集中处理此类路径覆盖，避免在 `skillDir()` 和 `checkInstalled()` 两处分别硬编码。

---

## Scope 模型（user vs project）

每类 item 都有 **user（全局）** 和 **project（项目级）** 两个 scope：

| | User scope | Project scope |
|--|-----------|--------------|
| **Skills** | `~/.{target}/skills/<name>/` | `<cwd>/.{target}/skills/<name>/` |
| **Hooks（脚本）** | `~/.claude/hooks/<name>.sh` | `<cwd>/.claude/hooks/<name>.sh` |
| **Hooks（settings）** | `~/.claude/settings.json` | `<cwd>/.claude/settings.json` |

Project scope 下，`installer.js` 用 `process.cwd()` 作为基准路径，不要求当前目录是 git 仓库。

---

## settings.json Patch 格式

安装 hook 时，installer 向目标 `settings.json` 注入以下结构（已有其他条目时追加到数组，不覆盖）：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/check-similar-branch.sh",
            "timeout": 60,
            "statusMessage": "检查相似分析..."
          }
        ]
      }
    ]
  }
}
```

command 路径规则：
- **user scope** → `~/.claude/hooks/<name>.sh`（绝对路径，硬编码 `~`）
- **project scope** → `bash "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/<name>.sh"`（动态路径，可移植）

---

## 版本检测设计：三类 item 对齐

skills、tools、hooks 三类 item 共享相同的版本感知行为，避免用户体验不一致：

| 状态 | 行为（非 TTY） | 行为（TTY） |
|------|--------------|-----------|
| 未安装 | 直接安装 | 直接安装 |
| 已安装，版本相同 | skip，`reason: up-to-date` | skip，打印 dim 提示 |
| 已安装，版本落后 | skip，`reason: outdated` | 询问是否覆盖 |
| `--force` | 直接覆盖（先清理 uninstallPaths） | 直接覆盖 |

**版本存储位置：**

| Item 类型 | 版本存储位置 |
|-----------|------------|
| Skill | `SKILL.md` frontmatter 的 `version:` 字段 |
| Tool（已安装） | `~/.local/share/hskill/tools/<name>.json` |
| Tool（源）| `tools/<name>/tool.json` 的 `version:` 字段 |
| Hook | 脚本文件头部的 `# version: x.x.x` 注释行 |

Hook 版本写在脚本头部而非 sidecar 文件，是因为脚本本身就是唯一的安装产物——读取同一个文件即可，无需维护额外状态。

---

## tool.json 格式

```json
{
  "name": "p-launch",
  "version": "3.0.0",
  "description": "local repository manager (Python + Textual)",
  "uninstallPaths": [
    "~/.local/share/hskill/p-launch-venv"
  ],
  "configPaths": [
    "~/.config/p-launch"
  ]
}
```

- **`uninstallPaths`**：`hskill uninstall` 时始终删除（venv、数据目录等工具私有文件）
- **`configPaths`**：TTY 时提示确认；非 TTY 时默认保留；`--yes` 时强制删除

`--force` 重装时也会清理 `uninstallPaths`，确保 venv 等依赖随新版本重建，不残留旧状态。

---

## 数据流（install 路径）

```
用户运行 hskill install --skill <name> --target claude --scope user
  → cli.js 解析参数
  → bundles.js 解析 skills-index.json → 找到 skill 元数据
  → installer.js installSkills():
      - 检查已安装版本（读取目标 SKILL.md frontmatter）
      - 版本相同 → skip up-to-date
      - 版本落后 + 非 TTY → skip outdated
      - 版本落后 + TTY → inquirer 询问
      - 确认安装 → 复制 skills/<path>/ → <targetDir>/<skillName>/
  → stdout 输出 JSON 结果（--json 模式）
```

---

## Bundle 管理设计

### 为什么 bundle 操作放在 bundles.js 而不是 installer.js

`installer.js` 负责文件系统写操作（安装、卸载 skill/tool/hook），与 bundle 元数据无关。bundle 管理只涉及 `skills-index.json` 的读写，属于元数据层操作，与 `bundles.js` 现有职责（解析 skills-index.json）天然对齐。引入 `installer.js` 会打破其单一职责，且制造不必要的双向依赖。

`bundles.js` 为此新增三个导出函数：`listBundles()`、`addBundle()`、`renameBundle()`。`cli.js` 的 `bundle` 子命令分支（list / info / add / rename）调用这些函数，`skills-index.json` 结构本身无需变更（`bundleMeta` 字段已存在）。

### bundle add 的幂等性

`hskill bundle add` 若 bundle 已存在，报错退出而非静默覆盖。原因：bundle 描述是人工维护的语义标签，覆盖操作可能导致已有 skill 归属语义丢失，应强制用户使用 `bundle rename` 或手动编辑。

---

## `hskill info` 的类型自动识别与 getItemInfo()

`hskill info <name>` 无需用户指定类型，由 `bundles.js` 中的 `getItemInfo(name)` 按固定优先级查找：

```
1. skills-index.json skills[] → 匹配 path 末尾片段或 skill name
2. skills-index.json tools[]  → 匹配 name
3. skills-index.json hooks[]  → 匹配 name
找不到 → 报错 exit 1
```

找到类型后，`getItemInfo()` 对每个 scope × target 组合调用现有检测函数（`checkSkillInstalled` / `checkToolInstalled` / `checkHookInstalled`），聚合结果为统一结构返回。

### 为什么放在 bundles.js 而不是 installer.js

`installer.js` 只负责写操作（安装 / 卸载），不依赖 `bundles.js`，保持单向依赖关系。`getItemInfo()` 是只读查询，与 `bundles.js` 读取 `skills-index.json` 的职责一致，放在此处不引入循环依赖。

### TTY 下的人读输出

`hskill info` 在 TTY 下输出分层文本格式，结构为：

```
<name>  v<version>  [<bundle>]

  USER SCOPE
    <target>    ✓  v<ver>  <path>
    <target>    —

  PROJECT SCOPE
    <target>    ✓  v<ver>  (outdated)  <path>
```

Tool 和 Hook 无 target × scope 二维结构，直接展示 `INSTALLED` / `STATUS` 行。`--json` 标志绕过 TTY 格式，输出机器可读 JSON（见 reference/agent-cli-guide.md）。

---

## config 子命令的设计原理

### 为什么引入 `hskill config`

hskill 早期没有持久化用户偏好的机制，每次调用都需要显式传 `--target` 和 `--scope`。在使用频率高的场景下（如某台机器始终只用 `claude` target），反复传相同 flag 产生摩擦。`hskill config` 子命令允许用户将常用默认值持久化，后续调用可省略对应 flag。

### 为什么用本地配置文件而非环境变量

配置持久化到 `~/.config/hskill/config.json` 而非环境变量，原因：

- 环境变量在不同 shell session 之间不持久，需要用户在 `.zshrc` 中手动维护
- 配置文件可被版本控制工具检测到并提醒用户，降低遗忘风险
- 多个项目可以有不同的 project-level 配置（`<cwd>/.hskillrc`），环境变量无法做到分层

这一决策的代价是引入了配置文件查找的优先级逻辑：project-level 覆盖 user-level，user-level 覆盖命令行默认值。
