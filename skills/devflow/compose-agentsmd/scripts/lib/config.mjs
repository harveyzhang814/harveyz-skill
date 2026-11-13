// 骨架、模块包加载与配置校验（Spec 5.2 / 5.2a / 5.3）。任何校验失败抛 ConfigError，消息指出字段、包或槽。

import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { templateParams } from './template.mjs'

export class ConfigError extends Error {
  constructor(message) {
    super(message)
    this.name = 'ConfigError'
  }
}

const DEFAULT_SKELETON = fileURLToPath(new URL('../../assets/skeleton.json', import.meta.url))
const PARAM_TYPES = ['string', 'boolean']
const PARAM_NAME = /^\w+$/
// 骨架级字段由生成器固定，包不可声明同名参数；其中只有 agent_canvas 可被模板引用。
const SKELETON_FIELDS = ['title', 'pack', 'slot_packs', 'agent_canvas', 'disabled_slots']
// 由生成器从 resolved.env 注入、可被模板引用的内部取值名；包不可声明同名参数，配置里也不能写。
export const INJECTED_PARAMS = ['integration_branch', 'merge_script']
const PACK_NAME = /^[A-Za-z0-9][A-Za-z0-9._-]*$/
const RESERVED_PACK_NAMES = ['disabled']
const FORBIDDEN_IN_TITLE = ['<!-- slot:', '<!-- compose-agentsmd:']
const SPEC_DIR_PREFIX = 'docs/superpowers/specs'

const isPlainObject = v => v !== null && typeof v === 'object' && !Array.isArray(v)
const isStringArray = v => Array.isArray(v) && v.every(x => typeof x === 'string')

const RESOLVED_ENV_PATH = '.hskill/init-workflow/resolved.env'

// 逐行读取 <root>/.hskill/init-workflow/resolved.env（不 source）：跳过 # 注释与空行，按第一个 = 拆分，去掉 CR。
export function readResolvedEnv(root) {
  const file = join(root, RESOLVED_ENV_PATH)
  if (!existsSync(file)) throw new ConfigError(`找不到 ${file}，请先运行 init-workflow 生成它（集成分支与合并脚本取自其中的 merge_target / merge_script）`)
  const env = new Map()
  for (const raw of readFileSync(file, 'utf8').split('\n')) {
    const line = raw.replace(/\r$/, '')
    if (line.trim() === '' || line.trimStart().startsWith('#')) continue
    const i = line.indexOf('=')
    if (i < 0) continue
    env.set(line.slice(0, i), line.slice(i + 1))
  }
  return env
}

function readJson(path, what) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch (e) {
    throw new ConfigError(`${what} ${path} 无法读取或不是合法 JSON：${e.message}`)
  }
}

export function loadSkeleton(skeletonPath = DEFAULT_SKELETON) {
  const data = readJson(skeletonPath, '骨架文件')
  if (!Array.isArray(data)) throw new ConfigError(`骨架文件 ${skeletonPath} 必须是数组`)
  return data.map(s => ({ id: s.id, kind: s.kind, heading: s.heading ?? null }))
}

function validateParams(params, where) {
  if (!isPlainObject(params)) throw new ConfigError(`${where}: params 必须是对象`)
  for (const [name, decl] of Object.entries(params)) {
    if (!PARAM_NAME.test(name)) throw new ConfigError(`${where}: 参数名 "${name}" 非法`)
    if (INJECTED_PARAMS.includes(name)) throw new ConfigError(`${where}: 参数 "${name}" 由生成器从 resolved.env 注入，不可在包里声明`)
    if (SKELETON_FIELDS.includes(name)) throw new ConfigError(`${where}: 参数 "${name}" 与骨架级字段重名，不可在包里声明`)
    if (!isPlainObject(decl) || !PARAM_TYPES.includes(decl.type)) {
      throw new ConfigError(`${where}: 参数 "${name}" 的 type 只能是 ${PARAM_TYPES.join(' / ')}`)
    }
    if ('required' in decl && typeof decl.required !== 'boolean') throw new ConfigError(`${where}: 参数 "${name}" 的 required 必须是 boolean`)
    if ('default' in decl && typeof decl.default !== decl.type) throw new ConfigError(`${where}: 参数 "${name}" 的 default 类型与 type 不符`)
  }
}

function loadPack(dir, name, source, standardSlots) {
  const where = `包 "${name}"（${dir}）`
  if (!PACK_NAME.test(name)) throw new ConfigError(`${where}: 包名 "${name}" 非法，只能由字母、数字、点、下划线、连字符组成，且以字母或数字开头`)
  if (RESERVED_PACK_NAMES.includes(name)) throw new ConfigError(`${where}: 包名 "${name}" 是保留字，请改名`)
  const manifestPath = join(dir, 'pack.json')
  if (!existsSync(manifestPath)) throw new ConfigError(`${where}: 缺少 pack.json`)
  const m = readJson(manifestPath, 'pack.json')
  if (!isPlainObject(m)) throw new ConfigError(`${where}: pack.json 必须是对象`)
  if (m.name !== name) throw new ConfigError(`${where}: pack.json 的 name "${m.name}" 与目录名不一致`)
  if (!isStringArray(m.slots)) throw new ConfigError(`${where}: slots 必须是字符串数组`)
  for (const s of m.slots) {
    if (!standardSlots.includes(s)) throw new ConfigError(`${where}: 槽 "${s}" 不是骨架中的标准槽`)
    if (!existsSync(join(dir, `${s}.md`))) throw new ConfigError(`${where}: 声明了槽 "${s}" 但缺少 ${s}.md`)
  }
  const linked = m.linked ?? []
  if (!Array.isArray(linked) || !linked.every(g => isStringArray(g) && g.length >= 2)) {
    throw new ConfigError(`${where}: linked 必须是由至少两个槽 id 组成的数组的数组`)
  }
  for (const g of linked) {
    for (const s of g) if (!m.slots.includes(s)) throw new ConfigError(`${where}: 联动组成员 "${s}" 不在 slots 内`)
  }
  const params = m.params ?? {}
  validateParams(params, where)

  const allowed = new Set([...Object.keys(params), 'agent_canvas', ...INJECTED_PARAMS])
  for (const s of m.slots) {
    const file = join(dir, `${s}.md`)
    for (const n of templateParams(readFileSync(file, 'utf8'), file)) {
      if (!allowed.has(n)) throw new ConfigError(`${file}: 模板引用了包 "${name}" 未声明的参数 "${n}"（undeclared）`)
    }
  }

  let version = null
  if (source === 'shipped') {
    const versionPath = join(dir, 'VERSION')
    if (!existsSync(versionPath)) throw new ConfigError(`${where}: 发布包缺少 VERSION`)
    version = readFileSync(versionPath, 'utf8').trim()
  }
  return { name, source, version, slots: m.slots, linked, params, dir }
}

function listPackDirs(root) {
  if (!existsSync(root)) return []
  return readdirSync(root)
    .filter(n => !n.startsWith('.') && statSync(join(root, n)).isDirectory())
    .sort()
    .map(n => [n, join(root, n)])
}

export function loadPacks({ packsDir, localPacksDir }) {
  const standardSlots = loadSkeleton().filter(s => s.kind === 'standard').map(s => s.id)
  const packs = new Map()
  for (const [source, root] of [['shipped', packsDir], ['local', localPacksDir]]) {
    for (const [name, dir] of listPackDirs(root)) {
      if (packs.has(name)) {
        throw new ConfigError(`包 "${name}" 在发布包目录与本地包目录里都存在（${packs.get(name).dir} 与 ${dir}），不做隐式优先，请改名或删除其一`)
      }
      packs.set(name, loadPack(dir, name, source, standardSlots))
    }
  }
  return packs
}

function checkSkeletonFields(config) {
  if (typeof config.title !== 'string' || config.title.trim() === '') throw new ConfigError('字段 title 必填，且必须是非空 string')
  if (/[\r\n]/.test(config.title)) throw new ConfigError('字段 title 不能含换行')
  for (const bad of FORBIDDEN_IN_TITLE) {
    if (config.title.includes(bad)) throw new ConfigError(`字段 title 不能含 "${bad}"（防止伪造标记）`)
  }
  if (typeof config.pack !== 'string' || config.pack === '') throw new ConfigError('字段 pack 必填，且必须是 string')
  if ('slot_packs' in config) {
    const sp = config.slot_packs
    if (!isPlainObject(sp) || !Object.values(sp).every(v => typeof v === 'string')) {
      throw new ConfigError('字段 slot_packs 必须是 { 槽id: 包名 } 对象')
    }
  }
  if ('agent_canvas' in config && typeof config.agent_canvas !== 'boolean') throw new ConfigError('字段 agent_canvas 必须是 boolean')
  if ('disabled_slots' in config && !isStringArray(config.disabled_slots)) throw new ConfigError('字段 disabled_slots 必须是 string 数组')
}

function getPack(packs, name, field) {
  const p = packs.get(name)
  if (!p) throw new ConfigError(`${field} 指向的包 "${name}" 不存在`)
  return p
}

export function resolveConfig({ config, skeleton, packs }) {
  if (!isPlainObject(config)) throw new ConfigError('配置必须是 JSON 对象')
  checkSkeletonFields(config)
  const slotPacks = config.slot_packs ?? {}
  const disabled = new Set(config.disabled_slots ?? [])
  const agentCanvas = config.agent_canvas ?? false
  const standardIds = skeleton.filter(s => s.kind === 'standard').map(s => s.id)

  // 解析每个标准槽的来源
  const mainPack = getPack(packs, config.pack, 'pack')
  for (const [slot, name] of Object.entries(slotPacks)) {
    if (!standardIds.includes(slot)) throw new ConfigError(`slot_packs 的键 "${slot}" 不是标准槽`)
    if (!getPack(packs, name, `slot_packs.${slot}`).slots.includes(slot)) {
      throw new ConfigError(`slot_packs.${slot} 指向的包 "${name}" 没有声明槽 "${slot}"`)
    }
  }
  for (const slot of disabled) {
    if (!standardIds.includes(slot)) throw new ConfigError(`disabled_slots 含非标准槽 "${slot}"，描述槽不能关闭`)
  }
  const source = new Map() // 标准槽 id -> 包名 | 'disabled' | null
  for (const id of standardIds) {
    if (disabled.has(id)) source.set(id, 'disabled')
    else if (slotPacks[id]) source.set(id, slotPacks[id])
    else source.set(id, mainPack.slots.includes(id) ? mainPack.name : null)
  }
  const slots = skeleton.map(s => ({
    id: s.id, kind: s.kind, heading: s.heading,
    pack: s.kind === 'standard' && source.get(s.id) !== 'disabled' ? source.get(s.id) : null,
  }))

  // 被用到的包：至少填了一个未关闭的槽
  const usedNames = [...new Set(slots.map(s => s.pack).filter(Boolean))]

  // 联动组：组内槽要么全关、要么来自同一个包
  for (const pack of new Set([mainPack, ...usedNames.map(n => packs.get(n))])) {
    for (const group of pack.linked) {
      const states = new Set(group.map(id => source.get(id)))
      if (states.size > 1) {
        throw new ConfigError(`联动组 [${group.join(', ')}]（包 "${pack.name}" 声明，linked）必须来自同一个包且只能一起关闭，现为 ${group.map(id => `${id}=${source.get(id) ?? '无来源'}`).join('，')}`)
      }
    }
  }

  // 生效参数 = 用到的包的 params 并集；类型或默认值冲突则报错
  const effective = new Map()
  for (const name of usedNames) {
    for (const [p, decl] of Object.entries(packs.get(name).params)) {
      const prev = effective.get(p)
      if (!prev) { effective.set(p, { ...decl, from: name }); continue }
      if (prev.type !== decl.type || JSON.stringify(prev.default) !== JSON.stringify(decl.default)) {
        throw new ConfigError(`参数 "${p}" 在包 "${prev.from}" 与 "${name}" 里的类型或默认值声明冲突`)
      }
      if (decl.required) prev.required = true
    }
  }

  for (const key of Object.keys(config)) {
    if (!SKELETON_FIELDS.includes(key) && !effective.has(key)) {
      const hint = INJECTED_PARAMS.includes(key) || key === 'merge_command'
        ? '；集成分支与合并脚本现由 init-workflow 的 resolved.env 提供，请从配置中删除该字段'
        : ''
      throw new ConfigError(`未知字段 "${key}"：既不是骨架级字段，也不是所用包声明的参数${hint}`)
    }
  }

  const params = { agent_canvas: agentCanvas }
  for (const [p, decl] of effective) {
    if (p in config) {
      if (typeof config[p] !== decl.type) throw new ConfigError(`字段 ${p} 必须是 ${decl.type}`)
      if (decl.required && decl.type === 'string' && config[p].trim() === '') throw new ConfigError(`必填字段 ${p} 不能为空字符串（包 "${decl.from}" 声明）`)
      params[p] = config[p]
    } else if (decl.required) {
      throw new ConfigError(`缺少必填字段 ${p}（包 "${decl.from}" 声明）`)
    } else {
      params[p] = decl.default ?? (decl.type === 'boolean' ? false : '')
    }
  }

  if (agentCanvas && typeof params.spec_dir === 'string' && !params.spec_dir.startsWith(SPEC_DIR_PREFIX)) {
    throw new ConfigError(`agent_canvas 为 true 时 spec_dir 必须以 ${SPEC_DIR_PREFIX} 开头（describe-node 的 spec 自动发现只认这个前缀），现为 "${params.spec_dir}"`)
  }

  return { params, slots }
}
