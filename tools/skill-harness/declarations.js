import fs from 'fs-extra'
import path from 'node:path'
import { PHASE1_PLATFORMS } from './select.js'

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
    // 带下标迭代：同一个 eval 里两条断言都是裸字符串，或者都缺 id，产出的
    // 错误消息如果只写 eval id 会长得一模一样——在几十条断言的大文件里，
    // 看到这条错误也定位不到是第几条。下标从 0 开始就行，这是给人看的
    // 定位线索，不是面向用户的文案。
    ev.assertions?.forEach((a, i) => {
      if (typeof a === 'string') {
        errors.push(`eval ${ev.id} assertion #${i}: 仍是裸字符串，缺稳定 id`)
        return
      }
      if (!a.id) errors.push(`eval ${ev.id} assertion #${i}: 缺 id`)
      else if (seen.has(a.id)) errors.push(`eval ${ev.id}: assertion id 重复 "${a.id}"`)
      else seen.add(a.id)
      if (a.source && !SOURCE_LEVELS.includes(a.source)) {
        errors.push(`eval ${ev.id}/${a.id}: 未知 source "${a.source}"`)
      }
      if (a.na_platforms !== undefined) {
        if (!Array.isArray(a.na_platforms)) {
          errors.push(`eval ${ev.id}/${a.id ?? '#' + i}: na_platforms 必须是数组`)
        } else {
          for (const p of a.na_platforms) {
            if (!PHASE1_PLATFORMS.includes(p)) {
              errors.push(`eval ${ev.id}/${a.id ?? '#' + i}: na_platforms 含未知平台 "${p}"`)
            }
          }
        }
      }
    })
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
