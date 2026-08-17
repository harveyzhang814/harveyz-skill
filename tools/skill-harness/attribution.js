// report.js（cell 级）和 quality-report.js（断言级）两份报告都要交代
// 「模型不匹配」和「哪些字段判不了」——这两条事实不该因为报告格式不同就各写一份，
// 分叉了就可能只在一份里改对、另一份漏改。
export function modelMismatchLines(records) {
  const mism = records.filter(r => r.modelMismatch)
  if (!mism.length) return []
  return ['', `model mismatch (${mism.length}): ${mism.map(r => `${r.skill}@${r.platform}`).join(', ')}`]
}

export function unavailableFieldLines(records) {
  const un = records.filter(r => r.unavailable?.length)
  if (!un.length) return []
  const lines = ['', 'unavailable fields:']
  for (const r of un) lines.push(`  ${r.skill}@${r.platform}/${r.mode}: ${r.unavailable.join(', ')}`)
  return lines
}
