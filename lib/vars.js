// lib/vars.js
import fs from 'fs-extra'
import path from 'path'
import os from 'os'
import { input } from '@inquirer/prompts'

export function buildAutoVars() {
  return { HOME: os.homedir() }
}

export async function loadVarDefs(skillSrcPath) {
  const varsFile = path.join(skillSrcPath, 'vars.json')
  if (!await fs.pathExists(varsFile)) return []
  return fs.readJson(varsFile)
}

export function substituteVars(text, varsMap) {
  return text.replace(/\{\{(\w+)\}\}/g, (_, name) => varsMap[name] ?? `{{${name}}}`)
}

export async function resolveVars(varDefs, autoVars) {
  const result = { ...autoVars }
  for (const def of varDefs) {
    const defaultVal = substituteVars(def.default ?? '', autoVars)
    const value = await input({
      message: `${def.description}:`,
      default: defaultVal,
    })
    result[def.name] = value
  }
  return result
}
