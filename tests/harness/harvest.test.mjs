import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import {
  snapshot, diffSnapshots, capTranscript, cellDirName,
  TRANSCRIPT_LIMIT, HARNESS_FILES,
} from '../../tools/skill-harness/harvest.js'

test('差集只留 agent 真正写的东西——跑之前就在的内置 skill 副本不该被当成产出物', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, '.claude/skills/builtin/SKILL.md'), 'pre-existing')
  const before = await snapshot(dir)

  await fs.outputFile(path.join(dir, 'Documents/notes/report.md'), 'agent wrote this')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['Documents/notes/report.md'])
  await fs.remove(dir)
})

test('内容变了但大小相同的文件也要被认出来——只比 size 会漏掉原地改写', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  const f = path.join(dir, 'a.txt')
  await fs.outputFile(f, 'aaaa')
  const before = await snapshot(dir)
  await new Promise(r => setTimeout(r, 10))
  await fs.outputFile(f, 'bbbb')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['a.txt'])
  await fs.remove(dir)
})

test('harness 自己写的 stdout.log 不是 agent 的产出物，必须排除', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, 'stdout.log'), '')
  const before = await snapshot(dir)
  await fs.outputFile(path.join(dir, 'stdout.log'), 'lots of output')
  await fs.outputFile(path.join(dir, 'out.md'), 'agent')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['out.md'])
  assert.ok(HARNESS_FILES.has('stdout.log'))
  await fs.remove(dir)
})

test('transcript 截断了必须说——把不完整的原料当完整的用，比没有原料更危险', () => {
  const raw = 'x'.repeat(TRANSCRIPT_LIMIT + 100)
  const { text, truncated } = capTranscript(raw)
  assert.equal(truncated, true)
  assert.equal(text.length, TRANSCRIPT_LIMIT)

  const small = capTranscript('short')
  assert.equal(small.truncated, false)
  assert.equal(small.text, 'short')
})

test('cell 目录名把 skill 路径里的斜杠压掉——否则会在 cells/ 下建出意外的子目录层级', () => {
  assert.equal(
    cellDirName({ skill: 'mint/learn-skill', platform: 'pi', mode: 'native', repeat: 0 }),
    'mint-learn-skill__pi__native__r0',
  )
  assert.equal(
    cellDirName({ skill: 'a/b', platform: 'claude', mode: 'inject' }),
    'a-b__claude__inject__r0',
  )
})
