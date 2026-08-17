import fs from 'fs-extra'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { cellDirName } from '../harvest.js'
import { maxSourceLevel } from '../declarations.js'
import { buildGradePrompt } from './prompt.js'
import { parseGraderOutput } from './parse.js'
import { createJail } from '../jail.js'
import { claudeAdapter } from '../adapters/claude.js'
import { PROFILES } from '../profiles.js'

const PROFILE_BY_ID = new Map(PROFILES.map(p => [p.id, p]))

// 只评「上游 pass 且有声明」的格子。上游没跑通时没有可判的东西——
// 那是装不上，不是做得差，混为一谈会把安装失败伪装成质量问题。
//
// 一条 record 只产出一份 grading——按 record.evalId 从声明里找回它当时是为
// 哪个 eval 场景跑的，只判那一个。过去这里是 `for (const evalDef of
// decl.evals ?? [])`，不看 record 到底是为哪个场景跑的，把声明里全部 eval
// 的断言都扣到同一次运行上；这正是本任务要修的缺陷——run 阶段过去没有 eval
// 轴，一次 `run skill` 通用任务的结果被拿去回答四个不同场景的断言。
// evalId 在声明里找不到（比如声明后来把这个 eval 删了，或者 record 压根
// 没有 evalId——无声明 skill 的格子）就跳过，不瞎判。
export function selectGradeCells({ records, declarations, only }) {
  const out = []
  for (const rec of records) {
    if (only?.length && !only.includes(rec.skill)) continue
    if (rec.exitCode !== 0) continue
    if (rec.reply === null || rec.reply === undefined) continue
    const decl = declarations.get(rec.skill)
    if (!decl) continue
    const evalDef = (decl.evals ?? []).find(e => e.id === rec.evalId)
    if (!evalDef) continue
    out.push({
      skill: rec.skill, platform: rec.platform, mode: rec.mode,
      repeat: rec.repeat ?? 0, evalId: rec.evalId, evalDef, reply: rec.reply, task: rec.task,
    })
  }
  return out
}

async function readArtifacts(dir) {
  const root = path.join(dir, 'artifacts')
  if (!await fs.pathExists(root)) return []
  const out = []
  async function walk(cur) {
    for (const e of await fs.readdir(cur, { withFileTypes: true })) {
      const full = path.join(cur, e.name)
      if (e.isDirectory()) await walk(full)
      else if (e.isFile()) {
        out.push({ path: path.relative(root, full), content: await fs.readFile(full, 'utf8') })
      }
    }
  }
  await walk(root)
  return out.sort((a, b) => a.path.localeCompare(b.path))
}

// level 在读盘这一层就生效：成本闸门若只在拼 prompt 时生效，
// 大文件已经进了内存，省不下真正贵的那部分。
export async function readMaterials(cellDir, level, reply = null) {
  const m = { reply, artifacts: [], transcript: null }
  if (level === 'reply') return m
  m.artifacts = await readArtifacts(cellDir)
  if (level === 'transcript') {
    const f = path.join(cellDir, 'transcript.jsonl')
    m.transcript = await fs.pathExists(f) ? await fs.readFile(f, 'utf8') : null
  }
  return m
}

// grader 跑在空 jail 里、不装任何 skill：跑在宿主环境的话，
// ~/.claude/skills 那些会被加载，grader 可能被自己要判的 skill 触发，判定不可复现。
export async function invokeClaudeGrader(prompt, model, ctx = {}) {
  const { dir: jailDir, cleanup } = await createJail()
  try {
    const env = claudeAdapter.jailEnv({
      jailDir, source: ctx.source ?? process.env,
      oauthToken: ctx.oauthToken, baseUrl: ctx.baseUrl, apiKey: ctx.apiKey,
    })
    const argv = ['-p', '--model', model, '--setting-sources', 'user', prompt]
    return await new Promise(resolve => {
      let out = ''
      const child = spawn('claude', argv, { cwd: jailDir, env, stdio: ['ignore', 'pipe', 'ignore'] })
      child.stdout.on('data', d => { out += d })
      child.on('close', () => resolve(out))
      child.on('error', e => resolve(`grader spawn failed: ${e.message}`))
    })
  } finally {
    await cleanup()
  }
}

// pi 的 artifactChannel 是 'none'：HOME 重定向后登录不了，产出物永远进不了 jail。
// 材料对 pi 来说恒为空，但一个自信的 grader 未必会老实报 unavailable——
// 信它自证等于把整个平台列的质量假象都放过去了。所以这里用平台画像做强制覆盖，
// 而不是指望 grader 每次都诚实认怂。只管 source === 'artifact'：transcript 对
// pi 仍然采得到，那些断言留给 grader 自己判，不该被这条规则误伤。
function applyArtifactChannelOverride(assertions, declaredAssertions, platform) {
  const profile = PROFILE_BY_ID.get(platform)
  if (profile?.artifactChannel !== 'none') return assertions
  const sourceById = new Map(declaredAssertions.map(a => [a.id, a.source]))
  return assertions.map(a => {
    if (sourceById.get(a.id) !== 'artifact') return a
    return {
      id: a.id,
      verdict: 'unavailable',
      evidence: `platform "${platform}" 的 artifactChannel 为 "none"，产出物出不了 jail，这条 artifact 级断言没有材料可判`,
    }
  })
}

// invoke 本身可能抛出（比如 CLI 里 claudeOAuthToken() 读 keychain 失败）——
// 不是只有「返回了坏文本」这一种坏法。抛出必须和坏文本走同一条路：
// 吞掉、留痕、让 parseGraderOutput 判 unavailable，不能让异常逃出格子的循环，
// 否则一次 keychain 抖动就会把已经判完的格子全部陪葬。
async function safeInvoke(invoke, prompt, model) {
  try {
    return await invoke(prompt, model)
  } catch (e) {
    return `grader invocation threw: ${e.message}`
  }
}

export async function runGrade({ runDir, graderModel, only, invoke, declarations }) {
  if (!graderModel) throw new Error('--grader-model is required — an unpinned grader confounds the measuring stick with the thing measured')
  const records = await fs.readJson(path.join(runDir, 'records.json'))
  const cells = selectGradeCells({ records, declarations, only })

  const gradings = []
  for (const c of cells) {
    const level = maxSourceLevel(c.evalDef.assertions)
    const cellDir = path.join(runDir, 'cells', cellDirName(c))
    const materials = await readMaterials(cellDir, level, c.reply)
    const prompt = buildGradePrompt({ evalDef: c.evalDef, materials, task: c.task })

    // 重试一次：量具偶发不吐 JSON 是常见的，重试成本远低于把整格记成 unavailable。
    let parsed = parseGraderOutput(await safeInvoke(invoke, prompt, graderModel), c.evalDef.assertions)
    if (!parsed.ok) {
      parsed = parseGraderOutput(await safeInvoke(invoke, prompt, graderModel), c.evalDef.assertions)
    }

    const assertions = applyArtifactChannelOverride(parsed.assertions, c.evalDef.assertions, c.platform)

    gradings.push({
      skill: c.skill, platform: c.platform, mode: c.mode,
      repeat: c.repeat, evalId: c.evalDef.id,
      frozen: c.evalDef.frozen ?? null,
      assertions,
    })
  }

  const subjectModel = records.find(r => r.model)?.model ?? null
  const out = { runId: path.basename(runDir), graderModel, subjectModel, gradings }
  await fs.writeJson(path.join(runDir, 'gradings.json'), out, { spaces: 2 })
  return out
}
