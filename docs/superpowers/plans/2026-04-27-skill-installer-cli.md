# Skill Installer CLI 实施计划

**目标：** 将本仓库发布为 npm 包，提供 `npx harveyz-skill` 命令，支持交互式 bundle 选择并安装 skill 到 Claude / Cursor / Codex。

**架构：** `bin/cli.js` 作为入口解析参数并驱动 inquirer UI；`lib/` 下三个模块分别负责 bundle 解析、target 路径映射、文件复制；`bundles.json` 定义 bundle 配置；`skills/` 目录直接打包进 npm。

**技术栈：** Node.js >=18, inquirer, chalk, fs-extra

---

### Task 1: 初始化 npm 包

**文件：**
- 创建: `package.json`
- 创建: `bundles.json`
- 创建: `.npmignore`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "harveyz-skill",
  "version": "1.0.0",
  "description": "One-click skill installer for Claude Code, Cursor, and Codex",
  "bin": {
    "harveyz-skill": "./bin/cli.js"
  },
  "files": [
    "bin/",
    "lib/",
    "skills/",
    "bundles.json"
  ],
  "engines": {
    "node": ">=18"
  },
  "dependencies": {
    "chalk": "^5.3.0",
    "fs-extra": "^11.2.0",
    "inquirer": "^9.2.0"
  },
  "license": "MIT"
}
```

- [ ] **Step 2: 创建 bundles.json**

```json
[
  {
    "name": "brainstorming",
    "description": "设计与规划工具（brainstorming + writing-plans）",
    "skills": [
      "superpowers-fork/brainstorming",
      "superpowers-fork/writing-plans"
    ]
  },
  {
    "name": "dev",
    "description": "开发工作流（executing-plans + systematic-debugging + using-git-worktrees）",
    "skills": [
      "superpowers-fork/executing-plans",
      "superpowers-fork/systematic-debugging",
      "superpowers-fork/using-git-worktrees"
    ]
  },
  {
    "name": "all",
    "description": "全部 skill",
    "skills": [
      "superpowers-fork/brainstorming",
      "superpowers-fork/writing-plans",
      "superpowers-fork/executing-plans",
      "superpowers-fork/systematic-debugging",
      "superpowers-fork/using-git-worktrees"
    ]
  }
]
```

- [ ] **Step 3: 创建 .npmignore**

```
docs/
scripts/
.worktrees/
.claude/
evals/
*.sh
CLAUDE.md
```

- [ ] **Step 4: 安装依赖**

```bash
npm install
```

预期：生成 `node_modules/` 和 `package-lock.json`，无报错。

- [ ] **Step 5: 提交**

```bash
git add package.json bundles.json .npmignore package-lock.json
git commit -m "feat: init npm package for skill installer"
```

---

### Task 2: 实现 lib/targets.js（target 路径映射）

**文件：**
- 创建: `lib/targets.js`

- [ ] **Step 1: 编写 targets.js**

```js
import os from 'os'
import path from 'path'

export const TARGETS = {
  claude: path.join(os.homedir(), '.claude', 'skills'),
  cursor: path.join(os.homedir(), '.cursor', 'skills'),
  codex: path.join(os.homedir(), '.codex', 'skills'),
}

export const TARGET_CHOICES = Object.entries(TARGETS).map(([name, dir]) => ({
  name: `${name.padEnd(8)} (${dir})`,
  value: name,
}))

// 返回选中 targets 的 { name, dir } 列表，all 展开为全部
export function resolveTargets(selected) {
  if (selected.includes('all')) return Object.entries(TARGETS).map(([name, dir]) => ({ name, dir }))
  return selected.map(name => ({ name, dir: TARGETS[name] }))
}
```

- [ ] **Step 2: 验证模块可加载**

```bash
node -e "import('./lib/targets.js').then(m => console.log(m.TARGETS))"
```

预期：打印三个路径，无报错。

- [ ] **Step 3: 提交**

```bash
git add lib/targets.js
git commit -m "feat: add target path resolver"
```

---

### Task 3: 实现 lib/bundles.js（bundle 解析）

**文件：**
- 创建: `lib/bundles.js`

- [ ] **Step 1: 编写 bundles.js**

```js
import { createRequire } from 'module'
import path from 'path'
import { fileURLToPath } from 'url'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const bundleDefs = require('../bundles.json')
const skillsRoot = path.join(__dirname, '..', 'skills')

export const BUNDLE_CHOICES = bundleDefs.map(b => ({
  name: `${b.name.padEnd(16)} — ${b.description}`,
  value: b.name,
}))

// 返回选中 bundles 对应的去重 skill 路径列表 { skillName, srcPath }
export function resolveSkills(selectedBundles) {
  const seen = new Set()
  const result = []
  for (const name of selectedBundles) {
    const def = bundleDefs.find(b => b.name === name)
    if (!def) continue
    for (const rel of def.skills) {
      if (seen.has(rel)) continue
      seen.add(rel)
      const skillName = rel.split('/').pop()
      result.push({ skillName, srcPath: path.join(skillsRoot, rel) })
    }
  }
  return result
}
```

- [ ] **Step 2: 验证解析结果**

```bash
node -e "import('./lib/bundles.js').then(m => console.log(m.resolveSkills(['brainstorming'])))"
```

预期：打印包含 `skillName` 和 `srcPath` 的数组，无报错。

- [ ] **Step 3: 提交**

```bash
git add lib/bundles.js
git commit -m "feat: add bundle resolver"
```

---

### Task 4: 实现 lib/installer.js（文件复制 & 冲突处理）

**文件：**
- 创建: `lib/installer.js`

- [ ] **Step 1: 编写 installer.js**

```js
import fs from 'fs-extra'
import path from 'path'
import { confirm } from '@inquirer/prompts'
import chalk from 'chalk'

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

      await fs.copy(srcPath, destPath, { overwrite: true })
      installed.push(skillName)
    }

    if (installed.length > 0) {
      summary[targetName] = installed
    }
  }

  return summary
}
```

- [ ] **Step 2: 验证模块可加载**

```bash
node -e "import('./lib/installer.js').then(() => console.log('ok'))"
```

预期：打印 `ok`，无报错。

- [ ] **Step 3: 提交**

```bash
git add lib/installer.js
git commit -m "feat: add skill file installer with conflict handling"
```

---

### Task 5: 实现 bin/cli.js（入口 & 交互 UI）

**文件：**
- 创建: `bin/cli.js`

- [ ] **Step 1: 创建 bin/ 目录并编写 cli.js**

```js
#!/usr/bin/env node
import { checkbox } from '@inquirer/prompts'
import chalk from 'chalk'
import { BUNDLE_CHOICES, resolveSkills } from '../lib/bundles.js'
import { TARGET_CHOICES, resolveTargets, TARGETS } from '../lib/targets.js'
import { installSkills } from '../lib/installer.js'

const args = process.argv.slice(2)
const forceFlag = args.includes('--force')
const bundleArg = args[args.indexOf('--bundle') + 1]
const targetArg = args[args.indexOf('--target') + 1]

// list 子命令
if (args[0] === 'list') {
  const { createRequire } = await import('module')
  const { fileURLToPath } = await import('url')
  const path = await import('path')
  const require = createRequire(import.meta.url)
  const bundles = require('../bundles.json')
  for (const b of bundles) {
    console.log(chalk.bold(b.name) + ' — ' + b.description)
    for (const s of b.skills) console.log('  ' + s)
  }
  process.exit(0)
}

// 解析 bundle 选择
let selectedBundles
if (bundleArg) {
  selectedBundles = [bundleArg]
} else {
  selectedBundles = await checkbox({
    message: '选择要安装的 bundle（空格多选）:',
    choices: BUNDLE_CHOICES,
  })
}

if (!selectedBundles.length) {
  console.log(chalk.red('未选择任何 bundle，退出。'))
  process.exit(1)
}

// 解析 target 选择
let selectedTargets
if (targetArg) {
  selectedTargets = targetArg === 'all' ? Object.keys(TARGETS) : [targetArg]
} else {
  selectedTargets = await checkbox({
    message: '安装到哪些工具（空格多选）:',
    choices: [
      ...TARGET_CHOICES,
      { name: 'all      — 全部工具', value: 'all' },
    ],
  })
}

if (!selectedTargets.length) {
  console.log(chalk.red('未选择任何目标工具，退出。'))
  process.exit(1)
}

const skills = resolveSkills(selectedBundles)
const targets = resolveTargets(selectedTargets)

console.log('')
const summary = await installSkills(skills, targets, forceFlag)

console.log('')
console.log(chalk.green('✔ 安装完成：'))
for (const [target, names] of Object.entries(summary)) {
  console.log(`  ${chalk.bold(target)} ← ${names.join(', ')}`)
}
```

- [ ] **Step 2: 添加执行权限**

```bash
chmod +x bin/cli.js
```

- [ ] **Step 3: 本地验证 list 命令**

```bash
node bin/cli.js list
```

预期：打印所有 bundle 名称和 skill 列表，无报错。

- [ ] **Step 4: 本地验证无交互模式**

```bash
node bin/cli.js --bundle brainstorming --target claude
```

预期：将 `brainstorming`、`writing-plans` 复制到 `~/.claude/skills/`，打印安装摘要。

- [ ] **Step 5: 本地验证交互模式**

```bash
node bin/cli.js
```

预期：展示 bundle checkbox → target checkbox → 复制文件 → 打印摘要。

- [ ] **Step 6: 提交**

```bash
git add bin/cli.js
git commit -m "feat: add CLI entry with interactive and non-interactive modes"
```

---

### Task 6: 发布到 npm

**文件：**
- 无新文件

- [ ] **Step 1: 确认 npm 登录状态**

```bash
npm whoami
```

预期：打印你的 npm 用户名。若未登录，运行 `npm login`。

- [ ] **Step 2: 干跑确认打包内容**

```bash
npm pack --dry-run
```

预期：列出 `bin/`、`lib/`、`skills/`、`bundles.json`，不包含 `docs/`、`.worktrees/` 等。

- [ ] **Step 3: 发布**

```bash
npm publish
```

预期：无报错，npm registry 上出现 `harveyz-skill` 包。

- [ ] **Step 4: 验证 npx 可用**

```bash
npx harveyz-skill list
```

预期：从 npm 拉取并打印 bundle 列表，无报错。
