# Skill 命名规范 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `<动词>-<名词>` 规范重命名仓库内 22 个 skill，并在 `hskill update` 时自动迁移用户各平台已安装的旧名称目录。

**Architecture:** 分四层改动：① 仓库内 skill 目录重命名 + SKILL.md frontmatter 更新；② `skills-index.json` 同步路径 + 新增 `renames[]`；③ `lib/installer.js` 新增 `migrateRenamedSkills()` 函数；④ `bin/cli.js` 的 `update` 命令执行完 npm 更新后调用迁移。

**Tech Stack:** Node.js ESM、fs-extra、chalk、bats（测试）

---

## 文件修改清单

| 操作 | 路径 |
|---|---|
| Modify | `skills-index.json` |
| Rename × 22 | `skills/<cat>/<old>/` → `skills/<cat>/<new>/` |
| Modify × 22 | `skills/<cat>/<new>/SKILL.md`（`name:` 字段 + description 中旧斜杠命令） |
| Modify | `lib/installer.js`（新增 `migrateRenamedSkills`） |
| Modify | `bin/cli.js`（`update` handler 调用迁移） |
| Modify | `tests/install.bats` |
| Modify | `tests/agent-cli.bats` |
| Modify | `tests/interactive.bats` |

---

## Task 1: 更新 skills-index.json

**Files:**
- Modify: `skills-index.json`

- [ ] **Step 1: 在 `skills-index.json` 顶层添加 `renames` 字段**

在 `"bundleMeta"` 之前插入：

```json
"renames": [
  { "from": "url-extract",          "to": "extract-url" },
  { "from": "vision-extract",       "to": "extract-vision" },
  { "from": "youtube-learner",      "to": "learn-video" },
  { "from": "add-todo",             "to": "capture-todo" },
  { "from": "insight",              "to": "capture-insight" },
  { "from": "git-workflow-init",    "to": "init-workflow" },
  { "from": "full-stack-debug-env", "to": "setup-debug" },
  { "from": "pm-task-dispatch",     "to": "dispatch-task" },
  { "from": "task-close",           "to": "close-task" },
  { "from": "doc-forge",            "to": "forge-doc" },
  { "from": "diagram",              "to": "draw-diagram" },
  { "from": "diataxis-docs",        "to": "manage-docs" },
  { "from": "dir-manage",           "to": "manage-dir" },
  { "from": "migrate-specs",        "to": "migrate-spec" },
  { "from": "brand-scout",          "to": "scout-brand" },
  { "from": "style-build",          "to": "build-style" },
  { "from": "sync-design-html",     "to": "sync-design" },
  { "from": "git-cleanup",          "to": "clean-git" },
  { "from": "skill-analyzer",       "to": "analyze-skill" },
  { "from": "skill-publish",        "to": "publish-skill" },
  { "from": "opencode-runner",      "to": "runby-opencode" },
  { "from": "project-release",      "to": "release-project" }
],
```

- [ ] **Step 2: 更新 `skills[]` 数组中每条记录的 `path` 字段**

将以下 22 条旧路径替换为新路径（其他字段不变）：

```
research/url-extract          → research/extract-url
research/vision-extract       → research/extract-vision
research/youtube-learner      → research/learn-video
creative/add-todo             → creative/capture-todo
creative/insight              → creative/capture-insight
coding/git-workflow-init      → coding/init-workflow
coding/full-stack-debug-env   → coding/setup-debug
coding/pm-task-dispatch       → coding/dispatch-task
coding/task-close             → coding/close-task
writing/doc-forge             → writing/forge-doc
writing/diagram               → writing/draw-diagram
writing/diataxis-docs         → writing/manage-docs
writing/dir-manage            → writing/manage-dir
writing/migrate-specs         → writing/migrate-spec
design/brand-scout            → design/scout-brand
design/style-build            → design/build-style
design/sync-design-html       → design/sync-design
meta/git-cleanup              → meta/clean-git
meta/skill-analyzer           → meta/analyze-skill
meta/skill-publish            → meta/publish-skill
meta/opencode-runner          → meta/runby-opencode
meta/project-release          → meta/release-project
```

- [ ] **Step 3: 验证 JSON 合法**

```bash
node -e "JSON.parse(require('fs').readFileSync('skills-index.json','utf-8')); console.log('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "chore: update skills-index.json for naming convention rename"
```

---

## Task 2: 批量重命名 skill 目录 + 更新 SKILL.md

**Files:**
- Rename × 22: `skills/<cat>/<old>/` → `skills/<cat>/<new>/`
- Modify × 22: `skills/<cat>/<new>/SKILL.md` (`name:` 字段)

- [ ] **Step 1: 执行批量目录重命名**

```bash
# research
mv skills/research/url-extract        skills/research/extract-url
mv skills/research/vision-extract     skills/research/extract-vision
mv skills/research/youtube-learner    skills/research/learn-video

# creative
mv skills/creative/add-todo           skills/creative/capture-todo
mv skills/creative/insight            skills/creative/capture-insight

# coding
mv skills/coding/git-workflow-init    skills/coding/init-workflow
mv skills/coding/full-stack-debug-env skills/coding/setup-debug
mv skills/coding/pm-task-dispatch     skills/coding/dispatch-task
mv skills/coding/task-close           skills/coding/close-task

# writing
mv skills/writing/doc-forge           skills/writing/forge-doc
mv skills/writing/diagram             skills/writing/draw-diagram
mv skills/writing/diataxis-docs       skills/writing/manage-docs
mv skills/writing/dir-manage          skills/writing/manage-dir
mv skills/writing/migrate-specs       skills/writing/migrate-spec

# design
mv skills/design/brand-scout          skills/design/scout-brand
mv skills/design/style-build          skills/design/build-style
mv skills/design/sync-design-html     skills/design/sync-design

# meta
mv skills/meta/git-cleanup            skills/meta/clean-git
mv skills/meta/skill-analyzer         skills/meta/analyze-skill
mv skills/meta/skill-publish          skills/meta/publish-skill
mv skills/meta/opencode-runner        skills/meta/runby-opencode
mv skills/meta/project-release        skills/meta/release-project
```

- [ ] **Step 2: 批量更新 SKILL.md 中的 `name:` 字段**

```bash
# 用 sed 逐一替换 frontmatter name 字段（精确匹配行首）
pairs=(
  "extract-url:url-extract"
  "extract-vision:vision-extract"
  "learn-video:youtube-learner"
  "capture-todo:add-todo"
  "capture-insight:insight"
  "init-workflow:git-workflow-init"
  "setup-debug:full-stack-debug-env"
  "dispatch-task:pm-task-dispatch"
  "close-task:task-close"
  "forge-doc:doc-forge"
  "draw-diagram:diagram"
  "manage-docs:diataxis-docs"
  "manage-dir:dir-manage"
  "migrate-spec:migrate-specs"
  "scout-brand:brand-scout"
  "build-style:style-build"
  "sync-design:sync-design-html"
  "clean-git:git-cleanup"
  "analyze-skill:skill-analyzer"
  "publish-skill:skill-publish"
  "runby-opencode:opencode-runner"
  "release-project:project-release"
)

for pair in "${pairs[@]}"; do
  new="${pair%%:*}"
  old="${pair##*:}"
  # Find the SKILL.md in the new directory location
  skill_file=$(find skills -name "SKILL.md" | xargs grep -l "^name: ${old}$" 2>/dev/null | head -1)
  if [ -n "$skill_file" ]; then
    sed -i '' "s/^name: ${old}$/name: ${new}/" "$skill_file"
    echo "Updated $skill_file: $old → $new"
  else
    echo "WARNING: SKILL.md with name: $old not found"
  fi
done
```

- [ ] **Step 3: 验证所有 name 字段已更新**

```bash
# 验证旧名称不再出现于 name: 行
old_names=(url-extract vision-extract youtube-learner add-todo insight git-workflow-init \
  full-stack-debug-env pm-task-dispatch task-close doc-forge diagram diataxis-docs \
  dir-manage migrate-specs brand-scout style-build sync-design-html git-cleanup \
  skill-analyzer skill-publish opencode-runner project-release)

for name in "${old_names[@]}"; do
  count=$(grep -r "^name: ${name}$" skills/ | grep -v archived | wc -l)
  if [ "$count" -gt 0 ]; then
    echo "FAIL: old name still present: $name"
  fi
done
echo "Verification done"
```

Expected: `Verification done`（无 FAIL 行）

- [ ] **Step 4: 更新 SKILL.md description 中引用旧斜杠命令名的文字**

搜索 description 字段中仍引用旧名称的 SKILL.md，手动核查并更新。常见模式为 `` `/old-name` `` 或 `` `/brand-scout` ``：

```bash
grep -r "brand-scout\|style-build\|sync-design-html\|doc-forge\|url-extract\|youtube-learner\|dir-manage\|diataxis-docs" skills/*/SKILL.md skills/*/*/SKILL.md 2>/dev/null | grep -v "^Binary"
```

对每处命中，将 description 里的旧斜杠命令名更新为新名称。例如：
- `"/brand-scout"` → `"/scout-brand"`
- `"/style-build"` → `"/build-style"`

- [ ] **Step 5: Commit**

```bash
git add skills/
git commit -m "feat: rename 22 skill directories to verb-noun convention"
```

---

## Task 3: 更新测试文件

**Files:**
- Modify: `tests/install.bats`
- Modify: `tests/agent-cli.bats`
- Modify: `tests/interactive.bats`

- [ ] **Step 1: 替换 install.bats 中的旧 skill 名**

`tests/install.bats` 第 15-16 行及第 152 行引用 `skill-analyzer`，改为 `analyze-skill`：

```bash
# Line 15
SKILL1_NAME="analyze-skill"
# Line 16
SKILL1_SRC="${REPO_ROOT}/skills/meta/analyze-skill"
# Line 152 comment: "meta bundle contains analyze-skill."
```

- [ ] **Step 2: 替换 agent-cli.bats 中的旧 skill 名**

将所有 `skill-analyzer` 替换为 `analyze-skill`（共 6 处）：

```bash
sed -i '' 's/skill-analyzer/analyze-skill/g' tests/agent-cli.bats
```

验证：
```bash
grep "skill-analyzer" tests/agent-cli.bats
```
Expected: 无输出

- [ ] **Step 3: 替换 interactive.bats 中的旧 skill 名**

```bash
sed -i '' 's/skill-analyzer/analyze-skill/g' tests/interactive.bats
```

验证：
```bash
grep "skill-analyzer" tests/interactive.bats
```
Expected: 无输出

- [ ] **Step 4: 运行测试确认通过**

```bash
npm test 2>&1 | grep -E "OK|FAIL|passed|failed"
```

Expected: `OK` 行出现，原先通过的测试数量不减少（doc-forge Python 测试的失败是预存在问题，不计入）。

- [ ] **Step 5: Commit**

```bash
git add tests/install.bats tests/agent-cli.bats tests/interactive.bats
git commit -m "test: update skill references to new naming convention"
```

---

## Task 4: 实现 migrateRenamedSkills()

**Files:**
- Modify: `lib/installer.js`

- [ ] **Step 1: 在 `lib/installer.js` 末尾追加 `migrateRenamedSkills` 函数**

在文件末尾（`uninstallHook` 函数之后）添加：

```js
/**
 * Migrate renamed skills across all user-level target platforms.
 * Reads renames[] from skills-index.json and removes old dirs, installs new ones.
 *
 * @param {Array<{from: string, to: string}>} renames
 * @param {Array<{name: string, dir: string}>} targets  - from resolveTargets()
 * @param {string} skillsRoot  - absolute path to the skills/ source directory
 * @param {Array<{path: string, bundle: string}>} skillDefs - skills[] from skills-index.json
 * @returns {Promise<Object>} summary keyed by target name
 */
export async function migrateRenamedSkills(renames, targets, skillsRoot, skillDefs) {
  const summary = {}

  for (const { name: targetName, dir: targetDir } of targets) {
    if (!await fs.pathExists(targetDir)) continue

    const migrated = []
    const skipped  = []
    const failed   = []

    for (const { from: oldName, to: newName } of renames) {
      const oldPath = path.join(targetDir, oldName)
      if (!await fs.pathExists(oldPath)) {
        skipped.push({ from: oldName, to: newName, reason: 'not_installed' })
        continue
      }

      // Find source for new name
      const skillDef = skillDefs.find(s => s.path.split('/').pop() === newName)
      if (!skillDef) {
        failed.push({ from: oldName, to: newName, reason: 'source_not_found' })
        console.error(chalk.red(`  ✗ No source found for ${newName}`))
        continue
      }

      const srcPath = path.join(skillsRoot, skillDef.path)
      const newPath = path.join(targetDir, newName)

      try {
        await fs.remove(oldPath)
        await copyDir(srcPath, newPath, {})
        migrated.push({ from: oldName, to: newName })
        console.error(chalk.green(`  ✓ ${targetName}: ${oldName} → ${newName}`))
      } catch (err) {
        failed.push({ from: oldName, to: newName, reason: err.message })
        console.error(chalk.red(`  ✗ ${targetName}: ${oldName} → ${newName}: ${err.message}`))
      }
    }

    summary[targetName] = { migrated, skipped, failed }
  }

  return summary
}
```

- [ ] **Step 2: 验证文件可被 Node.js 解析**

```bash
node --input-type=module <<'EOF'
import { migrateRenamedSkills } from './lib/installer.js'
console.log(typeof migrateRenamedSkills)
EOF
```

Expected: `function`

- [ ] **Step 3: Commit**

```bash
git add lib/installer.js
git commit -m "feat(installer): add migrateRenamedSkills() for hskill update flow"
```

---

## Task 5: 在 hskill update 中调用迁移

**Files:**
- Modify: `bin/cli.js`

- [ ] **Step 1: 在 cli.js 顶部导入 `migrateRenamedSkills` 和 `resolveTargets`**

`resolveTargets` 已导入（第 16 行）。将 `migrateRenamedSkills` 加入 installer.js 的导入行（当前第 17 行）：

```js
import { installSkills, installTools, installHooks, installHooksForTarget, uninstallHook, uninstallTool, uninstallSkill, migrateRenamedSkills } from '../lib/installer.js'
```

- [ ] **Step 2: 在 `update` handler 中，npm 成功后调用迁移（替换当前 148-166 行）**

```js
if (subcommand === 'update') {
  console.log(chalk.dim('  · Updating hskill…'))
  try {
    execSync('npm update -g harveyz-skill', { stdio: 'inherit' })
    console.log(chalk.green('  ✔ hskill updated'))
  } catch {
    console.error(chalk.red('  ✗ Update failed. Try: npm update -g harveyz-skill'))
    process.exit(1)
  }

  // Migrate renamed skills across all user-level target platforms
  const { renames = [], skills: skillDefs = [] } = require('../skills-index.json')
  if (renames.length > 0) {
    console.log('')
    console.log(chalk.dim('  · Migrating renamed skills…'))
    const { SKILL_TARGETS, userSkillDir } = await import('../lib/targets.js')
    const targets = SKILL_TARGETS.map(name => ({ name, dir: userSkillDir(name) }))
    const skillsRoot = path.join(__dirname, '..', 'skills')
    const migrationSummary = await migrateRenamedSkills(renames, targets, skillsRoot, skillDefs)

    const totalMigrated = Object.values(migrationSummary).reduce((n, s) => n + s.migrated.length, 0)
    const totalFailed   = Object.values(migrationSummary).reduce((n, s) => n + s.failed.length, 0)

    if (totalMigrated > 0) console.log(chalk.green(`  ✔ Migrated ${totalMigrated} skill(s)`))
    if (totalFailed   > 0) console.log(chalk.yellow(`  ⚠ ${totalFailed} migration(s) failed — check output above`))
  }

  const legacyDir = path.join(os.homedir(), '.local', 'share', 'hskill')
  if (existsSync(legacyDir)) {
    console.log('')
    console.log(chalk.yellow('  ⚠ Legacy data detected at ~/.local/share/hskill/'))
    console.log(chalk.dim('  Run the migration script to move data to the new location:'))
    console.log('')
    console.log('     ' + chalk.bold.cyan('bash "$(npm root -g)/harveyz-skill/scripts/migrate-data-dir.sh"'))
    console.log('')
  }
  process.exit(0)
}
```

- [ ] **Step 3: 冒烟测试（dry run，不实际跑 npm update）**

在 update handler 之外临时验证导入正确：

```bash
node -e "
import('./lib/installer.js').then(m => {
  console.log('migrateRenamedSkills:', typeof m.migrateRenamedSkills)
}).catch(e => console.error(e))
"
```

Expected: `migrateRenamedSkills: function`

- [ ] **Step 4: Commit**

```bash
git add bin/cli.js
git commit -m "feat(cli): run skill migration on hskill update"
```

---

## Task 6: 全量验证

- [ ] **Step 1: 运行完整测试套件**

```bash
npm test 2>&1
```

Expected: `custom skill tests: 1 passed, 1 failed (2 total)`（doc-forge Python 失败是预存在问题，JS 测试全部通过）

- [ ] **Step 2: 验证 skill-publish 检查通过（每个 skill 的 name 与目录名匹配）**

```bash
node -e "
import('./lib/bundles.js').then(m => {
  const items = m.getAllSkillItems()
  const { createRequire } = await import('module')
  // just check paths resolve
  console.log('skill count:', items.length)
})
" 2>/dev/null || echo "manual check needed"
```

手动确认：

```bash
# 验证每个 skill 目录的 SKILL.md name 字段与目录名一致
find skills -name "SKILL.md" | grep -v archived | while read f; do
  dir=$(basename $(dirname "$f"))
  name=$(grep "^name:" "$f" | head -1 | sed 's/name: *//')
  if [ "$dir" != "$name" ]; then
    echo "MISMATCH: dir=$dir  name=$name  ($f)"
  fi
done
echo "Done"
```

Expected: `Done`（无 MISMATCH 行）

- [ ] **Step 3: 验证 skills-index.json 中路径与实际目录对应**

```bash
node -e "
const idx = JSON.parse(require('fs').readFileSync('skills-index.json','utf-8'))
const fs = require('fs')
let ok = true
for (const s of idx.skills) {
  const p = 'skills/' + s.path
  if (!fs.existsSync(p)) { console.log('MISSING:', p); ok = false }
}
if (ok) console.log('All paths OK')
"
```

Expected: `All paths OK`

- [ ] **Step 4: Final commit（如有遗漏文件）**

```bash
git status
# 如有未提交文件：
git add -A
git commit -m "chore: finalize skill naming convention rename"
```
