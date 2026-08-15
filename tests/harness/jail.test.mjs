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
