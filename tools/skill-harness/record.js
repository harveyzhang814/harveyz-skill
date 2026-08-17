// stderr 保留尾部而非头部：退出码单独看没有诊断价值，
// 要拼上 stderr 尾部才知道子进程为什么死。
export const STDERR_LIMIT = 16 * 1024

export function tailBytes(s, limit = STDERR_LIMIT) {
  if (typeof s !== 'string') return ''
  return s.length <= limit ? s : s.slice(s.length - limit)
}

// 抓不到的字段显式标 null 并进 unavailable，不假装有。
// unavailable 对应 QM 的 residual：没有 residual 的归因表一定在撒谎。
export function makeRecord({
  platform, skill, skillName, contentHash, task, repeat, mode, evalId,
  requestedModel, durationMs, exitCode, stderr, parsed, harvest,
}) {
  const p = parsed ?? {}
  const unavailable = []

  const triggered = mode === 'inject' ? null : (p.triggered ?? null)
  if (mode !== 'inject' && triggered === null) unavailable.push('triggered')

  for (const field of ['toolCalls', 'turns', 'usage', 'model', 'reply']) {
    if (p[field] === null || p[field] === undefined) unavailable.push(field)
  }

  const shortName = (skillName ?? skill ?? '').split('/').pop()
  const builtinSkillFloor = Array.isArray(p.visibleSkills)
    ? p.visibleSkills.filter(n => n !== shortName && n !== skillName && n !== skill).length
    : null
  if (builtinSkillFloor === null) unavailable.push('builtinSkillFloor')

  return {
    platform, skill, task, repeat, mode,
    evalId: evalId ?? null,
    contentHash: contentHash ?? null,
    sessionId: p.sessionId ?? null,
    model: p.model ?? null,
    provider: p.provider ?? null,
    modelMismatch: Boolean(p.model && requestedModel && p.model !== requestedModel),
    builtinSkillFloor,
    reply: p.reply ?? null,
    triggered,
    toolCalls: p.toolCalls ?? null,
    turns: p.turns ?? null,
    usage: p.usage ?? null,
    durationMs,
    exitCode,
    stderr: tailBytes(stderr ?? ''),
    transcriptTruncated: Boolean(harvest?.truncated),
    harvestErrors: harvest?.errors ?? [],
    unavailable,
  }
}
