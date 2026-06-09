// lib/vars.js
import fs from 'fs-extra'
import path from 'path'
import os from 'os'
import { input, select } from '@inquirer/prompts'

export function buildAutoVars() {
  return { HOME: os.homedir() }
}

export async function loadVarDefs(skillSrcPath) {
  const varsFile = path.join(skillSrcPath, 'vars.json')
  if (!await fs.pathExists(varsFile)) return []
  const defs = await fs.readJson(varsFile)
  if (!Array.isArray(defs)) throw new Error(`vars.json must be an array (got ${typeof defs})`)
  return defs
}

export function substituteVars(text, varsMap) {
  return text.replace(/\{\{(\w+)\}\}/g, (_, name) => varsMap[name] ?? `{{${name}}}`)
}

async function detectChromeProfiles() {
  const chromeBase = path.join(os.homedir(), 'Library/Application Support/Google/Chrome')
  if (!await fs.pathExists(chromeBase)) return []

  const entries = await fs.readdir(chromeBase)
  const profileDirs = entries.filter(e => e === 'Default' || e.startsWith('Profile '))
  profileDirs.sort((a, b) => (a === 'Default' ? -1 : b === 'Default' ? 1 : a.localeCompare(b)))

  const profiles = []
  for (const name of profileDirs) {
    const dir = path.join(chromeBase, name)
    let email = ''
    try {
      const prefs = await fs.readJson(path.join(dir, 'Preferences'))
      const accounts = prefs.account_info ?? []
      email = accounts[0]?.email ?? prefs.user_name ?? ''
    } catch { /* unreadable */ }
    profiles.push({ name, dir, email })
  }
  return profiles
}

export async function resolveVars(varDefs = [], autoVars) {
  const result = { ...autoVars }
  for (const def of varDefs) {
    const defaultVal = substituteVars(def.default ?? '', autoVars)

    if (def.type === 'chrome_profile_select') {
      const profiles = await detectChromeProfiles()
      if (profiles.length > 0) {
        const choices = profiles.map(p => ({
          name: p.email ? `${p.name}  (${p.email})` : p.name,
          value: p.dir,
        }))
        choices.push({ name: '手动输入路径…', value: '__manual__' })
        const selected = await select({ message: `${def.description}:`, choices })
        if (selected !== '__manual__') {
          result[def.name] = selected
          continue
        }
      }
    }

    const value = await input({
      message: `${def.description}:`,
      default: defaultVal,
    })
    result[def.name] = value
  }
  return result
}
