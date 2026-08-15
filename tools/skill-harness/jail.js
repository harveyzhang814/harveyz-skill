import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'

// 白名单，不是黑名单：新出现的环境变量默认不通过。分组抄 QM 的 CLAUDE_ENV_PASSTHROUGH。
export const ENV_WHITELIST = [
  'PATH', 'TMPDIR', 'LANG', 'LC_ALL',
  'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS',
  'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'ALL_PROXY',
]

export const SECRET_KEYS = new Set([
  'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'MINIMAX_CN_API_KEY',
])

export function buildEnv(source, extra = {}) {
  const env = {}
  for (const name of ENV_WHITELIST) {
    if (source[name] !== undefined) env[name] = source[name]
  }
  return { ...env, ...extra }
}

export function redactEnv(env) {
  return Object.fromEntries(
    Object.entries(env).map(([k, v]) => [k, SECRET_KEYS.has(k) ? '***' : v]),
  )
}

// 目录名必须中性：模型看得见 cwd，带 jail/inject 字样会被判成 prompt injection。
export async function createJail() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'skill-harness-'))
  return { dir, cleanup: () => fs.remove(dir) }
}

// HOME 重定向后 claude 读不到凭证文件也读不到 keychain，必须显式注入 token。
export function claudeOAuthToken() {
  const raw = execFileSync('security', ['find-generic-password', '-s', 'Claude Code-credentials', '-w'], { encoding: 'utf8' })
  return JSON.parse(raw).claudeAiOauth.accessToken
}

export function readEnvFile(file) {
  if (!fs.existsSync(file)) return {}
  const out = {}
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq < 1) continue
    const key = trimmed.slice(0, eq).trim()
    let value = trimmed.slice(eq + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    out[key] = value
  }
  return out
}
