#!/usr/bin/env node
import fs from 'fs'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'
import { SKILL_TARGETS, USER_ONLY_TARGETS } from '../lib/targets.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const skillName        = process.argv[2]?.trim()
const availableVersion = process.argv[3]?.trim() || '—'
const kind             = process.argv[4]?.trim()
const srcPath          = process.argv[5]?.trim()
const platformKey      = process.argv[6]?.trim() || null

const G = '\x1b[32m', Y = '\x1b[33m', D = '\x1b[2m', R = '\x1b[0m', B = '\x1b[1m'

if (!skillName) process.exit(0)

if (kind !== 'skill') {
  const home = os.homedir()
  const installedBin  = path.join(home, '.local', 'bin', skillName)
  const installedMeta = path.join(home, '.hskill', 'tools', `${skillName}.json`)

  function readToolMeta(jsonPath) {
    try {
      const data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'))
      return data.version ?? '—'
    } catch { return '—' }
  }

  const installed        = fs.existsSync(installedBin)
  const installedVersion = installed ? readToolMeta(installedMeta) : '—'
  const sourceVersion    = srcPath ? readToolMeta(path.join(srcPath, 'tool.json')) : availableVersion
  const status = !installed ? 'none'
    : installedVersion === '—' || installedVersion === sourceVersion ? 'up-to-date'
    : 'update'

  function statusLine(version, st) {
    const ver = version.padEnd(8)
    if (st === 'up-to-date') return ver + '  ' + G + '✓ up to date' + R
    if (st === 'update')     return ver + '  ' + Y + '↑ update available' + R
    return ver + '  ' + D + '— not installed' + R
  }

  console.log(B + skillName + R)
  console.log(D + 'available: ' + R + sourceVersion)
  console.log('')
  console.log(B + 'INSTALL STATUS' + R)
  console.log('  ' + '~/.local/bin'.padEnd(14) + '  ' + statusLine(installedVersion, status))
  console.log('')
  if (status === 'update') {
    console.log(Y + 'ACTION: update → ~/.local/bin' + R)
  } else if (status === 'none') {
    console.log(D + 'STATUS: not installed' + R)
  } else {
    console.log(G + 'STATUS: ok' + R)
  }
  process.exit(0)
}

function readVersion(skillPath) {
  try {
    const content = fs.readFileSync(path.join(skillPath, 'SKILL.md'), 'utf8')
    const m = content.match(/^---[\s\S]*?^version:\s*["']?([^"'\n]+)["']?/m)
    return m ? m[1].trim() : '—'
  } catch { return '—' }
}

function statusLine(version, status) {
  const ver = version.padEnd(8)
  if (status === 'up-to-date') return ver + '  ' + G + '✓ up to date' + R
  if (status === 'update')     return ver + '  ' + Y + '↑ update available' + R
  return ver + '  ' + D + '— not installed' + R
}

const home = os.homedir()

function checkScope(targets, dirFn) {
  return targets.map(t => {
    const ver    = readVersion(path.join(dirFn(t), skillName))
    const status = ver === '—' ? 'none'
      : ver === availableVersion ? 'up-to-date'
      : 'update'
    return { tool: t, version: ver, status }
  })
}

// 单平台视图：只展示 ctrl-t 当前所在平台的状态，不展示全平台矩阵
if (platformKey && SKILL_TARGETS.includes(platformKey)) {
  const cwd = process.cwd()
  const userDir    = path.join(home, `.${platformKey}`, 'skills')
  const projectDir = path.join(cwd, `.${platformKey}`, 'skills')
  const [userDetail]    = checkScope([platformKey], () => userDir)
  const projectDetail   = USER_ONLY_TARGETS.has(platformKey) || cwd === home
    ? { version: '—', status: 'none' }
    : checkScope([platformKey], () => projectDir)[0]

  console.log(B + skillName + R)
  console.log(D + 'available: ' + R + availableVersion)
  console.log('')

  console.log(B + platformKey.toUpperCase() + ' STATUS' + R)
  console.log('  ' + 'user'.padEnd(8)    + statusLine(userDetail.version, userDetail.status))
  console.log('  ' + 'project'.padEnd(8) + statusLine(projectDetail.version, projectDetail.status))
  console.log('')

  if (userDetail.status === 'update' || projectDetail.status === 'update') {
    console.log(Y + 'ACTION: update → ' + platformKey + R)
  } else if (userDetail.status === 'none' && projectDetail.status === 'none') {
    console.log(D + 'STATUS: not installed' + R)
  } else {
    console.log(G + 'STATUS: ok' + R)
  }
  process.exit(0)
}

const userTargets    = SKILL_TARGETS
const projectTargets = SKILL_TARGETS.filter(t => !USER_ONLY_TARGETS.has(t))

const cwd = process.cwd()
const userDetails    = checkScope(userTargets,    t => path.join(home, `.${t}`, 'skills'))
const projectDetails = cwd === home
  ? projectTargets.map(t => ({ tool: t, version: '—', status: 'none' }))
  : checkScope(projectTargets, t => path.join(cwd, `.${t}`, 'skills'))

console.log(B + skillName + R)
console.log(D + 'available: ' + R + availableVersion)
console.log('')

console.log(B + 'USER LEVEL' + R)
for (const { tool, version, status } of userDetails) {
  console.log('  ' + tool.padEnd(8) + statusLine(version, status))
}
console.log('')

console.log(B + 'PROJECT LEVEL' + R)
for (const { tool, version, status } of projectDetails) {
  console.log('  ' + tool.padEnd(8) + statusLine(version, status))
}
console.log('')

const allDetails  = [...userDetails, ...projectDetails]
const needsUpdate = allDetails.filter(d => d.status === 'update')
const allNone     = allDetails.every(d => d.status === 'none')

if (needsUpdate.length > 0) {
  const tools = [...new Set(needsUpdate.map(d => d.tool))].join(', ')
  console.log(Y + 'ACTION: update → ' + tools + R)
} else if (allNone) {
  console.log(D + 'STATUS: not installed' + R)
} else {
  console.log(G + 'STATUS: ok' + R)
}
