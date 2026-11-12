// 拼装 AGENTS.md，以及 init / generate / check（Spec 5.2、5.6、5.7、6）。

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { ConfigError, loadSkeleton, loadPacks, resolveConfig } from './config.mjs'
import { renderTemplate } from './template.mjs'

const CONFIG_TEMPLATE = fileURLToPath(new URL('../../assets/config.template.json', import.meta.url))
const HEADER = /^<!-- compose-agentsmd: packs=(\S*) sha256=([0-9a-f]{64}); generated from \.hskill\/compose-agentsmd\/, do not edit -->$/
const FORBIDDEN_IN_SLOT = ['<!-- slot:', '<!-- compose-agentsmd:']

const sha256 = buf => createHash('sha256').update(buf).digest('hex')
const paths = root => {
  const base = resolve(root)
  const dir = join(base, '.hskill/compose-agentsmd')
  return { dir, config: join(dir, 'config.json'), slots: join(dir, 'slots'), localPacks: join(dir, 'packs'), agents: join(base, 'AGENTS.md') }
}

function readConfig(p) {
  if (!existsSync(p.dir) || !existsSync(p.config)) throw new ConfigError(`找不到配置 ${p.config}，请先运行 init`)
  try {
    return JSON.parse(readFileSync(p.config, 'utf8'))
  } catch (e) {
    throw new ConfigError(`配置 ${p.config} 不是合法 JSON：${e.message}`)
  }
}

function readDescriptionSlot(p, id) {
  const file = join(p.slots, `${id}.md`)
  if (!existsSync(file)) return ''
  const body = readFileSync(file, 'utf8').replace(/\r\n/g, '\n').trim()
  for (const bad of FORBIDDEN_IN_SLOT) {
    if (body.includes(bad)) throw new ConfigError(`${file}: 描述槽内容不能含 "${bad}"（防止伪造标记）`)
  }
  return body
}

// 返回完整 AGENTS.md 文本（含首行）、实际用到的包、以及不影响退出码的提示（warnings）
export function composeText({ root, packsDir }) {
  const p = paths(root)
  const config = readConfig(p)
  const skeleton = loadSkeleton()
  const packs = loadPacks({ packsDir, localPacksDir: p.localPacks })
  const { params, slots } = resolveConfig({ config, skeleton, packs })
  const disabled = new Set(config.disabled_slots ?? [])

  const blocks = []
  const used = new Map()
  const warnings = []
  for (const slot of slots) {
    const marker = `<!-- slot:${slot.id} -->`
    if (slot.kind === 'description') {
      const body = readDescriptionSlot(p, slot.id)
      if (slot.id === 'overview') {
        blocks.push(`${marker}\n# ${config.title}${body ? `\n\n${body}` : ''}`)
      } else if (body) {
        blocks.push(`${marker}\n${slot.heading ? `${slot.heading}\n\n` : ''}${body}`)
      }
      continue
    }
    if (slot.id === 'release-acceptance' && !params.agent_canvas) continue
    if (!slot.pack) {
      if (!disabled.has(slot.id)) warnings.push(`标准槽 "${slot.id}" 没有任何来源（所选包不填它、也没有覆盖），已跳过`)
      continue
    }
    const pack = packs.get(slot.pack)
    const file = join(pack.dir, `${slot.id}.md`)
    const rendered = renderTemplate(readFileSync(file, 'utf8'), params, file).replace(/\n+$/, '')
    const ref = pack.source === 'shipped' ? `${pack.name}@${pack.version}` : `local:${pack.name}`
    blocks.push(`<!-- slot:${slot.id} pack=${ref} -->\n${rendered}`)
    used.set(pack.name, { name: pack.name, source: pack.source, version: pack.version })
  }

  const usedPacks = [...used.values()].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
  const body = blocks.join('\n\n').replace(/\n{3,}/g, '\n\n').replace(/\n+$/, '') + '\n'
  const list = usedPacks.map(k => (k.source === 'shipped' ? `${k.name}@${k.version}` : `local:${k.name}`)).join(',')
  const header = `<!-- compose-agentsmd: packs=${list} sha256=${sha256(body)}; generated from .hskill/compose-agentsmd/, do not edit -->`
  return { text: `${header}\n${body}`, packs: usedPacks, warnings }
}

export function parseHeader(text) {
  const m = HEADER.exec(text.split('\n', 1)[0])
  if (!m) return null
  const packs = m[1] === '' ? [] : m[1].split(',').map(item => {
    if (item.startsWith('local:')) return { name: item.slice('local:'.length), source: 'local', version: null }
    const at = item.lastIndexOf('@')
    return { name: item.slice(0, at), source: 'shipped', version: item.slice(at + 1) }
  })
  return { packs, sha256: m[2] }
}

// 首行缺失或哈希与正文不符
function isHandEdited(buf) {
  const nl = buf.indexOf(10)
  const header = nl < 0 ? null : parseHeader(buf.subarray(0, nl).toString('utf8'))
  return !header || header.sha256 !== sha256(buf.subarray(nl + 1))
}

function compareVersions(a, b) {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (d !== 0) return Math.sign(d)
  }
  return 0
}

// 配置/模板错误与意外的 I/O 错误一律归为退出码 2（不写文件，消息进 errors），不抛堆栈；退出码 1 只留给「已存在 / 拒绝覆盖 / 状态非 ok」。
const failed = e => ({ code: 2, lines: [], errors: [e instanceof Error ? e.message : String(e)] })

export function runInit({ root }) {
  const p = paths(root)
  if (existsSync(p.dir)) {
    return { code: 1, lines: ['status=exists', `path=${p.dir}`] }
  }
  try {
    mkdirSync(p.slots, { recursive: true })
    writeFileSync(p.config, readFileSync(CONFIG_TEMPLATE))
    for (const s of loadSkeleton()) {
      if (s.kind === 'description') writeFileSync(join(p.slots, `${s.id}.md`), '')
    }
  } catch (e) {
    return failed(e)
  }
  return { code: 0, lines: ['status=created', `path=${p.dir}`] }
}

export function runGenerate({ root, packsDir, force = false }) {
  const p = paths(root)
  try {
    const composed = composeText({ root, packsDir })
    if (existsSync(p.agents) && isHandEdited(readFileSync(p.agents)) && !force) {
      return {
        code: 1,
        lines: ['status=hand-edited', `path=${p.agents}`],
        errors: [`${p.agents} 无生成标记或已被手改，拒绝覆盖；确认要覆盖请加 --force`, ...composed.warnings],
      }
    }
    writeFileSync(p.agents, composed.text)
    return { code: 0, lines: ['status=written', `path=${p.agents}`], errors: composed.warnings }
  } catch (e) {
    return failed(e)
  }
}

export function runCheck({ root, packsDir }) {
  try {
    return checkOnce({ root, packsDir })
  } catch (e) {
    return failed(e)
  }
}

function checkOnce({ root, packsDir }) {
  const p = paths(root)
  const composed = composeText({ root, packsDir })
  const shipped = composed.packs.filter(k => k.source === 'shipped')
  let generated = new Map()
  const status = []
  if (!existsSync(p.agents)) {
    status.push('missing')
  } else {
    const disk = readFileSync(p.agents)
    const header = parseHeader(disk.toString('utf8'))
    generated = new Map((header?.packs ?? []).filter(k => k.source === 'shipped').map(k => [k.name, k.version]))
    if (isHandEdited(disk)) status.push('hand-edited')
    if (shipped.some(k => generated.has(k.name) && compareVersions(generated.get(k.name), k.version) < 0)) status.push('outdated')
    if (status.length === 0 && !disk.equals(Buffer.from(composed.text))) status.push('stale')
  }
  if (status.length === 0) status.push('ok')
  const lines = [
    `status=${status.join(',')}`,
    `path=${p.agents}`,
    ...shipped.map(k => `pack=${k.name} installed=${k.version} generated=${generated.get(k.name) ?? ''}`),
  ]
  return { code: status[0] === 'ok' ? 0 : 1, lines, errors: composed.warnings }
}
