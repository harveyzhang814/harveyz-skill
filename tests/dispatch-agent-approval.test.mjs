import test from 'node:test'
import assert from 'node:assert/strict'
import { readSkill, indexEntry, contentHash } from './helpers/skillIndex.mjs'

const SKILL = 'skills/agent-canvas/dispatch-agent/SKILL.md'

test('dispatch-agent version and index hash are 1.1.0', async () => {
  const body = await readSkill(SKILL)
  const entry = await indexEntry('agent-canvas/dispatch-agent')
  assert.match(body, /^version: ["']?1\.1\.0["']?$/m)
  assert.equal(entry.contentVersion, '1.1.0')
  assert.equal(entry.contentHash, contentHash(body))
})

test('dispatch-agent approval follows collaboration relations', async () => {
  const body = await readSkill(SKILL)
  const lines = body.split('\n')
  assert.ok(!body.includes('子节点'))
  assert.ok(!body.includes('直接创建'))
  assert.ok(
    lines.some(l => l.includes('waits-for') && l.includes('hands-off-to') && l.includes('始终允许') && l.includes('active')),
    '放行条件（active 的 waits-for / hands-off-to、始终允许）写在同一行'
  )
  assert.ok(lines.some(l => l.includes('不再影响审批') && l.includes('你建')), '是不是你建的不影响审批')
  assert.ok(lines.some(l => l.includes('waits-for') && l.includes('发送前') && l.includes('不强制')), '等待关系发送前连、skill 不强制')
})

test('dispatch-agent spawn depth resets at human-initiated creation', async () => {
  const lines = (await readSkill(SKILL)).split('\n')
  assert.ok(lines.some(l => l.includes('agent 发起') && l.includes('人发起') && l.includes('重新计数')), '只数 agent 发起、人发起处重新计数')
  assert.ok(lines.some(l => l.includes('人发起') && l.includes('Fork') && l.includes('/branch')), '人发起举例')
  assert.ok(lines.some(l => l.includes('第 4 代及以后') && l.includes('建节点本身') && l.includes('审批')), '第 4 代及以后建节点弹审批')
})
