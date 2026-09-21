#!/usr/bin/env node
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.join(__dirname, '..')

const { skills: rawSkills, tools: rawTools = [], hooks: rawHooks = [] } = JSON.parse(readFileSync(path.join(root, 'skills-index.json'), 'utf8'))
const skillsDir = path.join(root, 'skills')
const toolsDir  = path.join(root, 'tools')
const hooksDir  = path.join(root, 'hooks')

// 规范化索引条目
const index = rawSkills.map(entry =>
  typeof entry === 'string' ? { path: entry, exclude: [] } : { exclude: [], ...entry }
)

// ── Skills ───────────────────────────────────────────────────────────────────
const baseFiles = ['bin/', 'lib/', 'tools/skill-harness/', 'bundles.json', 'skills-index.json', 'CHANGELOG.md']
const skillFiles = []

for (const entry of index) {
  const skillDir = path.join(skillsDir, entry.path)
  if (!existsSync(skillDir)) {
    throw new Error(`skills-index.json references skill "${entry.path}" but directory does not exist: ${skillDir}`)
  }
  const skillMd = path.join(skillDir, 'SKILL.md')
  if (!existsSync(skillMd)) {
    throw new Error(`Skill directory exists but SKILL.md not found: ${skillMd}`)
  }
  if (entry.exclude.length === 0) {
    skillFiles.push(`skills/${entry.path}/`)
  } else {
    // 展开直接子项，排除指定子目录
    const excludeSet = new Set(entry.exclude.map(e => e.replace(/\/$/, '')))
    // 警告：exclude 中列出的目录不存在（可能是历史遗留）
    for (const ex of excludeSet) {
      if (!existsSync(path.join(skillDir, ex))) {
        console.warn(`  ⚠ "${entry.path}" exclude "${ex}" does not exist — stale config?`)
      }
    }
    const items = readdirSync(skillDir, { withFileTypes: true })
    for (const item of items) {
      if (excludeSet.has(item.name)) continue
      skillFiles.push(`skills/${entry.path}/${item.name}${item.isDirectory() ? '/' : ''}`)
    }
  }
}

// ── Tools ────────────────────────────────────────────────────────────────────
const toolFiles = []

for (const tool of rawTools) {
  const subName    = tool.path ? tool.path.replace(/^tools\//, '') : tool.name
  const toolDir    = path.join(toolsDir, subName)
  const toolScript = path.join(toolDir, `${tool.name}.sh`)
  const pyProject  = path.join(toolDir, 'pyproject.toml')
  if (!existsSync(toolDir)) {
    throw new Error(`skills-index.json references tool "${tool.name}" but directory does not exist: ${toolDir}`)
  }
  if (!existsSync(toolScript) && !existsSync(pyProject)) {
    throw new Error(`Tool directory exists but entry point not found (expected ${tool.name}.sh or pyproject.toml): ${toolDir}`)
  }
  const subDir = tool.path ? tool.path.replace(/^tools\//, '') : tool.name
  toolFiles.push(`tools/${subDir}/`)
}

// ── Hooks ────────────────────────────────────────────────────────────────────
const hookFiles = []

for (const hook of rawHooks) {
  const hookDir    = path.join(root, hook.path)
  const hookScript = path.join(hookDir, `${hook.name}.sh`)
  if (!existsSync(hookDir)) {
    throw new Error(`skills-index.json references hook "${hook.name}" but directory does not exist: ${hookDir}`)
  }
  if (!existsSync(hookScript)) {
    throw new Error(`Hook directory exists but script not found: ${hookScript}`)
  }
  hookFiles.push(`${hook.path}/`)
}

// ── 更新 package.json files 字段 ─────────────────────────────────────────────
const pkgPath = path.join(root, 'package.json')
const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'))
pkg.files = [...baseFiles, ...skillFiles, ...toolFiles, ...hookFiles]
writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')

// ── 本脚本不再写 .npmignore ───────────────────────────────────────────────────
// 上面的 pkg.files 是白名单，没进 files[] 的目录本来就打不进包，所以原先那个
// "排除非索引 skill 目录" 的 block 是冗余的（实测：新建一个未索引、也不在 .npmignore
// 里的 skill 目录，npm pack --dry-run 照样不收）。
// 而它按磁盘 readdirSync 算路径，worktree 里没有主工作树那些未跟踪的在制品目录，
// 跑一次就会把它们的排除行静默删掉——不报错、退出码照样 0。本仓库要求改动都在
// worktree 里做，两条规矩撞在一起必然踩雷，因此整段去掉。

console.log(`Updated package.json files: ${pkg.files.length} entries`)
console.log(`  skills: ${skillFiles.length}, tools: ${toolFiles.length}, hooks: ${hookFiles.length}`)
