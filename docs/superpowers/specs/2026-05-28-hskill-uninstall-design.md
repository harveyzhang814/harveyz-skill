---
migrated: 2026-05-29
docs:
  - reference/agent-cli-guide.md       # Uninstall — 命令参考
  - explanation/hskill-architecture.md  # tool.json 格式（uninstallPaths / configPaths）
---

# hskill uninstall 功能设计文档

## 概述

为 hskill CLI 添加 `hskill uninstall <tool-name>` 命令，并在 fzf 交互界面中注入 Action 选择步骤，支持卸载 tool / skill / hook。tool-specific 清理路径通过 `tool.json` 的 `uninstallPaths[]` / `configPaths[]` 字段声明；用户配置文件在非 TTY 时保留、TTY 时询问（或 `--yes` 强制删除）。

## 背景

hskill 目前只能安装和更新，没有卸载命令。p-launch 等工具在用户目录写入多个文件（binary、Python 模块、venv、配置），用户无法通过 hskill 清理。

## 用户故事

```
# CLI 卸载
hskill uninstall p-launch

  ✓ Removed ~/.local/bin/p-launch
  ✓ Removed ~/.local/share/hskill/tools/p-launch.py
  ✓ Removed ~/.local/share/hskill/tools/p-launch.json
  ✓ Removed ~/.local/share/hskill/p-launch-venv/
  · Keep ~/.config/p-launch? (Y/n)  → user says n
  ✓ Removed ~/.config/p-launch
  ✓ Removed snippet from ~/.zshrc
✔ p-launch uninstalled

# fzf 交互卸载
hskill
  → 选中 p-launch
  → Action: [install | uninstall]  选 uninstall
  → 执行卸载流程
```

## 架构设计

### 改动点（4 处）

1. **`tools/p-launch/tool.json`** — 添加 `uninstallPaths` 和 `configPaths` 字段
2. **`lib/installer.js`** — 添加 `uninstallTool()` 和 `uninstallSkill()` 函数
3. **`bin/cli.js`** — 添加 `hskill uninstall <name>` 子命令 + fzf Action 选择步骤

### tool.json 扩展格式

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

- **`uninstallPaths`**：始终删除（venv、数据目录等工具私有文件）
- **`configPaths`**：TTY 时 confirm()；非 TTY 时默认保留并打印提示；`--yes` 时强制删除

### uninstallTool() 逻辑

```
1. 读取 ~/.local/share/hskill/tools/<name>.json，解析 uninstallPaths / configPaths
2. 标准路径（始终清理）：
   - ~/.local/bin/<name>
   - ~/.local/share/hskill/tools/<name>.py   （若存在）
   - ~/.local/share/hskill/tools/<name>.json
3. uninstallPaths：遍历删除（~ 展开）
4. configPaths：TTY 时 confirm()，非 TTY 时跳过，--yes 时直接删
5. ~/.zshrc snippet：按 marker `# >>> <name>` 删除区块
6. 返回 { removed[], skipped[], failed[] }
```

### uninstallSkill() 逻辑

```
1. 接收 skillName, scope（user/project）, targets（claude/cursor/...）
2. 删除对应目录 <targetDir>/<skillName>/
3. 返回 { removed[], skipped[], failed[] }
```

（hook 卸载已有 `uninstallHook()`，直接复用）

### fzf 交互流程变更

```
选择 items
  → Action 选择 [install | uninstall]
     ├─ install  → 原有 scope → target → install 逻辑
     └─ uninstall
          ├─ tools  → uninstallTool()
          ├─ skills → (scope/target 选择) → uninstallSkill()
          └─ hooks  → (scope 选择) → uninstallHook()
```

## CLI 接口

```
hskill uninstall <tool-name>        卸载工具（configPaths TTY 询问）
hskill uninstall <tool-name> --yes  跳过所有确认（含 configPaths）
```

help 文本同步更新。

## 错误处理

| 场景 | 行为 |
|------|------|
| 工具未安装（binary 不存在） | 提示 `· p-launch is not installed` 并 exit 0 |
| tool.json 不存在（旧版安装） | 仍清理标准路径，跳过 uninstallPaths/configPaths |
| 删除失败（权限等） | 打印 `✗ Failed to remove ...`，继续后续步骤，最终 exit 1 |
| 非 TTY + configPaths | 打印 `· Kept ~/.config/p-launch (remove manually if needed)` |
| skill 目录不存在 | 打印 `· <skillName> not installed in <scope>/<target>` |

## 测试策略

- **`lib/installer.js` 单元测试**（Jest/Node）：
  - `uninstallTool()` 覆盖：标准路径清理、uninstallPaths 删除、configPaths 保留/删除、zshrc snippet 清理、tool 未安装时的幂等行为
  - `uninstallSkill()` 覆盖：目录存在/不存在两种情况
- **`bin/cli.js` 集成测试**：`hskill uninstall p-launch --yes` 端到端冒烟测试
- **fzf 流程**：现有交互测试框架覆盖 Action 选择步骤（非 TTY 跳过）

## 风险和缓解

| 风险 | 缓解 |
|------|------|
| 误删用户配置 | configPaths 默认保留，需明确确认或 --yes |
| venv 删除耗时 | `fs.remove()` 异步，正常情况下秒级完成 |
| 旧版安装无 tool.json | 降级：只清理标准路径，不报错 |
| fzf uninstall 选项对未安装 item 显示 | Action 步骤展示时可过滤；未安装时 uninstallTool 幂等返回 |
