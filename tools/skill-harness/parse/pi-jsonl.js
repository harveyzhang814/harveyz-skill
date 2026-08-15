// 纯函数。pi --mode json 输出 JSONL。
// 与 claude 的关键差异：pi 没有 Skill 工具，skill 通过模型自己 read SKILL.md 加载。

function lines(raw) {
  const out = []
  for (const l of raw.split('\n')) {
    const t = l.trim()
    if (!t) continue
    try {
      out.push(JSON.parse(t))
    } catch {
      // 非法行跳过
    }
  }
  return out
}

function textOf(message) {
  return (message?.content ?? [])
    .filter(b => b.type === 'text')
    .map(b => b.text)
    .join('')
    .trim()
}

export function parsePiJsonl(raw, { skillDir } = {}) {
  const events = lines(raw)
  const session = events.find(e => e.type === 'session')
  const messageEnds = events.filter(e => e.type === 'message_end')
  const last = messageEnds[messageEnds.length - 1]

  const ends = new Map()
  for (const e of events) {
    if (e.type === 'tool_execution_end') ends.set(e.toolCallId, e)
  }

  const toolCalls = []
  for (const e of events) {
    if (e.type !== 'tool_execution_start') continue
    const end = ends.get(e.toolCallId)
    toolCalls.push({
      name: e.toolName,
      args: e.args ?? {},
      ok: end ? end.isError !== true : true,
      seq: toolCalls.length,
    })
  }

  const skillMd = skillDir ? `${skillDir.replace(/\/$/, '')}/SKILL.md` : null
  const triggered = Boolean(skillMd) && toolCalls.some(
    t => t.name === 'read' && typeof t.args?.path === 'string' && t.args.path.endsWith(skillMd),
  )

  const u = last?.message?.usage
  const usage = u
    ? {
        input: u.input ?? 0,
        output: u.output ?? 0,
        cacheRead: u.cacheRead ?? 0,
        cacheWrite: u.cacheWrite ?? 0,
        totalTokens: u.totalTokens ?? 0,
        costUsd: u.cost?.total ?? null,
      }
    : null

  return {
    sessionId: session?.id ?? null,
    model: last?.message?.model ?? null,
    provider: last?.message?.provider ?? null,
    reply: last ? textOf(last.message) : null,
    triggered,
    toolCalls,
    turns: events.filter(e => e.type === 'turn_start').length || null,
    usage,
    visibleSkills: null,
    isError: null,
  }
}
