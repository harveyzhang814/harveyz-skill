# Hook 版本追踪设计

**日期:** 2026-05-24  
**状态:** 已批准

## 背景

`hskill hooks install` 当前只检查脚本文件是否存在，已安装时直接 skip（原因 `already_exists`），无法感知新版本。Skills 和 Tools 都有版本追踪，hooks 应与之对齐。

## 目标

- hook 脚本携带版本号
- `hskill hooks install` 能区分 up-to-date / outdated / not-installed
- `hskill hooks list` 显示版本列
- `hskill status` hooks 区块显示版本号
- 行为与 skills 安装逻辑完全一致

## 版本存放方式

在脚本头部加 `# version: x.x.x` 注释行（对标 SKILL.md frontmatter）：

```bash
#!/bin/bash
# check-similar-branch.sh
# version: 1.0.0
```

安装后目标脚本（`~/.claude/hooks/<name>.sh` 或 `.claude/hooks/<name>.sh`）携带同样注释，直接从中读取已安装版本，无需 sidecar 文件。

## 数据层变动

### `lib/bundles.js`

新增 `readHookVersion(scriptPath)` 函数：

```js
function readHookVersion(scriptPath) {
  try {
    const content = fs.readFileSync(scriptPath, 'utf-8')
    const m = content.match(/^#\s*version:\s*(.+)$/m)
    return m ? m[1].trim() : '—'
  } catch { return '—' }
}
```

`getAllHookItems()` 加 `version` 字段（从 srcPath 读可用版本）：

```js
export function getAllHookItems() {
  return hookDefs.map(hook => {
    const srcPath = path.join(repoRoot, hook.path)
    return {
      ...hook,
      srcPath,
      version: readHookVersion(srcPath),
    }
  })
}
```

`checkHookInstalled(hookName, availableVersion)` 返回结构加 `version`：

```js
// 返回
{
  user:    { status: 'installed'|'partial'|'none', version: string },
  project: { status: 'installed'|'partial'|'none', version: string },
}
```

`checkScope()` 内部读取已安装脚本的版本：

```js
function checkScope(hooksDir, settingsPath) {
  const scriptPath = path.join(hooksDir, `${hookName}.sh`)
  const scriptExists = fs.existsSync(scriptPath)
  const installedVersion = scriptExists ? readHookVersion(scriptPath) : '—'
  let registered = false
  // ... 现有 settings.json 检测逻辑不变 ...
  return {
    status: scriptExists && registered ? 'installed'
          : scriptExists || registered ? 'partial'
          : 'none',
    version: installedVersion,
  }
}
```

## 安装逻辑变动

### `lib/installer.js` — `installHooks()`

当 `scriptExists && !force` 时，改为版本比较（对标 `installSkills()` 逻辑）：

```
已安装 && 版本相同  → skip，reason: 'up-to-date'，打印 dim 提示
已安装 && 版本不同  → TTY：询问是否覆盖；非 TTY：skip，reason: 'outdated'
未安装             → 正常复制 + patch settings.json
--force            → 无论版本直接覆盖
```

skipped 数组条目新增字段以对齐 skills：

```js
// up-to-date
{ name, reason: 'up-to-date', version: installedVersion }

// outdated
{ name, reason: 'outdated', installed: installedVersion, available: availableVersion }
```

## CLI 展示变动

### `hskill hooks list`

加版本列，对齐 `hskill status` 风格：

```
NAME                         VER    U  P  DESCRIPTION
─────────────────────────────────────────────────────
check-similar-branch         1.0.0  ✓  —  用 LLM 语义分析检测相似分支
```

### `hskill status` hooks 区块

```
hooks:
  check-similar-branch   1.0.0   U:✓  P:—   用 LLM 语义分析检测相似分支
```

## 测试变动

`tests/hooks.bats` 补充版本相关场景：
- `--force` 后版本号随新脚本更新
- 已安装且 up-to-date 时 skip 且 reason 为 `up-to-date`
- outdated 场景（非 TTY）skip 且 reason 为 `outdated`

`tests/hook-script.bats` 不受影响（测脚本行为，与版本无关）。

## 不在范围内

- `hskill hooks outdated` 子命令（版本展示在 `status` 和 `list` 中已够用）
- hook 自动升级（需要 `--force` 或交互确认）
