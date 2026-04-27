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
  // 展开 dynamic bundle（all）为所有非 dynamic bundle 的 union
  const expanded = selectedBundles.flatMap(name => {
    const def = bundleDefs.find(b => b.name === name)
    if (!def) throw new Error(`Unknown bundle: "${name}"`)
    if (def.dynamic) return bundleDefs.filter(b => !b.dynamic).map(b => b.name)
    return name
  })

  const seen = new Set()
  const result = []
  for (const name of expanded) {
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
