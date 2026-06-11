import os from 'os'
import path from 'path'

export const SKILL_TARGETS = ['claude', 'cursor', 'codex', 'openclaw', 'hermes', 'opencode']

export const USER_ONLY_TARGETS = new Set(['openclaw', 'hermes'])

// Targets whose user-level skill dir doesn't follow ~/.{name}/skills
const USER_DIR_OVERRIDES = {
  opencode: path.join(os.homedir(), '.config', 'opencode', 'skills'),
}

export function userSkillDir(name) {
  return USER_DIR_OVERRIDES[name] ?? path.join(os.homedir(), `.${name}`, 'skills')
}

function skillDir(name, scope) {
  if (USER_ONLY_TARGETS.has(name) || scope !== 'project')
    return userSkillDir(name)
  return path.join(process.cwd(), `.${name}`, 'skills')
}

export const TARGETS = {
  claude:   path.join(os.homedir(), '.claude',   'skills'),
  cursor:   path.join(os.homedir(), '.cursor',   'skills'),
  codex:    path.join(os.homedir(), '.codex',    'skills'),
  openclaw: path.join(os.homedir(), '.openclaw', 'skills'),
  hermes:   path.join(os.homedir(), '.hermes',   'skills'),
  opencode: path.join(os.homedir(), '.config', 'opencode', 'skills'),
  shell:    path.join(os.homedir(), '.local', 'bin'),
}

export function buildTargetChoices(scope = 'user') {
  return SKILL_TARGETS
    .filter(name => scope === 'user' || !USER_ONLY_TARGETS.has(name))
    .map(name => {
      const dir = skillDir(name, scope)
      return { name: `${name.padEnd(8)} (${dir})`, value: name }
    })
}

export const TARGET_CHOICES = buildTargetChoices('user')

// 返回选中 targets 的 { name, dir } 列表，all 展开为全部
export function resolveTargets(selected, scope = 'user') {
  const eligible = scope === 'user'
    ? SKILL_TARGETS
    : SKILL_TARGETS.filter(name => !USER_ONLY_TARGETS.has(name))
  if (selected.includes('all')) return eligible.map(name => ({ name, dir: skillDir(name, scope) }))
  return selected.map(name => {
    if (!SKILL_TARGETS.includes(name)) throw new Error(`Unknown target: "${name}"`)
    return { name, dir: skillDir(name, scope) }
  })
}

export const HOOK_TARGETS = ['claude', 'codex']

export function buildHookTargetChoices() {
  return [
    { name: `${'claude'.padEnd(8)} (~/.claude/hooks/)`, value: 'claude' },
    { name: `${'codex'.padEnd(8)} (~/.codex/hooks/)`, value: 'codex' },
  ]
}
