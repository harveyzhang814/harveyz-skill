# Skill Vars Substitution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 安装 skill 时，自动将文件内的 `{{VAR_NAME}}` 占位符替换为用户输入的本机路径，无需手动编辑安装后的文件。

**Architecture:** 每个需要配置路径的 skill 目录放一个 `vars.json`，声明所需变量及默认值。安装时 `lib/vars.js` 读取该文件、提示用户输入、返回替换映射；`lib/installer.js` 按文件逐一复制，文本文件执行变量替换，二进制文件直接复制，`vars.json` 本身不写入目标目录。

**Tech Stack:** Node.js ESM, `@inquirer/prompts` (input), `fs-extra`, `path`, `os`

---

### Task 1：创建 `lib/vars.js`

**Files:**
- Create: `lib/vars.js`

- [ ] **Step 1：写文件**

```js
// lib/vars.js
import fs from 'fs-extra'
import path from 'path'
import os from 'os'
import { input } from '@inquirer/prompts'

export function buildAutoVars() {
  return { HOME: os.homedir() }
}

export async function loadVarDefs(skillSrcPath) {
  const varsFile = path.join(skillSrcPath, 'vars.json')
  if (!await fs.pathExists(varsFile)) return []
  return fs.readJson(varsFile)
}

export function substituteVars(text, varsMap) {
  return text.replace(/\{\{(\w+)\}\}/g, (_, name) => varsMap[name] ?? `{{${name}}}`)
}

export async function resolveVars(varDefs, autoVars) {
  const result = { ...autoVars }
  for (const def of varDefs) {
    const defaultVal = substituteVars(def.default ?? '', autoVars)
    const value = await input({
      message: `${def.description}:`,
      default: defaultVal,
    })
    result[def.name] = value
  }
  return result
}
```

- [ ] **Step 2：手动验证 substituteVars**

在终端运行：

```bash
node --input-type=module <<'EOF'
import { substituteVars } from './lib/vars.js'
import assert from 'assert'

const map = { HOME: '/Users/test', VAULT_PATH: '/Users/test/Vault' }
assert.strictEqual(
  substituteVars('Path: {{VAULT_PATH}}/Origin', map),
  'Path: /Users/test/Vault/Origin'
)
assert.strictEqual(
  substituteVars('{{UNKNOWN}} stays', map),
  '{{UNKNOWN}} stays'
)
assert.strictEqual(
  substituteVars('Home is {{HOME}}', map),
  'Home is /Users/test'
)
console.log('✔ substituteVars 通过')
EOF
```

期望输出：`✔ substituteVars 通过`

- [ ] **Step 3：提交**

```bash
git add lib/vars.js
git commit -m "feat: add vars.js for skill template variable resolution"
```

---

### Task 2：更新 `lib/installer.js`

**Files:**
- Modify: `lib/installer.js`

- [ ] **Step 1：替换为支持变量替换的版本**

```js
import fs from 'fs-extra'
import path from 'path'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'
import { loadVarDefs, buildAutoVars, resolveVars, substituteVars } from './vars.js'

const BINARY_EXTS = new Set(['.db', '.pyc', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf'])
const SKIP_NAMES  = new Set(['vars.json', '__pycache__', '.DS_Store'])

async function copyDir(srcDir, destDir, varsMap) {
  await fs.ensureDir(destDir)
  const entries = await fs.readdir(srcDir, { withFileTypes: true })
  for (const entry of entries) {
    if (SKIP_NAMES.has(entry.name)) continue
    const src  = path.join(srcDir, entry.name)
    const dest = path.join(destDir, entry.name)
    if (entry.isDirectory()) {
      await copyDir(src, dest, varsMap)
    } else if (Object.keys(varsMap).length > 0 && !BINARY_EXTS.has(path.extname(entry.name).toLowerCase())) {
      const content = await fs.readFile(src, 'utf-8')
      await fs.writeFile(dest, substituteVars(content, varsMap), 'utf-8')
    } else {
      await fs.copy(src, dest, { overwrite: true })
    }
  }
}

// skills: [{ skillName, srcPath }]
// targets: [{ name, dir }]
// force: boolean
export async function installSkills(skills, targets, force = false) {
  const summary = {}

  for (const { name: targetName, dir: targetDir } of targets) {
    const exists = await fs.pathExists(targetDir)
    if (!exists) {
      console.log(chalk.yellow(`  跳过 ${targetName}（目录不存在：${targetDir}）`))
      continue
    }

    const installed = []
    for (const { skillName, srcPath } of skills) {
      const destPath = path.join(targetDir, skillName)
      const destExists = await fs.pathExists(destPath)

      if (destExists && !force) {
        const ok = await confirm({ message: `${targetName}/${skillName} 已存在，覆盖？`, default: false })
        if (!ok) {
          console.log(chalk.gray(`  跳过 ${targetName}/${skillName}`))
          continue
        }
      }

      try {
        const varDefs = await loadVarDefs(srcPath)
        let varsMap = {}
        if (varDefs.length > 0) {
          console.log(chalk.cyan(`\n  配置 ${skillName}：`))
          varsMap = await resolveVars(varDefs, buildAutoVars())
        }
        await copyDir(srcPath, destPath, varsMap)
        installed.push(skillName)
      } catch (err) {
        console.log(chalk.red(`  复制失败 ${targetName}/${skillName}: ${err.message}`))
      }
    }

    if (installed.length > 0) {
      summary[targetName] = installed
    }
  }

  return summary
}
```

- [ ] **Step 2：smoke test（无 vars.json 的 skill 不受影响）**

```bash
node bin/cli.js --bundle analysis --target claude
```

期望：正常安装，不弹出任何变量提示。

- [ ] **Step 3：提交**

```bash
git add lib/installer.js
git commit -m "feat: installer supports per-skill template variable substitution"
```

---

### Task 3：为 article-fetcher 添加 `vars.json`

**Files:**
- Create: `skills/web-fetch/article-fetcher/vars.json`

- [ ] **Step 1：写文件**

```json
[
  {
    "name": "VAULT_PATH",
    "description": "Obsidian Reading 目录完整路径（例如 /Users/you/Vault/Product/Reading）",
    "default": "{{HOME}}/Vault/Product/Reading"
  },
  {
    "name": "SKILL_DIR",
    "description": "article-fetcher skill 安装后的完整路径",
    "default": "{{HOME}}/.claude/skills/article-fetcher"
  }
]
```

- [ ] **Step 2：提交**

```bash
git add skills/web-fetch/article-fetcher/vars.json
git commit -m "feat: add vars.json to article-fetcher for path configuration"
```

---

### Task 4：将 article-fetcher 文件中的硬编码路径改为占位符

以下文件中有两类硬编码路径需要替换：
- `/Users/harveyopenclaw/Vault/Product/Reading`（及子目录）→ `{{VAULT_PATH}}`
- `~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher` → `{{SKILL_DIR}}`
- `/Users/harveyopenclaw/.openclaw/skills/article-fetcher` → `{{SKILL_DIR}}`

**Files:**
- Modify: `skills/web-fetch/article-fetcher/SKILL.md`
- Modify: `skills/web-fetch/article-fetcher/references/article_utils.py`
- Modify: `skills/web-fetch/article-fetcher/scripts/init_db.py`
- Modify: `skills/web-fetch/article-fetcher/scripts/import_reading.py`

- [ ] **Step 1：更新 `SKILL.md` 路径变量声明段**

将：
```
Base:     /Users/harveyopenclaw/Vault/Product/Reading
Origin:   /Users/harveyopenclaw/Vault/Product/Reading/Origin
Article:  /Users/harveyopenclaw/Vault/Product/Reading
Image:    /Users/harveyopenclaw/Vault/Product/Reading/Image
SkillDir: ~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher
```

改为：
```
Base:     {{VAULT_PATH}}
Origin:   {{VAULT_PATH}}/Origin
Article:  {{VAULT_PATH}}
Image:    {{VAULT_PATH}}/Image
SkillDir: {{SKILL_DIR}}
```

将：
```
**数据库路径：** `~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher/scripts/url-index.db`
```
改为：
```
**数据库路径：** `{{SKILL_DIR}}/scripts/url-index.db`
```

- [ ] **Step 2：更新 `SKILL.md` 内嵌 Python 代码块中的路径**

全局替换（使用编辑器或 sed）：

| 原文 | 替换为 |
|------|--------|
| `/Users/harveyopenclaw/Vault/Product/Reading/` | `{{VAULT_PATH}}/` |
| `/Users/harveyopenclaw/Vault/Product/Reading` | `{{VAULT_PATH}}` |
| `~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher/scripts/url-index.db` | `{{SKILL_DIR}}/scripts/url-index.db` |
| `~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher` | `{{SKILL_DIR}}` |
| `/Users/harveyopenclaw/.openclaw/skills/article-fetcher/references` | `{{SKILL_DIR}}/references` |

- [ ] **Step 3：更新 `references/article_utils.py`**

将：
```python
        db_path = os.path.expanduser(
            '~/.openclaw/agents/writing-assistant/workspace/'
            'skills/article-fetcher/scripts/url-index.db'
        )
```
改为：
```python
        db_path = os.path.expanduser(
            '{{SKILL_DIR}}/scripts/url-index.db'
        )
```

- [ ] **Step 4：更新 `scripts/init_db.py`**

将：
```python
DB_PATH = os.path.expanduser(
    '~/.openclaw/agents/writing-assistant/workspace/'
    'skills/article-fetcher/scripts/url-index.db'
)
```
改为：
```python
DB_PATH = os.path.expanduser(
    '{{SKILL_DIR}}/scripts/url-index.db'
)
```

- [ ] **Step 5：更新 `scripts/import_reading.py`**

将：
```python
BASE_DIR = "/Users/harveyopenclaw/Vault/Product/Reading"
DB_PATH  = os.path.expanduser("~/.openclaw/agents/writing-assistant/workspace/skills/article-fetcher/scripts/url-index.db")
```
改为：
```python
BASE_DIR = "{{VAULT_PATH}}"
DB_PATH  = os.path.expanduser("{{SKILL_DIR}}/scripts/url-index.db")
```

- [ ] **Step 6：end-to-end 验证**

```bash
node bin/cli.js --bundle web-fetch --target claude --force
```

输入：
- `VAULT_PATH`: `/Users/harveyzhang96/Vault/Product/Reading`
- `SKILL_DIR`: `/Users/harveyzhang96/.claude/skills/article-fetcher`

验证安装结果不含硬编码的 `harveyopenclaw`：

```bash
grep -r "harveyopenclaw" ~/.claude/skills/article-fetcher/ && echo "FAIL" || echo "PASS"
```

期望输出：`PASS`

- [ ] **Step 7：提交**

```bash
git add skills/web-fetch/article-fetcher/
git commit -m "feat: replace hardcoded paths in article-fetcher with template variables"
```
