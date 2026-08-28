import path from 'node:path'
import { buildEnv } from '../jail.js'
import { piProfile } from '../profiles.js'
import { parsePiJsonl } from '../parse/pi-jsonl.js'

// pi 是三个平台里 jail 最轻的：-ns 关闭发现、--skill 显式加载，
// 二者实测可共存，得到「恰好一个 skill」的环境。
export const piAdapter = {
  profile: piProfile,
  compensation: '',

  // 2026-08-17 实测：pi 的凭证存在 $HOME/.pi/agent/auth.json，重定向 HOME 后
  // pi 找不到 minimax-cn 的 key，报 "No API key found"（exitCode 1）。
  // 不重定向就没法把 skill 的产出物（写到 $HOME/.hskill/ 等）捞进 jail，
  // 但重定向就没法认证——两难之下选认证，产出物走 artifactChannel: 'none'。
  jailEnv({ source = {} }) {
    return buildEnv(source, {})
  },

  async install({ skillPath }) {
    return ['--skill', path.resolve(skillPath)]
  },

  args({ model, provider, systemAppend, positional, jailDir }) {
    const a = [
      '-p',
      '-ns', '-ne', '-np', '--no-themes', '-nc',
      '--session-dir', path.join(jailDir, 'sessions'),
      '--mode', 'json',
      '--model', model,
      '--provider', provider,
    ]
    if (systemAppend) a.push('--append-system-prompt', systemAppend)
    a.push(positional)
    return a
  },

  collect() {
    return null
  },

  parse(raw, ctx) {
    return parsePiJsonl(raw, ctx)
  },
}
