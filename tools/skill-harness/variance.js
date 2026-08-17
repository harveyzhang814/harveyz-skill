// 同一格重复跑，看的是 grader 的判定稳不稳，不是被测方稳不稳。
// 不一致时**不取多数决**：多数决会把「尺子在漂」粉饰成一个确定结论，
// 而这正是标定要暴露的东西。不稳的处置是换指标，不是加样本。
export function aggregateVerdicts(gradings) {
  const groups = new Map()
  for (const g of gradings ?? []) {
    for (const a of g.assertions ?? []) {
      const key = JSON.stringify([g.skill, g.platform, g.mode, g.evalId, a.id])
      if (!groups.has(key)) {
        groups.set(key, {
          skill: g.skill, platform: g.platform, mode: g.mode,
          evalId: g.evalId, assertionId: a.id, verdicts: [],
        })
      }
      groups.get(key).verdicts.push(a.verdict)
    }
  }

  return [...groups.values()].map(grp => {
    const unstable = new Set(grp.verdicts).size > 1
    return { ...grp, unstable, verdict: unstable ? 'unstable' : grp.verdicts[0] }
  })
}
