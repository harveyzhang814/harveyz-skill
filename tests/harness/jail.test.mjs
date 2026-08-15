import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv, redactEnv, createJail, ENV_WHITELIST, SECRET_KEYS, readEnvFile } from '../../tools/skill-harness/jail.js'

test('buildEnv: 白名单内的变量透传', () => {
  const env = buildEnv({ PATH: '/usr/bin', LANG: 'en_US.UTF-8' })
  assert.equal(env.PATH, '/usr/bin')
  assert.equal(env.LANG, 'en_US.UTF-8')
})

test('buildEnv: 白名单外的变量一律不透传', () => {
  const env = buildEnv({ PATH: '/usr/bin', CLAUDECODE: '1', ANTHROPIC_MODEL: 'x', RANDOM_NEW_VAR: 'y' })
  assert.equal(env.CLAUDECODE, undefined)
  assert.equal(env.ANTHROPIC_MODEL, undefined)
  assert.equal(env.RANDOM_NEW_VAR, undefined)
})

test('buildEnv: source 里没有的白名单变量不会造出 undefined 键', () => {
  const env = buildEnv({ PATH: '/usr/bin' })
  assert.ok(!('HTTPS_PROXY' in env))
})

test('buildEnv: extra 覆盖并追加', () => {
  const env = buildEnv({ PATH: '/usr/bin' }, { HOME: '/tmp/x', CLAUDE_CONFIG_DIR: '/tmp/x/.claude' })
  assert.equal(env.HOME, '/tmp/x')
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/x/.claude')
  assert.equal(env.PATH, '/usr/bin')
})

test('ENV_WHITELIST 是整表快照，新增项必须来这里登记', () => {
  assert.deepEqual(ENV_WHITELIST, [
    'PATH', 'TMPDIR', 'LANG', 'LC_ALL',
    'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS',
    'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'ALL_PROXY',
  ])
})

test('redactEnv: 凭证打码，其余原样', () => {
  const red = redactEnv({ PATH: '/usr/bin', CLAUDE_CODE_OAUTH_TOKEN: 'sk-ant-oat01-secret', ANTHROPIC_API_KEY: 'k' })
  assert.equal(red.PATH, '/usr/bin')
  assert.equal(red.CLAUDE_CODE_OAUTH_TOKEN, '***')
  assert.equal(red.ANTHROPIC_API_KEY, '***')
})

test('SECRET_KEYS 覆盖四个凭证变量', () => {
  assert.deepEqual([...SECRET_KEYS].sort(), [
    'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'MINIMAX_CN_API_KEY',
  ])
})

test('createJail: 目录名中性，不含 jail/inject/probe', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const base = path.basename(dir)
    assert.match(base, /^skill-harness-/)
    assert.doesNotMatch(base, /jail|inject|probe/i)
    assert.ok(await fs.pathExists(dir))
  } finally {
    await cleanup()
  }
})

test('createJail: cleanup 之后目录消失', async () => {
  const { dir, cleanup } = await createJail()
  await cleanup()
  assert.equal(await fs.pathExists(dir), false)
})

test('readEnvFile: 解析 KEY=VALUE，忽略注释与空行，去掉引号', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const p = path.join(dir, '.env')
    await fs.writeFile(p, '# comment\n\nFOO=bar\nQUOTED="baz"\nSINGLE=\'qux\'\nWITH_EQ=a=b\n')
    const env = readEnvFile(p)
    assert.equal(env.FOO, 'bar')
    assert.equal(env.QUOTED, 'baz')
    assert.equal(env.SINGLE, 'qux')
    assert.equal(env.WITH_EQ, 'a=b')
    assert.equal(env['# comment'], undefined)
  } finally {
    await cleanup()
  }
})

test('readEnvFile: 文件不存在返回空对象', () => {
  assert.deepEqual(readEnvFile('/nonexistent/path/.env'), {})
})

import { claudeAdapter } from '../../tools/skill-harness/adapters/claude.js'

test('claude: jailEnv 重定向 HOME 与 CLAUDE_CONFIG_DIR', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: { PATH: '/usr/bin' }, oauthToken: 'tok' })
  assert.equal(env.HOME, '/tmp/h')
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/h/.claude')
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'tok')
  assert.equal(env.PATH, '/usr/bin')
})

test('claude: jailEnv 不透传宿主的 CLAUDECODE 等变量', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: { CLAUDECODE: '1', CLAUDE_CONFIG_DIR: '/real' }, oauthToken: 't' })
  assert.equal(env.CLAUDECODE, undefined)
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/h/.claude')
})

test('claude: 走第三方端点时用 baseUrl + apiKey 而非 oauth', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: {}, baseUrl: 'https://x/anthropic', apiKey: 'k' })
  assert.equal(env.ANTHROPIC_BASE_URL, 'https://x/anthropic')
  assert.equal(env.ANTHROPIC_API_KEY, 'k')
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, undefined)
})

test('claude: install 把 skill 复制进 jail 的 .claude/skills/，返回空 args', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const extraArgs = await claudeAdapter.install({ jailDir: dir, skillPath: 'tools/skill-harness/probe/probe-anchor' })
    assert.deepEqual(extraArgs, [])
    assert.ok(await fs.pathExists(path.join(dir, '.claude/skills/probe-anchor/SKILL.md')))
    assert.ok(await fs.pathExists(path.join(dir, '.claude/skills/probe-anchor/references/token.md')))
  } finally {
    await cleanup()
  }
})

test('claude: args 含 --setting-sources user 与 stream-json', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: null, positional: 'go', sessionId: 'sid' })
  assert.ok(a.includes('-p'))
  assert.ok(a.includes('--setting-sources'))
  assert.equal(a[a.indexOf('--setting-sources') + 1], 'user')
  assert.ok(a.includes('--output-format'))
  assert.equal(a[a.indexOf('--output-format') + 1], 'stream-json')
  assert.ok(a.includes('--verbose'))
  assert.equal(a[a.indexOf('--model') + 1], 'M')
  assert.equal(a[a.indexOf('--session-id') + 1], 'sid')
  assert.equal(a[a.length - 1], 'go')
})

test('claude: systemAppend 为 null 时不出现 --append-system-prompt', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: null, positional: 'go', sessionId: 's' })
  assert.ok(!a.includes('--append-system-prompt'))
})

test('claude: systemAppend 非空时紧跟其值', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: 'COMP', positional: 'go', sessionId: 's' })
  assert.equal(a[a.indexOf('--append-system-prompt') + 1], 'COMP')
})

test('claude: collect 返回 null——过程数据在 stdout 里', () => {
  assert.equal(claudeAdapter.collect(), null)
})
