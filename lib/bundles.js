import { createRequire } from 'module'
import path from 'path'
import { fileURLToPath } from 'url'

const require = createRequire(import.meta.url)
const __dirname = path.dirname(fileURLToPath(import.meta.url))

const { bundleMeta, skills: skillDefs } = require('../skills-index.json')
const skillsRoot = path.join(__dirname, '..', 'skills')

// Group skills by bundle
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
