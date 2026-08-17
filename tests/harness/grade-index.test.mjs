import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { selectGradeCells, readMaterials, runGrade } from '../../tools/skill-harness/grade/index.js'
import { cellDirName } from '../../tools/skill-harness/harvest.js'

const DECL = {
  skill_name: 'x',
  evals: [{ id: 1, prompt: 'do it', frozen: '2026-08-17',
    assertions: [{ id: 'a', text: 'A', source: 'artifact' }] }],
}

test('只评上游 pass 的格子——上游装不上就没有可判的东西，不是质量差', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' },
    { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 1, reply: null },
    { skill: 'a/x', platform: 'hermes', mode: 'native', repeat: 0, exitCode: 0, reply: null },
  ]
  const cells = selectGradeCells({ records, declarations: new Map([['a/x', DECL]]) })
  assert.equal(cells.length, 1)
  assert.equal(cells[0].platform, 'claude')
})

test('没有声明的 skill 不评，也不报错——按需增量下这是常态', () => {
  const records = [{ skill: 'a/y', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }]
  const cells = selectGradeCells({ records, declarations: new Map() })
  assert.deepEqual(cells, [])
})

test('读材料时缺产出物不抛错——采集失败的格子要能一路走到 unavailable', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'transcript.jsonl'), '{"t":1}')
  const m = await readMaterials(dir, 'artifact')
  assert.deepEqual(m.artifacts, [])
  await fs.remove(dir)
})

test('产出物按相对路径读全，内容与路径一起交给 grader', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'artifacts/docs/a.md'), 'AAA')
  const m = await readMaterials(dir, 'artifact')
  assert.equal(m.artifacts.length, 1)
  assert.equal(m.artifacts[0].path, 'docs/a.md')
  assert.equal(m.artifacts[0].content, 'AAA')
  await fs.remove(dir)
})

test('reply 级不读产出物和轨迹——成本闸门要在读盘这一层就生效', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'artifacts/a.md'), 'AAA')
  await fs.outputFile(path.join(dir, 'transcript.jsonl'), 'T')
  const m = await readMaterials(dir, 'reply')
  assert.deepEqual(m.artifacts, [])
  assert.equal(m.transcript, null)
  await fs.remove(dir)
})

test('grader 首次输出坏掉时重试一次；两次都坏才判 unavailable', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])
  await fs.outputFile(path.join(runDir, 'cells', cellDirName(rec), 'artifacts/a.md'), 'AAA')

  let calls = 0
  const invoke = async () => {
    calls++
    return calls === 1 ? '不是 JSON' : '{"assertions":[{"id":"a","verdict":"pass","evidence":"AAA"}]}'
  }

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(calls, 2)
  assert.equal(out.gradings[0].assertions[0].verdict, 'pass')
  await fs.remove(runDir)
})

test('两次都解析失败就判 unavailable，且 gradings.json 头部记下 grader 模型', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke: async () => '始终不是 JSON',
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(out.graderModel, 'grader-m')
  assert.equal(out.gradings[0].assertions[0].verdict, 'unavailable')
  assert.ok(await fs.pathExists(path.join(runDir, 'gradings.json')))
  await fs.remove(runDir)
})

test('pi 的 artifact 断言即使 grader 判 pass 也被强制改判 unavailable——artifactChannel 为 none 时产出物出不了 jail，不能信任 grader 自证材料齐全', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])
  // 故意不写 artifacts 目录：pi 平台本来就拿不到产出物，材料恒为空

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"pass","evidence":"看起来不错"}]}'

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(out.gradings[0].assertions[0].verdict, 'unavailable')
  assert.match(out.gradings[0].assertions[0].evidence, /artifactChannel/)
  await fs.remove(runDir)
})
