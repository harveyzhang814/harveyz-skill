import os from 'os'
import path from 'path'

const SKILL_TARGETS = ['claude', 'cursor', 'codex']

function skillDir(name, scope) {
  if (scope === 'project') return path.join(process.cwd(), `.${name}`, 'skills')
  return path.join(os.homedir(), `.${name}`, 'skills')
}

export const TARGETS = {
  claude: path.join(os.homedir(), '.claude', 'skills'),
  cursor: path.join(os.homedir(), '.cursor', 'skills'),
  codex: path.join(os.homedir(), '.codex', 'skills'),
  shell: path.join(os.homedir(), '.local', 'bin'),
}

export function buildTargetChoices(scope = 'user') {
  return SKILL_TARGETS.map(name => {
    const dir = skillDir(name, scope)
    return { name: `${name.padEnd(8)} (${dir})`, value: name }
  })
}

export const TARGET_CHOICES = buildTargetChoices('user')

// 返回选中 targets 的 { name, dir } 列表，all 展开为全部
export function resolveTargets(selected, scope = 'user') {
  const allTargets = SKILL_TARGETS.map(name => ({ name, dir: skillDir(name, scope) }))
  if (selected.includes('all')) return allTargets
  return selected.map(name => {
    if (!SKILL_TARGETS.includes(name)) throw new Error(`Unknown target: "${name}"`)
    return { name, dir: skillDir(name, scope) }
  })
}
