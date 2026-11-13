import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile, access } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const read = p => readFile(resolve(root, p), 'utf8')
const RULE = [
  '### 计划后交接给执行模型',
  '先询问用户“本会话执行，还是交接给其他执行方”',
  '交出方按 develop-plan 的条件（执行方为全新会话）选定执行技能，填入计划开头的 `REQUIRED SUB-SKILL` 并提交计划',
  '交接文档写明所选技能及理由',
  '各 Task 的测试与计划写定的断言一致，并全部通过',
  '不得修改接口签名、测试名称与断言、`Global Constraints`',
  '执行技能要求的自行裁决只适用于上述不可修改项以外的问题；涉及不可修改项的冲突，包括任务审查者提出的，一律停止并打回',
]

test('AGENTS.md carries the plan handoff rule and the unified worktree path', async () => {
  const body = await read('AGENTS.md')
  for (const phrase of [...RULE, '`manage-worktree`', '`.worktrees/<分支名，/ 换成 +>`']) assert.ok(body.includes(phrase), phrase)
  assert.ok(!body.includes('填为 `superpowers:subagent-driven-development`'), 'hard-coded execution skill')
  assert.doesNotMatch(body, /develop-plan`? ?第 ?\d+ ?步/, 'hard-coded develop-plan step number')
})

test('AGENTS.md is the only repo instruction file', async () => {
  await assert.rejects(access(resolve(root, 'CLAUDE.md')), { code: 'ENOENT' })
})

test('old worktree recipes are gone from repo instructions', async () => {
  const body = await read('AGENTS.md')
  assert.ok(!body.includes('`.claude/worktrees/` 是本仓库现有的路径约定'))
  assert.ok(!body.includes('git worktree add .claude/worktrees/feature+<slug>'))
})

test('handoff config no longer tells the receiver to re-plan', async () => {
  const body = await read('.hskill/handoff/config.md')
  assert.doesNotMatch(body, /writing-plans|executing-plans/)
  assert.ok(body.includes('计划由交出方在交接前用 develop-plan 写好并经用户确认'))
  assert.ok(body.includes('manage-worktree'))
  assert.ok(body.includes('.worktrees/<分支名，/ 换成 +>'))
  assert.ok(!body.includes('EnterWorktree(path'))
})
