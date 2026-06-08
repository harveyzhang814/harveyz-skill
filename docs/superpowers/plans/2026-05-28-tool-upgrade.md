# tool 升级改进实施计划

**目标：** 修复 `installTools()` 两个缺陷：`--force` 时清理 `uninstallPaths`（含 venv）；新增版本感知逻辑，outdated 时提示升级而非直接跳过。

**架构：** 仅修改 `lib/installer.js` 的 `installTools()` 函数，将 `destExists && !force` 的跳过逻辑替换为版本对比逻辑，并在确认安装后、写文件前读取 `tool.json` 的 `uninstallPaths` 并清理。

**技术栈：** Node.js ESM, fs-extra, @inquirer/prompts, bats-core

---

### Task 1: 版本感知升级逻辑 + uninstallPaths 清理

**文件：**
- 修改: `lib/installer.js:44-118`（`installTools()` 内 for 循环体）
- 测试: `tests/install.bats`（末尾追加）

#### Step 1: 编写失败测试

在 `tests/install.bats` 末尾追加：

```bash

# ── tool version-aware upgrade ────────────────────────────────────────────────

@test "install --tool: skips with up-to-date message when version matches" {
  _install --tool "${TOOL_NAME}" --force
  # Install again without --force — should see up-to-date, not "already exists"
  run HOME="${MOCK_HOME}" node "${CLI}" install --tool "${TOOL_NAME}" 2>&1
  [[ "$output" == *"up-to-date"* ]]
}

@test "install --tool: skips with outdated message in non-TTY when version differs" {
  _install --tool "${TOOL_NAME}" --force
  # Downgrade the installed version to simulate outdated
  local meta="${MOCK_HOME}/.local/share/hskill/tools/${TOOL_NAME}.json"
  node -e "const f='${meta}'; const fs=require('fs'); const d=JSON.parse(fs.readFileSync(f,'utf8')); d.version='0.0.1'; fs.writeFileSync(f,JSON.stringify(d))"
  run HOME="${MOCK_HOME}" node "${CLI}" install --tool "${TOOL_NAME}" 2>&1
  [[ "$output" == *"outdated"* ]]
  [[ "$output" == *"--force"* ]]
}

@test "install --tool --force: removes uninstallPaths before reinstalling" {
  _install --tool "${TOOL_NAME}" --force
  # Simulate venv created at runtime
  local venv="${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  mkdir -p "$venv"
  _install --tool "${TOOL_NAME}" --force
  [ ! -d "$venv" ]
}

@test "install --tool --force: reinstalls even when up-to-date" {
  _install --tool "${TOOL_NAME}" --force
  local mtime1
  mtime1=$(stat -f '%m' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null || \
           stat -c '%Y' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null)
  sleep 1
  _install --tool "${TOOL_NAME}" --force
  local mtime2
  mtime2=$(stat -f '%m' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null || \
           stat -c '%Y' "${MOCK_HOME}/.local/bin/${TOOL_NAME}" 2>/dev/null)
  [ "$mtime1" != "$mtime2" ]
}
```

#### Step 2: 运行测试确认失败

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/install.bats --filter "version-aware\|uninstallPaths\|reinstalls even" 2>&1 | tail -15
```

预期：4 个测试 FAIL

#### Step 3: 替换 installTools() 中的跳过逻辑

找到 `lib/installer.js` 中 `installTools()` 的这段代码（lines 54–67）：

```js
    const destExists = await fs.pathExists(destPath)
    if (destExists && !force) {
      if (!process.stdout.isTTY) {
        skipped.push({ name: toolName, reason: 'already_exists' })
        console.error(chalk.dim(`  · Skipped ${toolName} (already exists — use --force to overwrite)`))
        continue
      }
      const ok = await confirm({ message: `${destPath} already exists. Overwrite?`, default: true })
      if (!ok) {
        skipped.push({ name: toolName, reason: 'already_exists' })
        console.error(chalk.dim(`  · Skipped ${toolName}`))
        continue
      }
    }
```

替换为：

```js
    const destExists = await fs.pathExists(destPath)
    if (destExists && !force) {
      // Version-aware upgrade logic (mirrors skill behavior)
      const home          = os.homedir()
      const dataDir       = path.join(home, '.local', 'share', 'hskill', 'tools')
      const installedMeta = path.join(dataDir, `${toolName}.json`)
      const sourceMeta    = path.join(srcPath, 'tool.json')

      let installedVersion = '—'
      let sourceVersion    = '—'
      try { installedVersion = (await fs.readJson(installedMeta)).version ?? '—' } catch { /* missing */ }
      try { sourceVersion    = (await fs.readJson(sourceMeta)).version    ?? '—' } catch { /* missing */ }

      const isUpToDate = installedVersion !== '—' && sourceVersion !== '—' && installedVersion === sourceVersion

      if (isUpToDate) {
        skipped.push({ name: toolName, reason: 'up-to-date', version: installedVersion })
        console.error(chalk.dim(`  · Skipped ${toolName} (up-to-date ${installedVersion})`))
        continue
      }

      // Outdated: prompt in TTY, skip in non-TTY
      if (!process.stdout.isTTY) {
        skipped.push({ name: toolName, reason: 'outdated', installed: installedVersion, available: sourceVersion })
        console.error(chalk.dim(`  · Skipped ${toolName} (outdated ${installedVersion} → ${sourceVersion}, use --force to overwrite)`))
        continue
      }

      const ok = await confirm({
        message: `${toolName} ${installedVersion} → ${sourceVersion}. Overwrite?`,
        default: true,
      })
      if (!ok) {
        skipped.push({ name: toolName, reason: 'outdated', installed: installedVersion, available: sourceVersion })
        console.error(chalk.dim(`  · Skipped ${toolName}`))
        continue
      }
    }
```

#### Step 4: 在安装执行块（try 内）写文件前添加 uninstallPaths 清理

找到 `try {` 块的开头（`const varDefs = await loadVarDefs(srcPath)` 行之前），插入：

```js
      // Clean up uninstallPaths declared in tool.json (e.g. venv) before overwriting
      try {
        const meta = await fs.readJson(path.join(srcPath, 'tool.json'))
        const home = os.homedir()
        for (const p of (meta.uninstallPaths ?? [])) {
          const resolved = p.replace(/^~/, home)
          if (await fs.pathExists(resolved)) {
            await fs.remove(resolved)
            console.error(chalk.green(`  ✓ Removed ${p}`))
          }
        }
        if ((meta.uninstallPaths ?? []).length > 0) {
          console.error(chalk.dim(`  · venv will be recreated on next launch`))
        }
      } catch { /* tool.json missing or no uninstallPaths — skip silently */ }
```

#### Step 5: 运行测试确认通过

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/install.bats --filter "version-aware\|uninstallPaths\|reinstalls even\|up-to-date\|outdated" 2>&1 | tail -20
```

预期：新增 4 个测试全部 PASS

#### Step 6: 运行完整测试套件确认无回归

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
bats tests/install.bats 2>&1 | tail -10
```

预期：全部 PASS（注意：原有 `install --tool (no --force): already-installed tool is skipped` 测试行为已改变——现在会显示 `up-to-date` 而非 `already exists`，需确认该测试是否需要更新断言）

如果原有测试 `install --tool (no --force): already-installed tool is skipped` 失败，将其断言从：
```bash
[[ "$output" == *"already exists"* ]]
```
更新为：
```bash
[[ "$output" == *"up-to-date"* ]] || [[ "$output" == *"Skipped"* ]]
```

#### Step 7: 运行全套测试

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
npm test 2>&1 | tail -15
```

预期：全部 PASS

#### Step 8: 提交

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add lib/installer.js tests/install.bats
git commit -m "fix(installer): version-aware tool upgrade and uninstallPaths cleanup on --force

- installTools() now compares installed vs source version (like skills)
- outdated tools prompt in TTY, skip with message in non-TTY
- --force cleans up uninstallPaths (e.g. p-launch venv) before reinstalling

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 收尾 — 更新文档并合并

**文件：**
- 修改: `docs/superpowers/specs/2026-05-28-tool-upgrade-design.md`（已存在）
- 合并到 staging

#### Step 1: 提交 spec 文档

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add docs/superpowers/specs/2026-05-28-tool-upgrade-design.md \
        docs/superpowers/plans/2026-05-28-tool-upgrade.md
git commit -m "docs: add design spec and plan for tool upgrade improvement

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

#### Step 2: 合并到 staging

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git checkout staging
git merge --no-ff feature/tool-upgrade -m "fix: version-aware tool upgrade and venv cleanup on --force

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

#### Step 3: 确认

```bash
git log --oneline -5
```

---

## 自检

### 1. 规格覆盖

| 规格要求 | 对应步骤 |
|----------|---------|
| --force 时清理 uninstallPaths | Task 1 Step 4 |
| 版本一致时 skip + "up-to-date" | Task 1 Step 3 |
| outdated + TTY 时 confirm | Task 1 Step 3 |
| outdated + 非 TTY 时 skip + "outdated … use --force" | Task 1 Step 3 |
| tool.json 缺失时安全回退 | Task 1 Step 3（try/catch） |
| uninstallPaths 不存在时静默跳过 | Task 1 Step 4（try/catch） |
| 打印 "venv will be recreated" | Task 1 Step 4 |

### 2. 占位符扫描

无 TBD / TODO / "后续"。

### 3. 类型一致性

- `skipped.push({ name, reason: 'up-to-date', version })` — 与 skill 逻辑 `{ name, reason: 'up-to-date', version }` 结构一致
- `skipped.push({ name, reason: 'outdated', installed, available })` — 与 skill 逻辑结构一致，CLI 的 `printSummary()` 已支持此格式
