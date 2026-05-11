import { createRequire } from 'module'
import path from 'path'
import { fileURLToPath } from 'url'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const { bundleMeta, skills: skillDefs, toolBundleMeta = {}, tools: toolDefs = [] } = require('../skills-index.json')
const repoRoot = path.join(__dirname, '..')
const skillsRoot = path.join(repoRoot, 'skills')

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
    return { skillName: name, srcPath: path.join(skillsRoot, skill.path) }
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
      result.push({ skillName, srcPath: path.join(skillsRoot, skill.path) })
    }
  }
  return result
}

// 单个 skill 粒度的选项列表（用于交互式选择）
// 每个值是 { kind:'skill', skillName, srcPath } 或特殊字符串 'all'
export function buildAllChoices() {
  const choices = []

  // ── skill ── 分组
  for (const [bundleName, skills] of Object.entries(bundleSkills)) {
    choices.push({ type: 'separator', separator: `── ${bundleName} ──` })
    for (const skill of skills) {
      const skillName = skill.path.split('/').pop()
      choices.push({
        name: skillName,
        value: { kind: 'skill', skillName, srcPath: path.join(skillsRoot, skill.path) },
      })
    }
  }

  return choices
}

// 所有 skill 展开为 { kind:'skill', skillName, srcPath } 列表（对应 all 选项）
export function getAllSkillItems() {
  return skillDefs.map(skill => ({
    kind: 'skill',
    skillName: skill.path.split('/').pop(),
    srcPath: path.join(skillsRoot, skill.path),
  }))
}

// 所有 tool 展开为 { kind:'tool', toolName, srcPath } 列表
export function getAllToolItems() {
  return toolDefs.map(tool => ({
    kind: 'tool',
    toolName: tool.name,
    srcPath: path.join(repoRoot, 'tools', tool.name),
  }))
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
