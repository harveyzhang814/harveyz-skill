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

// 两条 eval 的声明——专门用来暴露"一个 record 只产出一份 grading"这条不变式：
// 老代码 `for (const evalDef of decl.evals ?? [])` 不看 record 到底是为哪个
// evalId 跑的，会把声明里全部 eval 的断言都扣到同一条 record 上。
const DECL_MULTI = {
  skill_name: 'x',
  evals: [
    { id: 1, prompt: 'do A', frozen: '2026-08-17', assertions: [{ id: 'a', text: 'A', source: 'artifact' }] },
    { id: 2, prompt: 'do B', frozen: '2026-08-17', assertions: [{ id: 'b', text: 'B', source: 'artifact' }] },
  ],
}

test('只评上游 pass 的格子——上游装不上就没有可判的东西，不是质量差', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 },
    { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 1, reply: null, evalId: 1 },
    { skill: 'a/x', platform: 'hermes', mode: 'native', repeat: 0, exitCode: 0, reply: null, evalId: 1 },
  ]
  const cells = selectGradeCells({ records, declarations: new Map([['a/x', DECL]]) })
  assert.equal(cells.length, 1)
  assert.equal(cells[0].platform, 'claude')
})

test('没有声明的 skill 不评，也不报错——按需增量下这是常态', () => {
  const records = [{ skill: 'a/y', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }]
  const cells = selectGradeCells({ records, declarations: new Map() })
  assert.deepEqual(cells, [])
})

test('record.evalId 在声明里找不到对应的 eval（比如声明后来把它删了）就跳过，不瞎判成别的场景', () => {
  const records = [{ skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 99 }]
  const cells = selectGradeCells({ records, declarations: new Map([['a/x', DECL]]) })
  assert.deepEqual(cells, [])
})

// 回归本任务要修的缺陷：一个 record 只产出一份 grading，不是按声明里的 eval
// 数量翻倍——两条 record 分别为 evalId 1、2 跑的，selectGradeCells 必须各自
// 只找回它自己对应的那个 evalDef，产出恰好 2 份 grading（等于 record 数），
// 不是 2 record × 2 eval = 4 份。把这处改动还原（selectGradeCells 改回
// `for (const evalDef of decl.evals ?? [])`），这条测试必须失败——
// 那才是「revert 后必须失败」的判据本身。
test('selectGradeCells：grading 数量等于 record 数，不是 record 数 × 声明的 eval 数——一个 record 只判它自己实际运行的那个 eval 场景', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok A', evalId: 1 },
    { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok B', evalId: 2 },
  ]
  const cells = selectGradeCells({ records, declarations: new Map([['a/x', DECL_MULTI]]) })
  assert.equal(cells.length, records.length)
  assert.equal(cells.find(c => c.platform === 'claude').evalDef.id, 1)
  assert.equal(cells.find(c => c.platform === 'pi').evalDef.id, 2)
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
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
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
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
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

test('invoke 抛异常不炸掉整轮——已判完的格子必须留在 gradings.json 里', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const recA = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
  const recB = { skill: 'a/x', platform: 'hermes', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
  await fs.writeJson(path.join(runDir, 'records.json'), [recA, recB])

  let calls = 0
  const invoke = async () => {
    calls++
    // 前两次调用（第一个格子的首次 + 重试）都抛异常，模拟 keychain 中途失效；
    // 第三次调用（第二个格子）恢复正常，返回真实判定。
    if (calls <= 2) throw new Error(`keychain unreadable (attempt ${calls})`)
    return '{"assertions":[{"id":"a","verdict":"pass","evidence":"真实材料"}]}'
  }

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(out.gradings.length, 2)
  assert.equal(out.gradings[0].platform, 'claude')
  assert.equal(out.gradings[0].assertions[0].verdict, 'unavailable')
  assert.match(out.gradings[0].assertions[0].evidence, /keychain unreadable/)
  assert.equal(out.gradings[1].platform, 'hermes')
  assert.equal(out.gradings[1].assertions[0].verdict, 'pass')
  assert.equal(out.gradings[1].assertions[0].evidence, '真实材料')
  await fs.remove(runDir)
})

test('pi 的 artifact 断言即使 grader 判 pass 也被强制改判 unavailable——artifactChannel 为 none 时产出物出不了 jail，不能信任 grader 自证材料齐全', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
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

// I2：harvestErrors 记录的是「这次没能采到材料」的原料事故，不是被测方的
// 质量问题——凡是断言依赖那份缺失原料，必须强制改判 unavailable，不能指望
// grader 自己老实报「材料不足」（这与上面 artifactChannel 覆盖是同一类问题）。
const DECL_TWO_SOURCES = {
  skill_name: 'x',
  evals: [{ id: 1, prompt: 'do it', frozen: '2026-08-17',
    assertions: [
      { id: 'a', text: 'A', source: 'artifact' },
      { id: 'b', text: 'B', source: 'reply' },
    ] }],
}

test('I2：record.harvestErrors 含 artifact 采集失败时，source 为 artifact 的断言被强制改判 unavailable，即使 grader 判了 pass', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = {
    skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1,
    harvestErrors: ['artifact a.md: ENOENT'],
  }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"pass","evidence":"看起来不错"},{"id":"b","verdict":"pass","evidence":"回复本身没问题"}]}'

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL_TWO_SOURCES]]),
  })

  const assertions = out.gradings[0].assertions
  assert.equal(assertions.find(a => a.id === 'a').verdict, 'unavailable')
  assert.match(assertions.find(a => a.id === 'a').evidence, /ENOENT/)
  // 不依赖失败原料的 reply 级断言不受影响——过度覆盖跟这次修的缺陷同样糟
  assert.equal(assertions.find(a => a.id === 'b').verdict, 'pass')
  await fs.remove(runDir)
})

test('I2：harvestErrors 为空数组或字段缺失时行为不变——不误伤没有采集问题的格子', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const recEmpty = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1, harvestErrors: [] }
  await fs.writeJson(path.join(runDir, 'records.json'), [recEmpty])

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"pass","evidence":"AAA"},{"id":"b","verdict":"pass","evidence":"BBB"}]}'

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL_TWO_SOURCES]]),
  })

  assert.equal(out.gradings[0].assertions.find(a => a.id === 'a').verdict, 'pass')
  assert.equal(out.gradings[0].assertions.find(a => a.id === 'b').verdict, 'pass')
  await fs.remove(runDir)
})

// I5：--only 只重跑部分 skill 时，其余 skill 已经花钱评出的判定不能被整体
// 覆盖抹掉——那会让报告把「测了、被删了」显示成「没测过」，两者对使用者的
// 意义完全不同。
test('I5：--only 重跑单个 skill 时，其余 skill 已有的 gradings 原样保留，只有 --only 命中的 skill 被换成新判定', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const priorGradings = {
    runId: 'r1', graderModel: 'old-grader', subjectModel: 'old-subj',
    gradings: [
      { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, evalId: 1, frozen: null,
        assertions: [{ id: 'a', verdict: 'pass', evidence: '旧判定 A' }] },
      { skill: 'b/y', platform: 'claude', mode: 'native', repeat: 0, evalId: 1, frozen: null,
        assertions: [{ id: 'a', verdict: 'fail', evidence: '旧判定 B' }] },
    ],
  }
  await fs.writeJson(path.join(runDir, 'gradings.json'), priorGradings)

  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"fail","evidence":"新判定 A"}]}'

  const out = await runGrade({
    runDir, graderModel: 'grader-m', only: ['a/x'], invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  const bGrading = out.gradings.find(g => g.skill === 'b/y')
  assert.deepEqual(bGrading, priorGradings.gradings[1], 'b/y 未被 --only 命中，内容必须原样保留')
  const aGrading = out.gradings.find(g => g.skill === 'a/x')
  assert.equal(aGrading.assertions[0].verdict, 'fail')
  assert.equal(aGrading.assertions[0].evidence, '新判定 A')
  await fs.remove(runDir)
})

test('I5：没传 only（全量跑）时行为不变——旧文件内容被完全覆盖，只剩这次跑出来的', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const priorGradings = {
    runId: 'r1', graderModel: 'old-grader', subjectModel: 'old-subj',
    gradings: [
      { skill: 'b/y', platform: 'claude', mode: 'native', repeat: 0, evalId: 1, frozen: null,
        assertions: [{ id: 'a', verdict: 'fail', evidence: '旧判定 B' }] },
    ],
  }
  await fs.writeJson(path.join(runDir, 'gradings.json'), priorGradings)

  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1 }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"pass","evidence":"新判定 A"}]}'

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(out.gradings.length, 1)
  assert.equal(out.gradings[0].skill, 'a/x')
  await fs.remove(runDir)
})

// I6：subjectModel 取自并发 worker 乱序 push 的 records，谁先跑完谁说了算——
// 选哪条 record 不该是随机的，必须按稳定 key 排序后再取，与数组原始顺序无关。
test('I6：subjectModel 与 records 数组的原始顺序无关——两份顺序不同但内容相同的数组算出同一个 subjectModel', async () => {
  const runDir1 = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const runDir2 = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))

  const recA = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 1, reply: null, evalId: 1, model: null }
  const recB = { skill: 'a/x', platform: 'hermes', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1, model: 'subj-m' }
  const recC = { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok', evalId: 1, model: 'subj-m-2' }

  // 顺序一：worker 完成顺序 A, B, C（A 的 model 是 null，模拟采集失败没拿到 model）
  await fs.writeJson(path.join(runDir1, 'records.json'), [recA, recB, recC])
  // 顺序二：worker 完成顺序 C, A, B——内容完全相同，仅数组顺序不同
  await fs.writeJson(path.join(runDir2, 'records.json'), [recC, recA, recB])

  const invoke = async () => '{"assertions":[{"id":"a","verdict":"pass","evidence":"x"}]}'
  const declarations = new Map([['a/x', DECL]])

  const out1 = await runGrade({ runDir: runDir1, graderModel: 'grader-m', invoke, declarations })
  const out2 = await runGrade({ runDir: runDir2, graderModel: 'grader-m', invoke, declarations })

  assert.equal(out1.subjectModel, out2.subjectModel)
  // 按 stableRecordKey 排序后，claude（A，model null）< hermes（B）< pi（C）——
  // 排序后第一个"有 model"的记录是 B，不是数组原始顺序的第一个（recA/recC）
  assert.equal(out1.subjectModel, 'subj-m')
  await fs.remove(runDir1); await fs.remove(runDir2)
})
