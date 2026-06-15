import fs from 'fs'
import os from 'os'
import { createRequire } from 'module'
import path from 'path'
import { fileURLToPath } from 'url'
import { SKILL_TARGETS, USER_ONLY_TARGETS, userSkillDir } from './targets.js'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const { bundleMeta, skills: skillDefs, toolBundleMeta = {}, tools: toolDefs = [], hooks: hookDefs = [] } = require('../skills-index.json')
const repoRoot = path.join(__dirname, '..')
const skillsRoot = path.join(repoRoot, 'skills')

// 从 SKILL.md frontmatter 读取 version 字段
function readVersion(skillPath) {
  try {
    const content = fs.readFileSync(path.join(skillPath, 'SKILL.md'), 'utf8')
    const m = content.match(/^---[\s\S]*?^version:\s*["']?([^"'\n]+)["']?/m)
    return m ? m[1].trim() : '—'
  } catch {
    return '—'
  }
}

// 格式化 checkbox 展示名：左对齐 skill 名，右侧对齐版本号
function formatChoice(name, version, nameWidth) {
  const padded = name.padEnd(nameWidth)
  return `${padded}  ${version}`
}

// ── Skills ──────────────────────────────────────────────────────────────────
const bundleSkills = {}
for (const skill of skillDefs) {
  if (!bundleSkills[skill.bundle]) bundleSkills[skill.bundle] = []
  bundleSkills[skill.bundle].push(skill)
}

const namedBundles = Object.keys(bundleSkills)

export const BUNDLE_CHOICES = [
  ...namedBundles.map(name => ({
    name: `${name.padEnd(16)} — ${bundleMeta[name] ?? name}`,
    value: name,
  })),
  { name: `${'all'.padEnd(16)} — 全部 skill`, value: 'all' },
]

export function resolveSkillsByName(names) {
  return names.map(name => {
    const skill = skillDefs.find(s => s.path.split('/').pop() === name)
    if (!skill) throw new Error(`Unknown skill: "${name}"`)
    const srcPath = path.join(skillsRoot, skill.path)
    return { skillName: name, srcPath, version: readVersion(srcPath) }
  })
}

export function resolveSkills(selectedBundles) {
  const expanded = selectedBundles.includes('all') ? namedBundles : selectedBundles

  const seen = new Set()
  const result = []
  for (const bundleName of expanded) {
    const skills = bundleSkills[bundleName]
    if (!skills) throw new Error(`Unknown bundle: "${bundleName}"`)
    for (const skill of skills) {
      if (seen.has(skill.path)) continue
      seen.add(skill.path)
      const skillName = skill.path.split('/').pop()
      const srcPath   = path.join(skillsRoot, skill.path)
      result.push({ skillName, srcPath, version: readVersion(srcPath) })
    }
  }
  return result
}

// 单个 skill 粒度的选项列表（用于交互式选择）
// 每个值是 { kind:'skill', skillName, srcPath } 或特殊字符串 'all'
export function buildAllChoices() {
  const choices = []

  // 预计算所有 skill 名的最大长度，统一对齐
  const allSkillNames = skillDefs.map(s => s.path.split('/').pop())
  const allToolNames  = toolDefs.map(t => t.name)
  const nameWidth = Math.max(...[...allSkillNames, ...allToolNames].map(n => n.length))

  // ── skill ── 分组
  for (const [bundleName, skills] of Object.entries(bundleSkills)) {
    choices.push({ type: 'separator', separator: `── ${bundleName} ──` })
    for (const skill of skills) {
      const skillName = skill.path.split('/').pop()
      const srcPath   = path.join(skillsRoot, skill.path)
      const version   = readVersion(srcPath)
      choices.push({
        name:  formatChoice(skillName, version, nameWidth),
        value: { kind: 'skill', skillName, srcPath },
      })
    }
  }

  return choices
}

// 所有 skill 展开为 { kind:'skill', skillName, bundle, srcPath } 列表（对应 all 选项）
export function getAllSkillItems() {
  return skillDefs.map(skill => {
    const srcPath = path.join(skillsRoot, skill.path)
    return {
      kind: 'skill',
      skillName: skill.path.split('/').pop(),
      bundle: skill.bundle,
      global: skill.global ?? false,
      srcPath,
      version: readVersion(srcPath),
    }
  })
}

// 所有 tool 展开为 { kind:'tool', toolName, srcPath, version } 列表
export function getAllToolItems() {
  return toolDefs.map(tool => {
    const srcPath = path.join(repoRoot, 'tools', tool.name)
    return {
      kind: 'tool',
      toolName: tool.name,
      srcPath,
      version: readToolMeta(path.join(srcPath, 'tool.json')),
    }
  })
}

// 检查某个 skill 在 user/project 级别每个工具的安装状态
// 返回 { user: { claude, cursor, codex }, project: { claude, cursor, codex } }
// 每个工具: { version: string, status: 'up-to-date'|'update'|'none' }
export function checkInstalled(skillName, availableVersion) {
  const home = os.homedir()
  const targets = SKILL_TARGETS

  function checkScope(dirFn) {
    const result = {}
    for (const t of targets) {
      const dir = dirFn(t)
      if (dir === null) { result[t] = { version: '—', status: 'none' }; continue }
      const skillPath = path.join(dir, skillName)
      const version = readVersion(skillPath)
      const status = version === '—' ? 'none'
        : version === availableVersion ? 'up-to-date'
        : 'update'
      result[t] = { version, status }
    }
    return result
  }

  const cwd = process.cwd()
  const noneScope = Object.fromEntries(targets.map(t => [t, { version: '—', status: 'none' }]))

  return {
    user:    checkScope(t => userSkillDir(t)),
    project: cwd === home ? noneScope : checkScope(t =>
      USER_ONLY_TARGETS.has(t) ? null : path.join(cwd, `.${t}`, 'skills')
    ),
  }
}

// 将 scope detail 聚合为单一摘要状态
export function scopeSummary(scopeDetail) {
  const statuses = Object.values(scopeDetail).map(t => t.status)
  if (statuses.some(s => s === 'update'))     return 'update'
  if (statuses.some(s => s === 'up-to-date')) return 'up-to-date'
  return 'none'
}

// ── Hooks ────────────────────────────────────────────────────────────────────

function readHookVersion(scriptPath) {
  try {
    const content = fs.readFileSync(scriptPath, 'utf-8')
    const m = content.match(/^#\s*version:\s*(.+)$/m)
    return m ? m[1].trim() : '—'
  } catch { return '—' }
}

export function getAllHookItems() {
  return hookDefs.map(hook => {
    const srcPath = path.join(repoRoot, hook.path, `${hook.name}.sh`)
    return {
      ...hook,
      srcPath,
      version: readHookVersion(srcPath),
    }
  })
}

export function checkHookInstalled(hookName) {
  const home = os.homedir()
  const cwd  = process.cwd()

  function checkClaudeScope(hooksDir, settingsPath) {
    const scriptPath       = path.join(hooksDir, `${hookName}.sh`)
    const scriptExists     = fs.existsSync(scriptPath)
    const installedVersion = scriptExists ? readHookVersion(scriptPath) : '—'
    let registered = false
    try {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'))
      registered = Object.values(settings.hooks ?? {}).some(entries =>
        Array.isArray(entries) && entries.some(e =>
          Array.isArray(e.hooks) && e.hooks.some(h =>
            typeof h.command === 'string' && h.command.includes(`${hookName}.sh`)
          )
        )
      )
    } catch { /* settings.json 不存在或解析失败 */ }
    const status = scriptExists && registered ? 'installed'
                 : scriptExists || registered ? 'partial'
                 : 'none'
    return { status, version: installedVersion }
  }

  function checkCodexScope(hooksDir, hooksJsonPath) {
    const scriptPath       = path.join(hooksDir, `${hookName}.sh`)
    const scriptExists     = fs.existsSync(scriptPath)
    const installedVersion = scriptExists ? readHookVersion(scriptPath) : '—'
    let registered = false
    try {
      const data = JSON.parse(fs.readFileSync(hooksJsonPath, 'utf-8'))
      registered = Object.values(data.hooks ?? {}).some(entries =>
        Array.isArray(entries) && entries.some(e =>
          Array.isArray(e.hooks) && e.hooks.some(h =>
            typeof h.command === 'string' && h.command.includes(`${hookName}.sh`)
          )
        )
      )
    } catch { /* hooks.json 不存在或解析失败 */ }
    const status = scriptExists && registered ? 'installed'
                 : scriptExists || registered ? 'partial'
                 : 'none'
    return { status, version: installedVersion }
  }

  const userClaudeHooks    = path.join(home, '.claude', 'hooks')
  const userClaudeSettings = path.join(home, '.claude', 'settings.json')
  const projClaudeHooks    = path.join(cwd,  '.claude', 'hooks')
  const projClaudeSettings = path.join(cwd,  '.claude', 'settings.json')

  const userCodexHooks     = path.join(home, '.codex', 'hooks')
  const userCodexHooksJson = path.join(home, '.codex', 'hooks.json')
  const projCodexHooks     = path.join(cwd,  '.codex', 'hooks')
  const projCodexHooksJson = path.join(cwd,  '.codex', 'hooks.json')

  const claudeUser    = checkClaudeScope(userClaudeHooks, userClaudeSettings)
  const claudeProject = cwd === home ? { status: 'none', version: '—' } : checkClaudeScope(projClaudeHooks, projClaudeSettings)
  const codexUser     = checkCodexScope(userCodexHooks, userCodexHooksJson)
  const codexProject  = cwd === home ? { status: 'none', version: '—' } : checkCodexScope(projCodexHooks, projCodexHooksJson)

  return {
    // Legacy flat fields (backward compat — used by hooks list text output)
    user:    claudeUser,
    project: claudeProject,
    // Per-target
    claude: { user: claudeUser, project: claudeProject },
    codex:  { user: codexUser,  project: codexProject  },
  }
}

export { formatChoice, readVersion, readHookVersion }

const HSKILL_TOOLS_DATA = path.join(os.homedir(), '.hskill', 'tools')

function readToolMeta(jsonPath) {
  try {
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))
    return data.version ?? '—'
  } catch { return '—' }
}

// 检测工具安装状态：binary 存在于 ~/.local/bin，版本从安装时写入的 data JSON 读取
export function checkToolInstalled(toolName, srcPath) {
  const installedBin  = path.join(os.homedir(), '.local', 'bin', toolName)
  const installedMeta = path.join(HSKILL_TOOLS_DATA, `${toolName}.json`)
  try {
    if (!fs.existsSync(installedBin)) return { version: '—', status: 'none' }
    const installedVersion = readToolMeta(installedMeta)
    const sourceVersion    = readToolMeta(path.join(srcPath, 'tool.json'))
    const status = installedVersion === '—' || sourceVersion === '—' || installedVersion === sourceVersion
      ? 'up-to-date' : 'update'
    return { version: installedVersion, status }
  } catch { return { version: '—', status: 'none' } }
}

// ── Tools ────────────────────────────────────────────────────────────────────
const bundleTools = {}
for (const tool of toolDefs) {
  if (!bundleTools[tool.bundle]) bundleTools[tool.bundle] = []
  bundleTools[tool.bundle].push(tool)
}

const namedToolBundles = Object.keys(bundleTools)

export const TOOL_BUNDLE_CHOICES = namedToolBundles.map(name => ({
  name: `${name.padEnd(16)} — ${toolBundleMeta[name] ?? name}`,
  value: name,
}))

export function resolveToolsByName(names) {
  return names.map(name => {
    const tool = toolDefs.find(t => t.name === name)
    if (!tool) throw new Error(`Unknown tool: "${name}"`)
    return { toolName: tool.name, srcPath: path.join(repoRoot, 'tools', tool.name) }
  })
}

export function resolveTools(selectedBundles) {
  const expanded = selectedBundles.includes('all') ? namedToolBundles : selectedBundles

  const seen = new Set()
  const result = []
  for (const bundleName of expanded) {
    const tools = bundleTools[bundleName]
    if (!tools) throw new Error(`Unknown tool bundle: "${bundleName}"`)
    for (const tool of tools) {
      if (seen.has(tool.name)) continue
      seen.add(tool.name)
      result.push({ toolName: tool.name, srcPath: path.join(repoRoot, 'tools', tool.name) })
    }
  }
  return result
}
