import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  SOURCE_LEVELS, sourceIncludes, maxSourceLevel,
  validateDeclaration, isFrozen, loadDeclaration,
} from '../../tools/skill-harness/declarations.js'

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

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

// I10：loadDeclaration 过去读完 JSON 直接返回，validateDeclaration 只在
// 测试里被调用过——格式错误的 evals.json（比如漏了某条 assertion 的 id）
// 会被原样吃进 selectCells/selectGradeCells/renderQualityReport，字段
// 该有的地方变成 undefined，报告上印出字面量 "undefined"，而不是在加载
// 的第一时间报错拒绝。
test('I10：loadDeclaration 对格式不合法的 evals.json（assertion 缺 id）必须抛错，且错误信息复用 validateDeclaration 的文案', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'decl-test-'))
  const skillPath = path.join(root, 'skills', 'test', 'bad-skill', 'evals')
  await fs.ensureDir(skillPath)
  await fs.writeJson(path.join(skillPath, 'evals.json'), {
    skill_name: 'bad-skill',
    evals: [{ id: 1, assertions: [{ text: '缺 id 的断言' }] }],
  })

  await assert.rejects(
    () => loadDeclaration(root, 'test/bad-skill'),
    err => {
      assert.match(err.message, /bad-skill/)
      assert.match(err.message, /assertion 缺 id/) // 复用 validateDeclaration 产出的原句，不是重新拼一句不一致的文案
      return true
    },
  )

  await fs.remove(root)
})

test('I10：loadDeclaration 对格式正确的 evals.json 正常返回，不抛错——回归，确认没把正常路径改坏', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'decl-test-'))
  const skillPath = path.join(root, 'skills', 'test', 'good-skill', 'evals')
  await fs.ensureDir(skillPath)
  const evalData = { skill_name: 'good-skill', evals: [{ id: 1, assertions: [{ id: 'a', text: 't' }] }] }
  await fs.writeJson(path.join(skillPath, 'evals.json'), evalData)

  const loaded = await loadDeclaration(root, 'test/good-skill')
  assert.deepEqual(loaded, evalData)

  await fs.remove(root)
})

test('仓库里每一份 evals.json 都必须合法——这是防止声明跟着 skill 一起腐烂的闸门', async () => {
  const skillsDir = path.join(REPO_ROOT, 'skills')
  const found = []
  for (const cat of await fs.readdir(skillsDir)) {
    const catDir = path.join(skillsDir, cat)
    if (!(await fs.stat(catDir)).isDirectory()) continue
    for (const name of await fs.readdir(catDir)) {
      const file = path.join(catDir, name, 'evals/evals.json')
      if (await fs.pathExists(file)) found.push({ file, skillPath: path.join(catDir, name) })
    }
  }

  assert.ok(found.length >= 4, `预期至少 4 份 evals.json，实际找到 ${found.length}`)
  for (const { file, skillPath } of found) {
    const errs = validateDeclaration(await fs.readJson(file), skillPath)
    assert.deepEqual(errs, [], `${path.relative(REPO_ROOT, file)}:\n  ${errs.join('\n  ')}`)
  }
})
