import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv } from '../jail.js'
import { claudeProfile } from '../profiles.js'
import { parseClaudeCodeJsonl } from '../parse/claude-code-jsonl.js'

// HOME 重定向后 claude 既读不到 ~/.claude/.credentials.json 也认不了 keychain
// （实测报 "Not logged in · Please run /login"），凭证必须经环境变量注入。
export const claudeAdapter = {
  profile: claudeProfile,
  compensation: '',

  jailEnv({ jailDir, source = {}, oauthToken, baseUrl, apiKey }) {
    const extra = { HOME: jailDir, CLAUDE_CONFIG_DIR: path.join(jailDir, '.claude') }
    if (baseUrl) extra.ANTHROPIC_BASE_URL = baseUrl
    if (apiKey) extra.ANTHROPIC_API_KEY = apiKey
    else if (oauthToken) extra.CLAUDE_CODE_OAUTH_TOKEN = oauthToken
    return buildEnv(source, extra)
  },

  async install({ jailDir, skillPath }) {
    const dest = path.join(jailDir, '.claude/skills', path.basename(skillPath))
    await fs.ensureDir(path.dirname(dest))
    await fs.copy(skillPath, dest)
    return []
  },

  args({ model, systemAppend, positional, sessionId }) {
    const a = [
      '-p',
      '--setting-sources', 'user',
      '--permission-mode', 'bypassPermissions',
      '--output-format', 'stream-json',
      '--verbose',
      '--model', model,
      '--session-id', sessionId,
    ]
    if (systemAppend) a.push('--append-system-prompt', systemAppend)
    a.push(positional)
    return a
  },

  collect() {
    return null
  },

  parse(raw, ctx) {
    return parseClaudeCodeJsonl(raw, ctx)
  },
}
