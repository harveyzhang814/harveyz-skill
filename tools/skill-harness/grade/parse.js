export const VERDICTS = new Set(['pass', 'fail', 'unavailable'])

const TAIL = 400
export const EVIDENCE_LIMIT = 2000

function tail(s) {
  const str = String(s ?? '')
  return str.length <= TAIL ? str : str.slice(str.length - TAIL)
}

// grader 常自作主张加 ```json 围栏或前后寒暄，这里只负责把 JSON 那段抠出来。
export function extractJson(raw) {
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(raw ?? '')
  if (fenced) return fenced[1].trim()
  const s = String(raw ?? '')
  const start = s.indexOf('{')
  const end = s.lastIndexOf('}')
  if (start === -1 || end <= start) throw new Error('no JSON object found')
  return s.slice(start, end + 1)
}

function allUnavailable(assertions, reason) {
  return assertions.map(a => ({ id: a.id, verdict: 'unavailable', evidence: reason }))
}

// 输出顺序恒等于声明顺序：矩阵行顺序必须稳定，不能由 grader 的心情决定。
// 声明里没有的 id 一律丢弃——量具无权给自己加行。
export function parseGraderOutput(raw, assertions) {
  let doc
  try {
    doc = JSON.parse(extractJson(raw))
  } catch (e) {
    return { ok: false, assertions: allUnavailable(assertions, `grader output unparseable (${e.message}): ${tail(raw)}`) }
  }

  const byId = new Map((doc?.assertions ?? []).map(a => [a?.id, a]))
  const out = assertions.map(decl => {
    const got = byId.get(decl.id)
    if (!got) return { id: decl.id, verdict: 'unavailable', evidence: 'grader 未给出该条判定' }
    if (!VERDICTS.has(got.verdict)) {
      return { id: decl.id, verdict: 'unavailable', evidence: `grader 返回了非法 verdict "${got.verdict}"` }
    }
    const evidence = String(got.evidence ?? '')
    return { id: decl.id, verdict: got.verdict, evidence: evidence.length <= EVIDENCE_LIMIT ? evidence : evidence.slice(0, EVIDENCE_LIMIT) }
  })

  return { ok: true, assertions: out }
}
