import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const RULE = [
  '### 计划后交接给执行模型',
  '先询问用户“本会话执行，还是交接给其他执行方”',
  '`REQUIRED SUB-SKILL` 填为 `superpowers:subagent-driven-development` 并提交计划',
  '各 Task 的测试与计划写定的断言一致，并全部通过',
  '不得修改接口签名、测试名称与断言、`Global Constraints`',
]

for (const file of ['AGENTS.md', 'CLAUDE.md']) {
  test(`${file} carries the plan handoff rule and the unified worktree path`, async () => {
    const body = await read(file)
    for (const phrase of [...RULE, '`manage-worktree`', '`.worktrees/<分支名，/ 换成 +>`']) assert.ok(body.includes(phrase), `${file}: ${phrase}`)
  })
}

test('old worktree recipes are gone from repo instructions', async () => {
  assert.ok(!(await read('AGENTS.md')).includes('`.claude/worktrees/` 是本仓库现有的路径约定'))
  assert.ok(!(await read('CLAUDE.md')).includes('git worktree add .claude/worktrees/feature+<slug>'))
})

test('handoff config no longer tells the receiver to re-plan', async () => {
  const body = await read('.hskill/handoff/config.md')
  assert.doesNotMatch(body, /writing-plans|executing-plans/)
  assert.ok(body.includes('计划由交出方在交接前用 develop-plan 写好并经用户确认'))
  assert.ok(body.includes('manage-worktree'))
  assert.ok(body.includes('.worktrees/<分支名，/ 换成 +>'))
  assert.ok(!body.includes('EnterWorktree(path'))
})
