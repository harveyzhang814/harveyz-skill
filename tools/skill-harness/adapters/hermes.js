import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv } from '../jail.js'
import { hermesProfile } from '../profiles.js'
import { parseClaudeCodeJsonl } from '../parse/claude-code-jsonl.js'

// 白名单，不是整目录复制：只带凭证与模型配置，不带用户的 skills/SOUL.md/memory。
const SEED_FILES = ['.env', 'auth.json', 'config.yaml']

// Real hermes session IDs look like `20260815_055002_18cd05`
// (YYYYMMDD_HHMMSS_ + 6 lowercase hex chars), not a UUID — confirmed against
// real `hermes sessions list` output. UUID kept as a fallback alternative in
// case a different hermes version/config ever produces UUID-style IDs.
const SESSION_ID_RE = /\d{8}_\d{6}_[0-9a-f]{6}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i

export const hermesAdapter = {
  profile: hermesProfile,
  compensation: '',

  jailEnv({ jailDir, source = {} }) {
    return buildEnv(source, { HOME: jailDir })
  },

  async seedJail({ jailDir, hermesHome }) {
    const dest = path.join(jailDir, '.hermes')
    await fs.ensureDir(dest)
    for (const name of SEED_FILES) {
      const src = path.join(hermesHome, name)
      if (await fs.pathExists(src)) await fs.copy(src, path.join(dest, name))
    }
  },

  async install({ jailDir, skillPath }) {
    const dest = path.join(jailDir, '.hermes/skills', path.basename(skillPath))
    await fs.ensureDir(path.dirname(dest))
    await fs.copy(skillPath, dest)
    return []
  },

  args({ model, provider, positional, jailDir, systemAppend }) {
    if (systemAppend) throw new Error('hermes is prompt-only: systemAppend must be folded into the positional prompt')
    return [
      '-z', positional,
      '--safe-mode',
      '--yolo',
      '--usage-file', path.join(jailDir, 'usage.json'),
      '-m', model,
      '--provider', provider,
    ]
  },

  // -z 不打印 session id，所以 collect 先 sessions list。
  // jail 里每次运行都是全新 store，有且只有一个会话，因此这个做法是确定性的。
  parseSessionId(listOutput) {
    const m = String(listOutput).match(SESSION_ID_RE)
    return m ? m[0] : null
  },

  collectArgs(sessionId) {
    return ['sessions', 'export', '--format', 'trace', '--session-id', sessionId, '-']
  },

  parse(raw, ctx) {
    return parseClaudeCodeJsonl(raw, ctx)
  },
}
