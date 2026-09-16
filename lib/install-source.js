import { execSync } from 'child_process'
import { existsSync, readFileSync, writeFileSync } from 'fs'
import path from 'path'

let cachedGlobalRoot = null

export function globalRoot() {
  if (process.env.HSKILL_GLOBAL_ROOT) return process.env.HSKILL_GLOBAL_ROOT
  if (!cachedGlobalRoot) cachedGlobalRoot = execSync('npm root -g', { encoding: 'utf8' }).trim()
  return cachedGlobalRoot
}

function sourceFilePath() {
  return path.join(globalRoot(), 'harveyz-skill', '.hskill-source.json')
}

export function readSource() {
  const file = sourceFilePath()
  if (!existsSync(file)) return null
  try {
    return JSON.parse(readFileSync(file, 'utf8'))
  } catch {
    return null
  }
}

export function writeSource(info) {
  writeFileSync(sourceFilePath(), JSON.stringify(info, null, 2) + '\n')
}

export function gitInfo(repo) {
  const branch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: repo, encoding: 'utf8' }).trim()
  const commit = execSync('git rev-parse --short HEAD', { cwd: repo, encoding: 'utf8' }).trim()
  const dirty = execSync('git status --porcelain', { cwd: repo, encoding: 'utf8' }).trim().length > 0
  return { branch, commit, dirty }
}
