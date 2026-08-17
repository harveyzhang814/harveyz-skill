import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildGradePrompt } from '../../tools/skill-harness/grade/prompt.js'

const EVAL_REPLY_ONLY = {
  id: 1, prompt: '分析这个 skill',
  assertions: [{ id: 'zh-body', text: '主体使用中文', source: 'reply' }],
}

const EVAL_ARTIFACT = {
  id: 2, prompt: '写一份交接',
  assertions: [
    { id: 'zh-body', text: '主体使用中文', source: 'reply' },
    { id: 'has-anchor', text: '文档含最小验收锚点章节', source: 'artifact' },
  ],
}

const MATERIALS = {
  reply: '已完成，文档在 docs/commute/x.md',
  artifacts: [{ path: 'docs/commute/x.md', content: '# 交接\n## 最小验收锚点\n...' }],
  transcript: '{"type":"tool_use","name":"Write"}',
}

test('prompt 必须给 grader 一个说「判不了」的出口——不给出口，被迫二选一的 grader 会编证据', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: MATERIALS })
  assert.ok(p.includes('unavailable'))
  assert.ok(/不要猜/.test(p))
})

test('要求 evidence 引原文而非复述——复述出来的证据无法核对', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: MATERIALS })
  assert.ok(/原文/.test(p))
})

test('全是 reply 级断言时不塞产出物和轨迹——source 是成本闸门，塞了就白花钱', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: { ...MATERIALS, reply: '已完成' } })
  assert.ok(!p.includes('docs/commute/x.md'))
  assert.ok(!p.includes('tool_use'))
  assert.ok(p.includes('已完成'))
})

test('有一条 artifact 级断言就把产出物一起喂——层级取最高，不是逐条各喂一份', () => {
  const p = buildGradePrompt({ evalDef: EVAL_ARTIFACT, materials: MATERIALS })
  assert.ok(p.includes('docs/commute/x.md'))
  assert.ok(p.includes('最小验收锚点'))
  assert.ok(!p.includes('tool_use'), 'transcript 未被任何断言声明，不该出现')
})

test('材料缺失时显式写「缺失」而不是留空——留空 grader 会以为材料就长这样', () => {
  const p = buildGradePrompt({
    evalDef: EVAL_ARTIFACT,
    materials: { reply: null, artifacts: [], transcript: null },
  })
  assert.ok(p.includes('(缺失)'))
})

test('每条断言的 id 都出现在 prompt 里——grader 要按 id 回填，对不上就没法归位', () => {
  const p = buildGradePrompt({ evalDef: EVAL_ARTIFACT, materials: MATERIALS })
  assert.ok(p.includes('zh-body'))
  assert.ok(p.includes('has-anchor'))
})
