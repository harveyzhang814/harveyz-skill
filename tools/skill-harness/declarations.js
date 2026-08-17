import fs from 'fs-extra'
import path from 'node:path'

// 顺序即层级，不是集合：artifact 含 reply，transcript 含前两者。
// 这样「同时需要回复与产出物」的断言不必拆成两条，也不必把字段做成数组。
export const SOURCE_LEVELS = ['reply', 'artifact', 'transcript']

export function sourceIncludes(declared, needed) {
  return SOURCE_LEVELS.indexOf(declared) >= SOURCE_LEVELS.indexOf(needed)
}

export function maxSourceLevel(assertions) {
  let max = 'reply'
  for (const a of assertions ?? []) {
    const lv = a.source ?? 'reply'
    if (SOURCE_LEVELS.indexOf(lv) > SOURCE_LEVELS.indexOf(max)) max = lv
  }
  return max
}

export function isFrozen(evalDef) {
  return Boolean(evalDef?.frozen)
}

// 返回错误消息数组而非抛出：一次列全所有问题，迁移时能一遍改完。
export function validateDeclaration(doc, skillPath) {
  const errors = []
  const expected = path.basename(skillPath)
  if (doc?.skill_name !== expected) {
    errors.push(`skill_name "${doc?.skill_name}" 与目录名 "${expected}" 不符`)
  }
  for (const ev of doc?.evals ?? []) {
    const seen = new Set()
    for (const a of ev.assertions ?? []) {
      if (typeof a === 'string') {
        errors.push(`eval ${ev.id}: assertion 仍是裸字符串，缺稳定 id`)
        continue
      }
      if (!a.id) errors.push(`eval ${ev.id}: assertion 缺 id`)
      else if (seen.has(a.id)) errors.push(`eval ${ev.id}: assertion id 重复 "${a.id}"`)
      else seen.add(a.id)
      if (a.source && !SOURCE_LEVELS.includes(a.source)) {
        errors.push(`eval ${ev.id}/${a.id}: 未知 source "${a.source}"`)
      }
    }
  }
  return errors
}

export async function loadDeclaration(repoRoot, skill) {
  const file = path.join(repoRoot, 'skills', skill, 'evals/evals.json')
  if (!await fs.pathExists(file)) return null
  const doc = await fs.readJson(file)
  const errors = validateDeclaration(doc, skill)
  if (errors.length) {
    throw new Error(`${skill} 的 evals.json 格式不合法：\n  ${errors.join('\n  ')}`)
  }
  return doc
}
