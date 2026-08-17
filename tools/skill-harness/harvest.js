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
  'usage.json',
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

// 各平台把自己的配置/会话状态目录钉在 jail 内的哪个前缀——诊断自一次真实
// 采集：claude 靠 CLAUDE_CONFIG_DIR 把状态放进 .claude/（见 adapters/claude.js
// jailEnv），hermes 靠 HOME 重定向叠加 seedJail/install 把状态放进 .hermes/
// （见 adapters/hermes.js），pi 不重定向 HOME，但把会话目录钉在
// --session-dir 指向的 sessions/（见 adapters/pi.js args()）。这些目录下的
// 文件由平台自己在运行期间写出，必然出现在 before/after 差集里——不排除
// 就会被当成 skill 的产出物喂给 grader，浪费评分的 token 还污染判断。
// 前缀匹配而非精确文件名：真实采集到的路径里带时间戳/多变的会话 id
// （如 backups/....backup.1786959592650、projects/<jail-path>/<uuid>.jsonl），
// 固定列表枚举不完。
// 只排除平台自己的状态目录，不是整个 HOME——skill 写到 $HOME/.hskill/ 和
// ~/Documents/notes/ 这些路径必须原样留在差集里，那才是我们要采集的东西。
export const PLATFORM_STATE_PREFIXES = {
  claude: ['.claude/'],
  hermes: ['.hermes/'],
  pi: ['sessions/'],
}

export function diffSnapshots(before, after, platform) {
  const statePrefixes = PLATFORM_STATE_PREFIXES[platform] ?? []
  const changed = []
  for (const [rel, sig] of after) {
    if (HARNESS_FILES.has(rel)) continue
    if (statePrefixes.some(prefix => rel.startsWith(prefix))) continue
    if (before.get(rel) !== sig) changed.push(rel)
  }
  return changed.sort()
}

export function capTranscript(raw, limit = TRANSCRIPT_LIMIT) {
  if (typeof raw !== 'string') return { text: '', truncated: false }
  if (raw.length <= limit) return { text: raw, truncated: false }
  return { text: raw.slice(0, limit), truncated: true }
}

// evalId 缺省（null/undefined）时不加段——与旧目录名保持字节级兼容（探针、
// 无声明 skill）。带 evalId 时必须加段：同一个 skill 在同一 platform/mode
// 下的两个 eval 场景若共享目录名，第二个的 transcript/artifacts 会直接覆盖
// 第一个已落盘的证据，这是本任务要修的缺陷本身在磁盘上的翻版。
export function cellDirName({ skill, platform, mode, repeat, evalId }) {
  const evalPart = evalId === undefined || evalId === null ? '' : `__eval${evalId}`
  return `${String(skill).replace(/\//g, '-')}__${platform}__${mode}${evalPart}__r${repeat ?? 0}`
}

// 每个错误单独 catch 并收集，不中断后续采集：
// 少捞到一个文件，剩下的仍有价值；抛出去则整格白跑。
export async function harvestCell({ jailDir, destDir, raw, changedFiles }) {
  const errors = []
  await fs.ensureDir(destDir)

  const { text, truncated } = capTranscript(raw)
  try {
    await fs.writeFile(path.join(destDir, 'transcript.jsonl'), text)
  } catch (e) {
    errors.push(`transcript: ${e.message}`)
  }

  for (const rel of changedFiles ?? []) {
    try {
      await fs.copy(path.join(jailDir, rel), path.join(destDir, 'artifacts', rel))
    } catch (e) {
      errors.push(`artifact ${rel}: ${e.message}`)
    }
  }

  return { truncated, errors }
}

// snapshot 阶段的错误排在前，harvestCell 自身的 errors 紧随其后——两边都要保留，
// 谁都不能覆盖谁。result 缺失代表 harvestCell 自己抛出了（比如 destDir 建不出来），
// 这种情况下没有 truncated 可言，falls back to false，errors 用调用方传入的
// fallbackError 顶替 result.errors。
export function mergeHarvest(snapshotErrors, result, fallbackError) {
  if (result) {
    return { truncated: result.truncated, errors: [...snapshotErrors, ...result.errors] }
  }
  return { truncated: false, errors: [...snapshotErrors, fallbackError] }
}
