// 纯函数。不碰进程、不碰文件系统、不读 process.env。
// hermes 的 `sessions export --format trace` 也输出这个格式，故两平台共用。

function lines(raw) {
  const out = []
  for (const l of raw.split('\n')) {
    const t = l.trim()
    if (!t) continue
    try {
      out.push(JSON.parse(t))
    } catch {
      // 非法行跳过：上游偶发的非 JSON 噪声不该让整次运行报废
    }
  }
  return out
}

export function parseClaudeCodeJsonl(raw, { skillName } = {}) {
  const events = lines(raw)
  const system = events.find(e => e.type === 'system')
  const result = events.find(e => e.type === 'result')

  const toolCalls = []
  for (const e of events) {
    if (e.type !== 'assistant') continue
    for (const block of e.message?.content ?? []) {
      if (block.type !== 'tool_use') continue
      toolCalls.push({ name: block.name, args: block.input ?? {}, ok: true, seq: toolCalls.length })
    }
  }

  // 空集合是"不知道"，不是"没触发"：零个可解析事件说明这次运行本身没抓到东西，
  // 不能拿空数组算出一个自信的 false 来冒充"确实没触发"。
  const noEvents = events.length === 0
  const triggered = noEvents ? null : toolCalls.some(t => t.name === 'Skill' && t.args?.skill === skillName)

  const u = result?.usage
  const usage = u
    ? {
        input: u.input_tokens ?? 0,
        output: u.output_tokens ?? 0,
        cacheRead: u.cache_read_input_tokens ?? 0,
        cacheWrite: u.cache_creation_input_tokens ?? 0,
        totalTokens: (u.input_tokens ?? 0) + (u.output_tokens ?? 0) + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0),
        costUsd: result.total_cost_usd ?? null,
      }
    : null

  return {
    sessionId: system?.session_id ?? result?.session_id ?? null,
    model: system?.model ?? null,
    provider: null,   // claude 的输出不带 provider；显式 null 保证与 pi 解析器形状一致
    reply: result?.result ?? null,
    triggered,
    toolCalls: noEvents ? null : toolCalls,
    turns: result?.num_turns ?? null,
    usage,
    visibleSkills: system?.skills ?? null,
    isError: result?.is_error ?? null,
  }
}
