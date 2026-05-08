import os from 'os'
import path from 'path'

export const TARGETS = {
  claude: path.join(os.homedir(), '.claude', 'skills'),
  cursor: path.join(os.homedir(), '.cursor', 'skills'),
  codex: path.join(os.homedir(), '.codex', 'skills'),
  shell: path.join(os.homedir(), '.local', 'bin'),
}

export const TARGET_CHOICES = Object.entries(TARGETS).map(([name, dir]) => ({
  name: `${name.padEnd(8)} (${dir})`,
  value: name,
}))

// 返回选中 targets 的 { name, dir } 列表，all 展开为全部
export function resolveTargets(selected) {
  if (selected.includes('all')) return Object.entries(TARGETS).map(([name, dir]) => ({ name, dir }))
  return selected.map(name => {
    const dir = TARGETS[name]
    if (!dir) throw new Error(`Unknown target: "${name}"`)
    return { name, dir }
  })
}
