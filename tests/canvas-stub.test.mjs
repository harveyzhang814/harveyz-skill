import test from 'node:test'
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, rmSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const SETUP = resolve(root, 'skills/coding/handoff/evals/fixtures/canvas-stub/setup.sh')

// 跑 setup.sh，解析 stdout 的 STUB_BIN / STUB_LOG / WORKTREE 三行；
// cleanup 删掉 setup.sh 里 mktemp -d 建出的整个临时目录（即 STUB_BIN 的上一级，bin 的父目录）。
function setup(mode) {
  const r = spawnSync('bash', [SETUP, mode], { encoding: 'utf8' })
  assert.equal(r.status, 0, r.stderr)
  const vars = Object.fromEntries(
    r.stdout.split('\n').filter(l => /^(STUB_BIN|STUB_LOG|WORKTREE)=/.test(l)).map(l => {
      const i = l.indexOf('=')
      return [l.slice(0, i), l.slice(i + 1)]
    }),
  )
  assert.deepEqual(Object.keys(vars).sort(), ['STUB_BIN', 'STUB_LOG', 'WORKTREE'])
  const dir = dirname(vars.STUB_BIN)
  // 防御：只删确认是 setup.sh 生成的目录（里面有 mode 文件），绝不误删 TMPDIR 之类的上层目录
  assert.ok(existsSync(resolve(dir, 'mode')), `unexpected STUB_BIN: ${vars.STUB_BIN}`)
  return { ...vars, dir, cleanup: () => rmSync(dir, { recursive: true, force: true }) }
}

// handoff 的完整性门禁（validate-handoff.sh）要求 source_node / target_node 是合法 uuid，桩返回的 id 必须过这一关
const UUID = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/

const ctl = (env, ...args) =>
  spawnSync(resolve(env.STUB_BIN, 'agent-canvas-ctl'), args, { encoding: 'utf8' })

test('routed mode answers the routing commands and logs every call', () => {
  const env = setup('routed')
  try {
    const list = ctl(env, 'list-node-route-categories')
    assert.equal(list.status, 0)
    const cats = JSON.parse(list.stdout).categories.map(c => c.name)
    assert.ok(cats.includes('develop') && cats.includes('think'))

    const desc = ctl(env, 'describe-node-route-category', 'develop')
    assert.equal(desc.status, 0)
    assert.equal(JSON.parse(desc.stdout).category.name, 'develop')

    const create = ctl(env, 'create-routed-pty-node', '--title', 'T 1', '--category', 'develop', '--params', 'scale=small')
    assert.equal(create.status, 0)
    assert.equal(JSON.parse(create.stdout).decision.category, 'develop')
    assert.match(JSON.parse(create.stdout).nodeId, UUID)

    const lines = readFileSync(env.STUB_LOG, 'utf8').split('\n').filter(Boolean)
    assert.equal(lines.length, 3)
    assert.ok(lines[2].startsWith('agent-canvas-ctl create-routed-pty-node'), lines[2])
    assert.ok(lines[2].includes('T\\ 1'), `args should be printf %q quoted: ${lines[2]}`)
  } finally {
    env.cleanup()
  }
})

test('old-app mode rejects routing commands like an App without them', () => {
  const env = setup('old-app')
  try {
    for (const args of [
      ['list-node-route-categories'],
      ['describe-node-route-category', 'develop'],
      ['create-routed-pty-node', '--category', 'develop'],
    ]) {
      const r = ctl(env, ...args)
      assert.equal(r.status, 1, args[0])
      assert.ok(r.stderr.startsWith('未知子命令: '), `${args[0]}: ${r.stderr}`)
    }
    const plain = ctl(env, 'create-pty-node', '--title', 'x')
    assert.equal(plain.status, 0)
    assert.match(JSON.parse(plain.stdout).nodeId, UUID)
  } finally {
    env.cleanup()
  }
})

test('reject-once mode rejects the first routed create with INVALID_ARGUMENT then accepts', () => {
  const env = setup('reject-once')
  try {
    assert.match(JSON.parse(ctl(env, 'whoami').stdout).id, UUID)
    const first = ctl(env, 'create-routed-pty-node', '--category', 'develop')
    assert.equal(first.status, 1)
    assert.ok(first.stderr.startsWith('INVALID_ARGUMENT'), first.stderr)
    const second = ctl(env, 'create-routed-pty-node', '--category', 'develop')
    assert.equal(second.status, 0)
    assert.match(JSON.parse(second.stdout).nodeId, UUID)
  } finally {
    env.cleanup()
  }
})

test('setup prints a worktree on feature/slugify-numbers with the test plan committed', () => {
  const env = setup('routed')
  try {
    const git = (...a) => spawnSync('git', ['-C', env.WORKTREE, ...a], { encoding: 'utf8' })
    assert.equal(git('branch', '--show-current').stdout.trim(), 'feature/slugify-numbers')
    const files = git('ls-files').stdout.split('\n')
    assert.ok(files.includes('docs/superpowers/specs/2026-11-11-slugify-numbers-test-plan.md'))
    assert.ok(files.includes('src/slugify.js'))
  } finally {
    env.cleanup()
  }
})

test('unknown mode exits 2', () => {
  const r = spawnSync('bash', [SETUP, 'bogus'], { encoding: 'utf8' })
  assert.equal(r.status, 2)
})
