import path from 'node:path'
import { buildEnv } from '../jail.js'
import { piProfile } from '../profiles.js'
import { parsePiJsonl } from '../parse/pi-jsonl.js'

// pi 是三个平台里 jail 最轻的：-ns 关闭发现、--skill 显式加载，
// 二者实测可共存，得到「恰好一个 skill」的环境，无需 HOME 重定向。
export const piAdapter = {
  profile: piProfile,
  compensation: '',

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
