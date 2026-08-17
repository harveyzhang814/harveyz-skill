import fs from 'fs-extra'
import path from 'node:path'

// 4 MB。超限截断而非丢弃：一份被截断且标明截断的原料，仍比没有原料有用。
export const TRANSCRIPT_LIMIT = 4 * 1024 * 1024

// harness 自己往 jail 里写的文件。它们在 spawn 之前就被创建、运行期间被写入，
// 必然出现在差集里——不排除就会被当成 agent 的产出物。
export const HARNESS_FILES = new Set([
  'stdout.log', 'stderr.log',
  'hermes-list-stdout.log', 'hermes-list-stderr.log',
  'hermes-export-stdout.log', 'hermes-export-stderr.log',
])

// 签名带 mtime 与 size 两项：只比 size 会漏掉「改写成等长内容」，
// 只比 mtime 会被时钟精度坑到。
export async function snapshot(dir) {
  const out = new Map()

  // 根目录 readdir 失败必须抛错——空 snapshot 会让所有已存在文件看起来像 agent 产出物
  const rootEntries = await fs.readdir(dir, { withFileTypes: true })

  async function walk(cur, entries) {
    for (const e of entries) {
      const full = path.join(cur, e.name)
      if (e.isDirectory()) {
        // 递归遍历子目录，仅容忍运行期间删除的竞态
        try {
          const subEntries = await fs.readdir(full, { withFileTypes: true })
          await walk(full, subEntries)
        } catch (err) {
          if (err.code === 'ENOENT') {
            // 子目录在列举与遍历之间被删掉——竞态可容忍
            continue
          }
          throw err
        }
      } else if (e.isFile()) {
        // 对单个文件 stat，仅容忍运行期间删除的竞态
        try {
          const st = await fs.stat(full)
          out.set(path.relative(dir, full), `${st.mtimeMs}:${st.size}`)
        } catch (err) {
          if (err.code === 'ENOENT') {
            // 文件在遍历期间被删掉——竞态可容忍
            continue
          }
          throw err
        }
      }
    }
  }

  await walk(dir, rootEntries)
  return out
}

export function diffSnapshots(before, after) {
  const changed = []
  for (const [rel, sig] of after) {
    if (HARNESS_FILES.has(rel)) continue
    if (before.get(rel) !== sig) changed.push(rel)
  }
  return changed.sort()
}

export function capTranscript(raw, limit = TRANSCRIPT_LIMIT) {
  if (typeof raw !== 'string') return { text: '', truncated: false }
  if (raw.length <= limit) return { text: raw, truncated: false }
  return { text: raw.slice(0, limit), truncated: true }
}

export function cellDirName({ skill, platform, mode, repeat }) {
  return `${String(skill).replace(/\//g, '-')}__${platform}__${mode}__r${repeat ?? 0}`
}
