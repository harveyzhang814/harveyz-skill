# tool 升级改进设计文档

## 概述

修复 `hskill install --tool` 的两个升级缺陷：`--force` 时不清理 venv 导致依赖停留在旧版；tool 缺少版本感知逻辑导致 outdated 时直接跳过而非提示升级。

## 背景

- **venv 问题**：p-launch 首次运行时在 `~/.local/share/hskill/p-launch-venv/` 创建隔离 venv 并安装 textual。`hskill install --tool p-launch --force` 会更新 binary 和 `.py` 文件，但 venv 未被清理，textual 版本永远停在初次安装时。
- **版本感知问题**：skill 安装时会对比已装版本与可用版本，outdated 时提示升级；tool 只检查 binary 是否存在，版本落后时直接跳过，用户必须手动加 `--force`。

## 用户故事

```
# 版本感知升级（outdated，TTY）
hskill install --tool p-launch
  · p-launch 3.0.0 → 3.1.0. Overwrite? (Y/n)  → Y
  ✓ Removed ~/.local/share/hskill/p-launch-venv  (--force cleanup)
  ✓ p-launch installed
  · venv will be recreated on next launch

# 版本感知（up-to-date）
hskill install --tool p-launch
  · Skipped p-launch (up-to-date 3.0.0)

# --force 时清理 venv
hskill install --tool p-launch --force
  ✓ Removed ~/.local/share/hskill/p-launch-venv
  ✓ p-launch installed
```

## 架构设计

### 改动点（2 处）

1. **`lib/installer.js`** — `installTools()` 内部逻辑
2. **`tests/install.bats`** — 补充 venv 清理 + 版本感知测试

### Fix 1：`--force` 时清理 uninstallPaths

在 `installTools()` 中，确认执行安装（用户确认或 `--force`）后、写入新文件前，读取 `tool.json` 的 `uninstallPaths` 并删除：

```
1. 读取 srcPath/tool.json，解析 uninstallPaths[]
2. 对每个路径（支持 ~ 展开）：若存在则 fs.remove()，打印 "✓ Removed ~/<path>"
3. 继续原有的 binary / tool.json / .py 复制逻辑
```

触发条件：用户确认覆盖 OR `--force` 标志（即进入实际安装的代码路径时）。

### Fix 2：tool 版本感知

在 `installTools()` 中，binary 存在时增加版本对比，对齐 skill 逻辑：

```
binary 不存在
  → 直接安装

binary 存在 + --force
  → 清理 uninstallPaths → 安装

binary 存在 + 无 --force
  → 读取 installedVersion（来自 ~/.local/share/hskill/tools/<name>.json）
  → 读取 sourceVersion（来自 srcPath/tool.json）
  → installedVersion === sourceVersion
       → skip，提示 "up-to-date <version>"
  → installedVersion !== sourceVersion + TTY
       → confirm "p-launch <old> → <new>. Overwrite?"
       → yes → 清理 uninstallPaths → 安装
       → no  → skip
  → installedVersion !== sourceVersion + 非 TTY
       → skip，提示 "outdated <old> → <new>, use --force to overwrite"
```

`readToolMeta(path)` 函数已在 `lib/bundles.js` 中存在，但 installer.js 未 import。需要新增一个内联读取函数，或从 bundles.js 导出复用。

**选择**：在 installer.js 内用 `fs.readJson` 直接读取，保持 installer 独立性，不引入 bundles 依赖。

## 错误处理

| 场景 | 行为 |
|------|------|
| tool.json 不存在（无 uninstallPaths）| 跳过 uninstallPaths 清理，正常安装 |
| uninstallPaths 路径不存在 | 静默跳过（不报错） |
| 版本文件（installed .json）缺失 | 视为 "无法比较"，等同 up-to-date 跳过（安全回退） |
| venv 删除失败（权限等） | 打印警告，继续安装其余文件 |

## 测试策略

新增 bats 测试（`tests/install.bats`）：

- `install --tool --force: removes uninstallPaths before reinstalling`
  — 预先创建 fake venv 目录，`--force` 后确认目录已删除
- `install --tool: skips with up-to-date message when version matches`
  — 安装后再次安装（无 force），确认输出含 "up-to-date"
- `install --tool: skips with outdated message in non-TTY when version differs`
  — 安装后手动修改 installed tool.json 的版本，再次安装，确认输出含 "outdated"
- `install --tool --force: reinstalls even when up-to-date`
  — 安装后 `--force` 再装，确认成功覆盖（binary mtime 变化）

## 风险和缓解

| 风险 | 缓解 |
|------|------|
| 版本字段缺失时误判 outdated | 缺失时回退 up-to-date，与现有行为一致 |
| venv 删除后用户启动 p-launch 要等待重建 | 安装成功时打印 "· venv will be recreated on next launch" |
| 非 p-launch 工具没有 uninstallPaths | uninstallPaths 不存在时静默跳过，无副作用 |
