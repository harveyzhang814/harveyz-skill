# hskill uninstall 实施计划

**目标：** 为 hskill 添加 `hskill uninstall <tool>` 命令和 fzf 交互卸载支持，清理工具安装的所有文件。

**架构：** 在 `lib/installer.js` 添加 `uninstallTool()` / `uninstallSkill()` 函数；`bin/cli.js` 添加 `uninstall` 子命令，并在 fzf 交互循环里注入 Action 选择步骤（install / uninstall）；tool-specific 清理路径通过 `tool.json` 的 `uninstallPaths` / `configPaths` 字段声明。

**技术栈：** Node.js ESM, fs-extra, @inquirer/prompts, bats-core

---

### Task 1: 扩展 tool.json 格式

**文件：**
- 修改: `tools/p-launch/tool.json`

- [ ] **Step 1: 更新 tool.json**

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

- [ ] **Step 2: 提交**

```bash
git add tools/p-launch/tool.json
git commit -m "feat(p-launch): declare uninstallPaths and configPaths in tool.json"
```

---

### Task 2: 添加 uninstallTool() 到 lib/installer.js

**文件：**
- 修改: `lib/installer.js`（在文件末尾 export 新函数）
- 测试: `tests/install.bats`（新增 uninstall section）

#### Step 1: 编写失败测试

在 `tests/install.bats` 末尾追加：

```bash
# ── uninstall tool ────────────────────────────────────────────────────────────

_uninstall() {
  HOME="${MOCK_HOME}" node "${CLI}" uninstall "$@" 2>/tmp/bats-uninstall-stderr | cat
}

@test "uninstall: removes binary from ~/.local/bin" {
  _install --tool "${TOOL_NAME}" --force
  [ -x "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/bin/${TOOL_NAME}" ]
}

@test "uninstall: removes tool.json from share dir" {
  _install --tool "${TOOL_NAME}" --force
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.json" ]
}

@test "uninstall: removes companion .py from share dir" {
  _install --tool "${TOOL_NAME}" --force
  _uninstall "${TOOL_NAME}" --yes
  [ ! -f "${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.py" ]
}

@test "uninstall: removes uninstallPaths declared in tool.json" {
  _install --tool "${TOOL_NAME}" --force
  # Simulate venv dir created at runtime
  mkdir -p "${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  _uninstall "${TOOL_NAME}" --yes
  [ ! -d "${MOCK_HOME}/.local/share/hskill/p-launch-venv" ]
}

@test "uninstall: keeps configPaths without --yes in non-TTY" {
  _install --tool "${TOOL_NAME}" --force
  mkdir -p "${MOCK_HOME}/.config/p-launch"
  printf 'PROJECT_DIRS=(%s)\n' "${MOCK_HOME}" > "${MOCK_HOME}/.config/p-launch/config.zsh"
  _uninstall "${TOOL_NAME}"
  [ -f "${MOCK_HOME}/.config/p-launch/config.zsh" ]
}

@test "uninstall: removes configPaths with --yes" {
  _install --tool "${TOOL_NAME}" --force
  mkdir -p "${MOCK_HOME}/.config/p-launch"
  printf 'PROJECT_DIRS=(%s)\n' "${MOCK_HOME}" > "${MOCK_HOME}/.config/p-launch/config.zsh"
  _uninstall "${TOOL_NAME}" --yes
  [ ! -d "${MOCK_HOME}/.config/p-launch" ]
}

@test "uninstall: removes zshrc snippet if present" {
  _install --tool "${TOOL_NAME}" --force
  printf '# >>> p-launch\nexport PATH="$HOME/.local/bin:$PATH"\n# <<< p-launch\n' \
    >> "${MOCK_HOME}/.zshrc"
  _uninstall "${TOOL_NAME}" --yes
  run grep "p-launch" "${MOCK_HOME}/.zshrc"
  [ "$status" -ne 0 ]
}

@test "uninstall: exits 0 when tool is not installed" {
  run _uninstall "${TOOL_NAME}" --yes
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
bats tests/install.bats --filter "uninstall"
```

预期：所有 uninstall 测试 FAIL（命令不存在）

- [ ] **Step 3: 实现 uninstallTool()**

在 `lib/installer.js` 文件末尾，`uninstallHook()` 之后添加：

```js
// ── Tool uninstall ────────────────────────────────────────────────────────────

/**
 * Uninstall a shell tool and clean up all associated files.
 * @param {string} toolName
 * @param {{ yes?: boolean }} opts  - yes: skip configPaths confirmation
 */
export async function uninstallTool(toolName, opts = {}) {
  const { yes = false } = opts
  const home     = os.homedir()
  const binPath  = path.join(home, '.local', 'bin', toolName)
  const dataDir  = path.join(home, '.local', 'share', 'hskill', 'tools')
  const jsonPath = path.join(dataDir, `${toolName}.json`)
  const pyPath   = path.join(dataDir, `${toolName}.py`)

  // Check if installed
  if (!await fs.pathExists(binPath) && !await fs.pathExists(jsonPath)) {
    console.error(chalk.dim(`  · ${toolName} is not installed`))
    return { removed: [], skipped: [], failed: [] }
  }

  const removed  = []
  const skipped  = []
  const failed   = []

  // Read tool.json for extended paths (before removing it)
  let uninstallPaths = []
  let configPaths    = []
  try {
    const meta = JSON.parse(await fs.readFile(jsonPath, 'utf-8'))
    uninstallPaths = (meta.uninstallPaths ?? []).map(p => p.replace(/^~/, home))
    configPaths    = (meta.configPaths    ?? []).map(p => p.replace(/^~/, home))
  } catch { /* tool.json missing or unreadable — proceed with standard paths only */ }

  // Helper: remove a path (file or dir)
  async function removePath(p) {
    if (!await fs.pathExists(p)) return
    try {
      await fs.remove(p)
      console.error(chalk.green(`  ✓ Removed ${p.replace(home, '~')}`))
      removed.push(p)
    } catch (err) {
      console.error(chalk.red(`  ✗ Failed to remove ${p.replace(home, '~')}: ${err.message}`))
      failed.push(p)
    }
  }

  // 1. Standard paths
  await removePath(binPath)
  await removePath(pyPath)
  await removePath(jsonPath)

  // 2. uninstallPaths (always remove)
  for (const p of uninstallPaths) await removePath(p)

  // 3. configPaths (ask or skip)
  for (const p of configPaths) {
    if (!await fs.pathExists(p)) continue
    if (yes) {
      await removePath(p)
    } else if (process.stdout.isTTY) {
      const ok = await confirm({
        message: `Remove ${p.replace(home, '~')}? (user config)`,
        default: false,
      })
      if (ok) {
        await removePath(p)
      } else {
        skipped.push(p)
        console.error(chalk.dim(`  · Kept ${p.replace(home, '~')}`))
      }
    } else {
      skipped.push(p)
      console.error(chalk.dim(`  · Kept ${p.replace(home, '~')} (remove manually if needed)`))
    }
  }

  // 4. Remove zshrc snippet
  const zshrcPath = path.join(home, '.zshrc')
  const startMarker = `# >>> ${toolName}`
  const endMarker   = `# <<< ${toolName}`
  try {
    const content = await fs.readFile(zshrcPath, 'utf-8')
    const startIdx = content.indexOf(startMarker)
    const endIdx   = content.indexOf(endMarker)
    if (startIdx !== -1 && endIdx !== -1) {
      const cleaned = content.slice(0, startIdx) + content.slice(endIdx + endMarker.length + 1)
      await fs.writeFile(zshrcPath, cleaned, 'utf-8')
      console.error(chalk.green(`  ✓ Removed snippet from ~/.zshrc`))
      removed.push('~/.zshrc snippet')
    }
  } catch { /* .zshrc doesn't exist or not readable */ }

  return { removed, skipped, failed }
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
bats tests/install.bats --filter "uninstall"
```

预期：仍 FAIL（CLI 子命令尚未添加）— 只有调用 `uninstallTool()` 的 CLI 测试失败，函数逻辑本身可在下一步集成后一起验证。

- [ ] **Step 5: 提交**

```bash
git add lib/installer.js tests/install.bats
git commit -m "feat: add uninstallTool() to installer.js with tests"
```

---

### Task 3: 添加 uninstallSkill() 到 lib/installer.js

**文件：**
- 修改: `lib/installer.js`
- 测试: `tests/install.bats`（新增 uninstall skill section）

- [ ] **Step 1: 编写失败测试**

在 `tests/install.bats` uninstall section 末尾追加：

```bash
# ── uninstall skill ───────────────────────────────────────────────────────────

@test "uninstall skill: removes skill dir from user claude" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ -d "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}" ]
  HOME="${MOCK_HOME}" node "${CLI}" uninstall "${SKILL1_NAME}" --scope user --target claude
  [ ! -d "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}" ]
}

@test "uninstall skill: exits 0 when skill not installed" {
  run HOME="${MOCK_HOME}" node "${CLI}" uninstall "${SKILL1_NAME}" --scope user --target claude
  [ "$status" -eq 0 ]
}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
bats tests/install.bats --filter "uninstall skill"
```

预期：FAIL

- [ ] **Step 3: 实现 uninstallSkill()**

在 `lib/installer.js` 的 `uninstallTool()` 之后添加：

```js
/**
 * Uninstall a skill from a specific target directory.
 * @param {string} skillName
 * @param {string} targetDir  - full path to target skills dir (e.g. ~/.claude/skills)
 */
export async function uninstallSkill(skillName, targetDir) {
  const skillPath = path.join(targetDir, skillName)
  const removed = [], skipped = [], failed = []

  if (!await fs.pathExists(skillPath)) {
    console.error(chalk.dim(`  · ${skillName} not installed in ${targetDir.replace(os.homedir(), '~')}`))
    skipped.push(skillName)
    return { removed, skipped, failed }
  }

  try {
    await fs.remove(skillPath)
    console.error(chalk.green(`  ✓ Removed ${skillPath.replace(os.homedir(), '~')}`))
    removed.push(skillName)
  } catch (err) {
    console.error(chalk.red(`  ✗ Failed to remove ${skillPath.replace(os.homedir(), '~')}: ${err.message}`))
    failed.push(skillName)
  }

  return { removed, skipped, failed }
}
```

同时在文件顶部 export 列表中补充：

```js
export async function uninstallSkill(skillName, targetDir) { ... }
```

（已在函数定义处 export，无需额外修改）

- [ ] **Step 4: 运行测试确认通过**

```bash
bats tests/install.bats --filter "uninstall skill"
```

预期：仍 FAIL（CLI 子命令未添加）

- [ ] **Step 5: 提交**

```bash
git add lib/installer.js tests/install.bats
git commit -m "feat: add uninstallSkill() to installer.js with tests"
```

---

### Task 4: CLI uninstall 子命令

**文件：**
- 修改: `bin/cli.js`

- [ ] **Step 1: 在 cli.js 顶部 import 新函数**

找到现有 import 行：
```js
import { installSkills, installTools, installHooks, installHooksForTarget, uninstallHook } from '../lib/installer.js'
```

替换为：
```js
import { installSkills, installTools, installHooks, installHooksForTarget, uninstallHook, uninstallTool, uninstallSkill } from '../lib/installer.js'
```

- [ ] **Step 2: 在 help 文本中添加 uninstall**

找到 `printHelp()` 里的 `hskill hooks uninstall` 行，在 `hskill update` 行之前插入：

```js
    hskill uninstall <tool>            uninstall a shell tool
    hskill uninstall <tool> --yes      skip all confirmations (incl. config files)
    hskill uninstall <skill> --scope <s> --target <t>  uninstall a skill
```

同时在 `--help` JSON 的 `commands` 数组中添加：

```js
{
  name: 'uninstall',
  description: 'Uninstall a shell tool or skill',
  args: ['<name>'],
  flags: [
    { name: '--yes',    description: 'Skip all confirmations including config file removal' },
    { name: '--scope',  arg: '<scope>',  description: 'Skill scope: user or project', enum: ['user','project'] },
    { name: '--target', arg: '<target>', description: 'Skill target: claude, cursor, codex, etc.' },
  ],
},
```

- [ ] **Step 3: 实现 uninstall 子命令**

在 `bin/cli.js` 里，`// ── Info ──` 块之后、`// ── Hooks ──` 块之前插入：

```js
// ── Uninstall ─────────────────────────────────────────────────────────────────
if (subcommand === 'uninstall') {
  const nameToRemove = args[1]
  if (!nameToRemove || nameToRemove.startsWith('--')) {
    console.error(chalk.red('  ✗ Usage: hskill uninstall <tool-or-skill-name> [--yes] [--scope user|project] [--target claude|...]'))
    process.exit(1)
  }

  const yesFlag   = args.includes('--yes')
  const scopeIdx2 = args.indexOf('--scope')
  const targetIdx2 = args.indexOf('--target')
  const scopeArg2  = scopeIdx2  !== -1 ? args[scopeIdx2  + 1] : 'user'
  const targetArg2 = targetIdx2 !== -1 ? args[targetIdx2 + 1] : undefined

  // Determine if it's a tool or skill
  const toolItems2  = getAllToolItems()
  const skillItems2 = getAllSkillItems()
  const isTool  = toolItems2.some(t => t.toolName  === nameToRemove)
  const isSkill = skillItems2.some(s => s.skillName === nameToRemove)

  if (!isTool && !isSkill) {
    console.error(chalk.red(`  ✗ Unknown tool or skill: "${nameToRemove}"`))
    process.exit(1)
  }

  if (isTool) {
    const { removed, skipped, failed } = await uninstallTool(nameToRemove, { yes: yesFlag })
    if (removed.length > 0) {
      console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
    }
    process.exit(failed.length ? 1 : 0)
  }

  // Skill uninstall: resolve target dirs
  const scope = scopeArg2
  let selectedTargets = targetArg2 ? [targetArg2] : ['claude', 'cursor', 'codex', 'openclaw', 'hermes']
  const targets = resolveTargets(selectedTargets, scope)

  let anyRemoved = false
  let anyFailed  = false
  for (const { dir } of targets) {
    const { removed, failed } = await uninstallSkill(nameToRemove, dir)
    if (removed.length) anyRemoved = true
    if (failed.length)  anyFailed  = true
  }
  if (anyRemoved) console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
  process.exit(anyFailed ? 1 : 0)
}
```

- [ ] **Step 4: 运行所有 uninstall 测试确认通过**

```bash
bats tests/install.bats --filter "uninstall"
```

预期：全部 PASS

- [ ] **Step 5: 运行完整测试套件确认无回归**

```bash
bats tests/install.bats
```

预期：全部 PASS

- [ ] **Step 6: 提交**

```bash
git add bin/cli.js
git commit -m "feat: add hskill uninstall subcommand for tools and skills"
```

---

### Task 5: fzf 交互界面注入 Action 选择步骤

**文件：**
- 修改: `bin/cli.js`（fzf 交互循环 `while (true)` 块）
- 测试: `tests/interactive.bats`（新增 action 选择测试）

- [ ] **Step 1: 编写失败测试**

查看 `tests/interactive.bats` 现有结构后，在末尾追加：

```bash
# ── fzf action selection ──────────────────────────────────────────────────────

@test "interactive: HSKILL_TEST_UNINSTALL env triggers uninstall action" {
  # Pre-install p-launch
  HOME="${MOCK_HOME}" node "${CLI}" install --tool p-launch --force 2>/dev/null
  [ -x "${MOCK_HOME}/.local/bin/p-launch" ]

  # HSKILL_TEST_ACTION=uninstall bypasses fzf and forces uninstall action
  run env HOME="${MOCK_HOME}" HSKILL_TEST_TOOL="p-launch" HSKILL_TEST_ACTION="uninstall" \
    HSKILL_TEST_YES="1" node "${CLI}"
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_HOME}/.local/bin/p-launch" ]
}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
bats tests/interactive.bats --filter "fzf action"
```

预期：FAIL

- [ ] **Step 3: 在 fzf 循环里注入 Action 选择**

找到 `bin/cli.js` 的 `while (true)` 循环开头（`const selected = fzfSelect()` 之后），在处理 `toolItems`、`skillItems` 之前，插入 Action 选择逻辑：

```js
// ── Action selection (install / uninstall) ───────────────────────────────────
let action = 'install'

// Test hook: bypass fzf action selection
if (process.env.HSKILL_TEST_ACTION) {
  action = process.env.HSKILL_TEST_ACTION
  // Also inject selected item for test
  if (process.env.HSKILL_TEST_TOOL) {
    const testTool = getAllToolItems().find(t => t.toolName === process.env.HSKILL_TEST_TOOL)
    if (testTool) selected.splice(0, selected.length, { kind: 'tool', ...testTool })
  }
} else {
  const actionResult = spawnSync('fzf', [
    '--prompt=  › ',
    '--header=  Action  ·  enter 确认  ·  esc 取消',
    '--layout=reverse',
    '--border=rounded',
    '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
  ], {
    input: `install    安装 / 重新安装\nuninstall  卸载并清理文件`,
    encoding: 'utf8',
    stdio: ['pipe', 'pipe', 'inherit'],
  })
  if (!actionResult.stdout.trim()) {
    console.log(chalk.dim('  · Cancelled'))
    break
  }
  action = actionResult.stdout.trim().startsWith('uninstall') ? 'uninstall' : 'install'
}
```

然后，在 `const toolItems = selected.filter(...)` 之后，用 if/else 将原有安装逻辑包裹在 `action === 'install'` 分支，并添加 `action === 'uninstall'` 分支：

```js
if (action === 'uninstall') {
  const yesFlag2 = !!process.env.HSKILL_TEST_YES
  console.log('')
  for (const item of selected) {
    if (item.kind === 'tool') {
      const { removed, failed } = await uninstallTool(item.toolName, { yes: yesFlag2 })
      if (removed.length) console.error(chalk.green.bold(`✔ ${item.toolName} uninstalled`))
      if (failed.length)  console.error(chalk.red(`  ✗ ${item.toolName}: some files could not be removed`))
    } else if (item.kind === 'skill') {
      // Scope + target selection (reuse existing fzf pickers)
      const scopeRes = spawnSync('fzf', [
        '--prompt=  › ',
        '--header=  Uninstall from scope  ·  enter 确认  ·  esc 取消',
        '--layout=reverse', '--border=rounded',
        '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
      ], {
        input: `user     — ~/.claude/skills/\nproject  — .claude/skills/`,
        encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
      })
      if (!scopeRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
      const scope2 = scopeRes.stdout.trim().startsWith('project') ? 'project' : 'user'

      const targetChoices2 = buildTargetChoices(scope2)
      const targetRes = spawnSync('fzf', [
        '--multi', '--prompt=  › ',
        '--header=  Uninstall from  ·  tab 多选  ·  enter 确认',
        '--layout=reverse', '--border=rounded',
        '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
      ], {
        input: targetChoices2.map(c => c.name).join('\n') + '\nall      — all tools',
        encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
      })
      if (!targetRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
      const selTargets2 = targetRes.stdout.trim().split('\n').map(l => l.trim().split(/\s+/)[0])
      const targets2 = resolveTargets(selTargets2, scope2)
      for (const { dir } of targets2) {
        await uninstallSkill(item.skillName, dir)
      }
    } else if (item.kind === 'hook') {
      // Scope selection
      const hookScopeRes = spawnSync('fzf', [
        '--prompt=  › ',
        '--header=  Hook scope  ·  enter 确认',
        '--layout=reverse', '--border=rounded',
        '--color=header:italic:dim,prompt:cyan,pointer:cyan,hl:cyan,hl+:cyan:bold',
      ], {
        input: `user     — ~/.claude/hooks/\nproject  — .claude/hooks/`,
        encoding: 'utf8', stdio: ['pipe', 'pipe', 'inherit'],
      })
      if (!hookScopeRes.stdout.trim()) { console.log(chalk.dim('  · Cancelled')); break }
      const hookScope2 = hookScopeRes.stdout.trim().startsWith('project') ? 'project' : 'user'
      await uninstallHook(item.name, hookScope2, process.cwd())
    }
  }
  console.log('')
  // Loop back to selector
} else {
  // ── Original install logic (unchanged) ─────────────────────────────────────
  // ... (existing toolItems/skillItems/hookItems install blocks, unchanged)
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
bats tests/interactive.bats --filter "fzf action"
```

预期：PASS

- [ ] **Step 5: 运行完整测试套件确认无回归**

```bash
bats tests/
```

预期：全部 PASS

- [ ] **Step 6: 提交**

```bash
git add bin/cli.js tests/interactive.bats
git commit -m "feat: inject Action selection step (install/uninstall) into fzf interactive loop"
```

---

### Task 6: 更新 TODO.md 和合并到 staging

**文件：**
- 修改: `TODO.md`

- [ ] **Step 1: 把 TODO 项标记为完成**

找到 `TODO.md` 中 `### [ ] Tool uninstall mechanism`，改为：

```markdown
### [x] Tool uninstall mechanism
```

- [ ] **Step 2: 运行完整测试套件最终确认**

```bash
npm test
```

预期：全部 PASS

- [ ] **Step 3: 提交 + 合并到 staging**

```bash
git add TODO.md
git commit -m "chore: mark tool uninstall mechanism as done"

git checkout staging
git merge --no-ff feature/<branch-name> -m "feat: hskill uninstall command and fzf action selection"
```

---

## 自检

### 1. 规格覆盖

| 规格要求 | 对应 Task |
|----------|-----------|
| tool.json 添加 uninstallPaths / configPaths | Task 1 |
| uninstallTool() — 标准路径 + uninstallPaths | Task 2 |
| uninstallTool() — configPaths TTY 询问 / non-TTY 保留 / --yes 强制 | Task 2 |
| uninstallTool() — zshrc snippet 清理 | Task 2 |
| uninstallSkill() | Task 3 |
| CLI `hskill uninstall <tool>` | Task 4 |
| CLI `hskill uninstall <skill> --scope --target` | Task 4 |
| fzf Action 选择步骤（install / uninstall） | Task 5 |
| fzf 卸载支持 tool / skill / hook | Task 5 |
| 工具未安装时幂等 exit 0 | Task 2 Step 3 |
| tool.json 不存在时仍清理标准路径 | Task 2 Step 3 |

### 2. 占位符扫描

无 TBD / TODO / "后续"。

### 3. 类型一致性

- `uninstallTool(toolName, { yes })` — Task 2 定义，Task 4/5 使用，签名一致
- `uninstallSkill(skillName, targetDir)` — Task 3 定义，Task 4/5 使用，签名一致
- `resolveTargets(selectedTargets, scope)` — 现有函数，Task 4/5 直接复用
- `buildTargetChoices(scope)` — 现有函数，Task 5 复用
