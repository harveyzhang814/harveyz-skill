import { createHash, randomUUID } from 'node:crypto'
import * as fs from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const SOURCE = 'docs/reference/skill-platform-adaptation.md'
const CONSUMERS = ['init-skill', 'contribute-skill']
const MARKER = /^<!-- platform-standard-sha256: [0-9a-f]{64} -->$/gm

async function readOptional(fsApi, path) {
  try { return await fsApi.readFile(path) }
  catch (error) {
    if (error.code === 'ENOENT') return null
    throw error
  }
}

export async function syncPlatformStandard({ root, mode, fsApi = fs }) {
  if (!['check', 'write'].includes(mode)) throw new Error('mode must be check or write')
  const source = await fsApi.readFile(join(root, SOURCE))
  const digest = createHash('sha256').update(source).digest('hex')
  const generated = Buffer.from(`<!-- Generated from ${SOURCE}; sha256: ${digest}. Do not edit. -->\n\n${source.toString('utf8')}`)
  const targets = []

  for (const name of CONSUMERS) {
    const base = `skills/mint/${name}`
    const skillPath = join(root, base, 'SKILL.md')
    const skill = await fsApi.readFile(skillPath)
    const body = skill.toString('utf8')
    const matches = [...body.matchAll(MARKER)]
    if (matches.length !== 1) throw new Error(`${skillPath}: expected exactly one platform-standard marker`)
    const next = body.replace(MARKER, `<!-- platform-standard-sha256: ${digest} -->`)
    targets.push({ path: skillPath, original: skill, expected: Buffer.from(next) })
    const copyPath = join(root, base, 'references/platform-adaptation.md')
    targets.push({ path: copyPath, original: await readOptional(fsApi, copyPath), expected: generated })
  }

  const drift = targets.filter(({ original, expected }) => original === null || !original.equals(expected)).map(({ path }) => path)
  if (mode === 'check' || drift.length === 0) return { ok: drift.length === 0, drift }

  const changed = targets.filter(({ path }) => drift.includes(path))
  const prepared = []
  const replaced = []
  try {
    for (const target of changed) {
      await fsApi.mkdir(dirname(target.path), { recursive: true })
      const temp = `${target.path}.platform-standard-tmp-${randomUUID()}`
      const backup = target.original === null ? null : `${target.path}.platform-standard-backup-${randomUUID()}`
      await fsApi.writeFile(temp, target.expected)
      if (backup) await fsApi.writeFile(backup, target.original)
      prepared.push({ ...target, temp, backup })
    }
    for (const target of prepared) {
      await fsApi.rename(target.temp, target.path)
      replaced.push(target)
    }
  } catch (error) {
    const rollbackErrors = []
    for (const target of replaced.reverse()) {
      try {
        if (target.backup) await fsApi.rename(target.backup, target.path)
        else await fsApi.unlink(target.path)
      } catch (rollbackError) {
        rollbackErrors.push(`${target.path}: ${rollbackError.message}`)
      }
    }
    for (const target of prepared) {
      await fsApi.unlink(target.temp).catch(() => {})
      if (target.backup && !rollbackErrors.some(line => line.startsWith(`${target.path}:`))) await fsApi.unlink(target.backup).catch(() => {})
    }
    if (rollbackErrors.length) throw new Error(`${error.message}; rollback failed: ${rollbackErrors.join('; ')}`, { cause: error })
    throw error
  }
  for (const target of prepared) if (target.backup) await fsApi.unlink(target.backup)
  return { ok: true, drift: [] }
}

const invokedAsCli = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (invokedAsCli) {
  const [arg, ...extra] = process.argv.slice(2)
  if (extra.length || !['--check', '--write'].includes(arg)) {
    console.error('Usage: node scripts/sync-skill-platform-standard.mjs --check|--write')
    process.exitCode = 2
  } else {
    const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
    try {
      const result = await syncPlatformStandard({ root, mode: arg.slice(2) })
      if (!result.ok) {
        console.error(`Platform standard drift:\n${result.drift.join('\n')}`)
        process.exitCode = 1
      } else console.log('Platform standard synchronized')
    } catch (error) {
      console.error(error.message)
      process.exitCode = 1
    }
  }
}
