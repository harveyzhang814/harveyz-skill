import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')

/** 读取 skill 的 SKILL.md 正文；path 是相对仓库根的路径。 */
export const readSkill = path => readFile(resolve(root, path), 'utf8')

/** 与 skills-index.json 的 contentHash 算法一致：version 行置换为占位符后取 sha256 前 16 位。 */
export const contentHash = body =>
  createHash('sha256').update(body.replace(/^version:.*$/m, 'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0, 16)

/** 按 skills-index.json 的 path（如 agent-canvas/relate-node）取 { contentHash, contentVersion }。 */
export async function indexEntry(path) {
  const index = JSON.parse(await readFile(resolve(root, 'skills-index.json'), 'utf8'))
  const entry = index.skills.find(s => s.path === path)
  if (!entry) throw new Error(`skills-index.json 中没有 ${path}`)
  return { contentHash: entry.contentHash, contentVersion: entry.contentVersion }
}
