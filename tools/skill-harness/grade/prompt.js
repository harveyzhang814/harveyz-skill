import { sourceIncludes, maxSourceLevel } from '../declarations.js'

// 「判不了」必须是个真出口。不给出口，被迫在 pass/fail 里二选一的 grader
// 会编出看起来很可信的证据——那比缺一格数据危险得多。
const HEADER = `你是判定器。逐条判定下面每一条断言，只依据「材料」一节给出的内容。

规则：
- 每条断言独立判定，不要用某一条的材料去推断另一条。
- 材料不足以判定某一条时，该条 verdict 输出 "unavailable"，并在 evidence 里写明缺什么。不要猜。
- evidence 必须引用材料中的原文片段，不要复述、不要概括。
- 只输出 JSON，不要输出任何其他文字。

输出格式：
{"assertions":[{"id":"<断言 id>","verdict":"pass|fail|unavailable","evidence":"<原文片段，或缺失说明>"}]}`

export function buildGradePrompt({ evalDef, materials }) {
  const parts = [HEADER, '', '## 断言', '']
  for (const a of evalDef.assertions) {
    parts.push(`- id: ${a.id}`)
    parts.push(`  ${a.text}`)
  }

  parts.push('', '## 材料', '', '### 交给被测方的任务', evalDef.prompt ?? '(缺失)')
  parts.push('', '### 被测方的回复', materials.reply ?? '(缺失)')

  const level = maxSourceLevel(evalDef.assertions)

  if (sourceIncludes(level, 'artifact')) {
    parts.push('', '### 被测方产出的文件')
    if (!materials.artifacts?.length) parts.push('(缺失)')
    for (const f of materials.artifacts ?? []) {
      parts.push('', `--- ${f.path} ---`, f.content)
    }
  }

  if (sourceIncludes(level, 'transcript')) {
    parts.push('', '### 执行轨迹', materials.transcript ?? '(缺失)')
  }

  return parts.join('\n')
}
