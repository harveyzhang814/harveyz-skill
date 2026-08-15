import fs from 'fs-extra'
import path from 'node:path'
import { PHASE1_PLATFORMS } from './select.js'

export async function loadRuns(baseDir) {
  if (!await fs.pathExists(baseDir)) return []
  const entries = await fs.readdir(baseDir)
  const runs = []
  for (const id of entries.sort()) {
    const file = path.join(baseDir, id, 'records.json')
    if (!await fs.pathExists(file)) continue
    const stat = await fs.stat(file)
    runs.push({ runId: id, at: stat.mtime, records: await fs.readJson(file) })
  }
  return runs
}

// 允许挑着跑，就必须同时提供「哪些格子很久没跑 / 结论已过期」的视图，
// 否则选择机制会在半年内把覆盖率悄悄掏空，而没有任何一次运行会报错。
export function buildCoverage({ runs, skills, now = new Date() }) {
  const latest = new Map()
  for (const run of runs) {
    for (const rec of run.records) {
      const key = `${rec.skill}/${rec.platform}`
      const prev = latest.get(key)
      if (!prev || run.at > prev.at) latest.set(key, { at: run.at, contentHash: rec.contentHash ?? null })
    }
  }

  const cells = []
  for (const s of skills) {
    for (const platform of PHASE1_PLATFORMS) {
      const hit = latest.get(`${s.path}/${platform}`)
      if (!hit) {
        cells.push({ skill: s.path, platform, lastRunAt: null, ageDays: null, stale: false, state: 'never' })
        continue
      }
      const stale = hit.contentHash !== s.contentHash
      cells.push({
        skill: s.path, platform,
        lastRunAt: hit.at,
        ageDays: Math.floor((now - hit.at) / 86400000),
        stale,
        state: stale ? 'stale' : 'fresh',
      })
    }
  }
  return cells
}

export function renderCoverage(cells) {
  const skills = [...new Set(cells.map(c => c.skill))]
  const width = Math.max(24, ...skills.map(s => s.length)) + 2
  const head = 'skill'.padEnd(width) + PHASE1_PLATFORMS.map(p => p.padEnd(12)).join('')
  const rows = skills.map(skill => {
    const cols = PHASE1_PLATFORMS.map(platform => {
      const c = cells.find(x => x.skill === skill && x.platform === platform)
      if (!c || c.state === 'never') return 'never'.padEnd(12)
      return `${c.ageDays}d ago${c.stale ? '·陈' : ''}`.padEnd(12)
    })
    return skill.padEnd(width) + cols.join('')
  })
  return [head, ...rows].join('\n')
}
