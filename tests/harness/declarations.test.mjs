import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import {
  SOURCE_LEVELS, sourceIncludes, maxSourceLevel,
  validateDeclaration, isFrozen, loadDeclaration,
} from '../../tools/skill-harness/declarations.js'

test('source 是累进层级不是互斥集合——artifact 含 reply，否则同时要两者的断言得拆成两条', () => {
  assert.equal(sourceIncludes('artifact', 'reply'), true)
  assert.equal(sourceIncludes('transcript', 'artifact'), true)
  assert.equal(sourceIncludes('transcript', 'reply'), true)
  assert.equal(sourceIncludes('reply', 'artifact'), false)
  assert.equal(sourceIncludes('artifact', 'transcript'), false)
  assert.deepEqual(SOURCE_LEVELS, ['reply', 'artifact', 'transcript'])
})

test('取最高层级——一条要 transcript 就得喂 transcript，其余条不必各喂一份', () => {
  assert.equal(maxSourceLevel([{ source: 'reply' }, { source: 'transcript' }, { source: 'artifact' }]), 'transcript')
  assert.equal(maxSourceLevel([{ source: 'reply' }, {}]), 'reply')
  assert.equal(maxSourceLevel([]), 'reply')
})

test('skill_name 与目录名不符要报错——learn-skill 那份写成 inspect-skill 就是没有这道闸门的结果', () => {
  const errs = validateDeclaration({ skill_name: 'inspect-skill', evals: [] }, 'skills/mint/learn-skill')
  assert.equal(errs.length, 1)
  assert.match(errs[0], /inspect-skill/)
  assert.match(errs[0], /learn-skill/)
})

test('裸字符串断言要报错——没有稳定 id 就无法跨 runId 对齐行', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: ['报告要有四个维度'] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /裸字符串/)
})

test('同一 eval 内 id 重复要报错——重复 id 会让两条断言在矩阵里抢同一行', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: [{ id: 'a', text: 't' }, { id: 'a', text: 'u' }] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /重复/)
})

test('未知 source 要报错，不静默当成 reply', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: [{ id: 'a', text: 't', source: 'stdout' }] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /stdout/)
})

test('合法声明零错误', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, frozen: '2026-08-17', assertions: [{ id: 'a', text: 't', source: 'artifact' }] }] },
    'skills/a/x',
  )
  assert.deepEqual(errs, [])
})

test('未冻结的声明认得出来——冻结前不得据其下平台结论', () => {
  assert.equal(isFrozen({ frozen: '2026-08-17' }), true)
  assert.equal(isFrozen({}), false)
  assert.equal(isFrozen({ frozen: '' }), false)
})

test('断言 id 在不同 eval 中可以重复——seen 在 eval 循环内声明，只需同一 eval 内唯一', () => {
  const errs = validateDeclaration(
    {
      skill_name: 'extract-cognition',
      evals: [
        { id: 0, assertions: [{ id: 'every_move_has_anchor', text: 't1' }, { id: 'moves_are_transferable', text: 't2' }] },
        { id: 1, assertions: [{ id: 'every_move_has_anchor', text: 't3' }, { id: 'generator_section_present', text: 't4' }] },
      ],
    },
    'skills/research/extract-cognition',
  )
  assert.deepEqual(errs, [])
})

test('loadDeclaration 从磁盘加载合法 JSON——路径不存在时返回 null 而非抛出', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'decl-test-'))
  const skillPath = path.join(root, 'skills', 'test', 'skill-name', 'evals')
  await fs.ensureDir(skillPath)
  const evalData = { skill_name: 'skill-name', evals: [{ id: 1, assertions: [] }] }
  await fs.writeJson(path.join(skillPath, 'evals.json'), evalData)

  const loaded = await loadDeclaration(root, 'test/skill-name')
  assert.deepEqual(loaded, evalData)

  await fs.remove(root)
})

test('loadDeclaration 缺失文件返回 null——让 grader 跳过无声明的 skill', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'decl-test-'))

  const result = await loadDeclaration(root, 'nonexistent/skill')
  assert.equal(result, null)

  await fs.remove(root)
})
