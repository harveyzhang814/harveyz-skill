export function stripFrontmatter(md) {
  if (!md.startsWith('---')) return md
  const end = md.indexOf('\n---', 3)
  if (end === -1) return md
  const after = md.indexOf('\n', end + 1)
  return after === -1 ? '' : md.slice(after + 1).replace(/^\n+/, '')
}

// 实测：缺这一行，claude / pi / hermes 三平台在 inject 模式下一律读不到
// skill 的同目录附属文件（FILE=UNREACHABLE）。这不是可选补偿。
export function anchorLine(skillDir) {
  return `This skill directory is: ${skillDir}`
}

export function buildPrompt({ mode, injection, skillBody, skillDir, compensation, task }) {
  if (mode !== 'native' && mode !== 'inject') throw new Error(`unknown mode: ${mode}`)

  const head = []
  if (compensation) head.push(compensation)
  if (mode === 'inject') {
    head.push(anchorLine(skillDir))
    head.push(skillBody)
  }

  if (injection === 'prompt-only') {
    if (mode === 'native') {
      const parts = head.length ? [head.join('\n\n'), task] : [task]
      return { systemAppend: null, positional: parts.join('\n\n') }
    }
    // inject mode
    const parts = head.length ? [head.join('\n\n'), '---', task] : [task]
    return { systemAppend: null, positional: parts.join('\n') }
  }

  return { systemAppend: head.length ? head.join('\n\n') : null, positional: task }
}
