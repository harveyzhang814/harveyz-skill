// 模板语法：行内参数 @{name}；独占一行的条件指令 <!-- @if name --> / <!-- @else --> / <!-- @endif -->。
// 条件单层，不可嵌套。{{name}} 不属于本语法，原样保留。

const DIRECTIVE = /^<!-- @(if \w+|else|endif) -->$/
const PARAM = /@\{(\w+)\}/g

export class TemplateError extends Error {
  constructor(file, line, detail) {
    super(`${file}:${line}: ${detail}`)
    this.name = 'TemplateError'
    this.file = file
    this.line = line
  }
}

// 逐行扫描，状态：块外(null) / if 分支('if') / else 分支('else')。
// 对每个非指令行回调 onLine(text, branch)，branch 为 null 或 { state, cond }；对每个引用的参数名回调 onParam(name, lineNo)。
// 被丢弃分支里的参数引用同样校验，保证错误与参数取值无关。
function scan(text, file, onParam, onLine) {
  let state = null
  let cond = null
  let openLine = 0
  text.split('\n').forEach((raw, i) => {
    const no = i + 1
    const m = DIRECTIVE.exec(raw)
    if (m) {
      const [word, name] = m[1].split(' ')
      if (word === 'if') {
        if (state) throw new TemplateError(file, no, '@if 不可嵌套')
        state = 'if'; cond = name; openLine = no
        onParam(name, no)
      } else if (word === 'else') {
        if (state !== 'if') throw new TemplateError(file, no, '多余的 @else')
        state = 'else'
      } else {
        if (!state) throw new TemplateError(file, no, '多余的 @endif')
        state = null; cond = null
      }
      return
    }
    for (const p of raw.matchAll(PARAM)) onParam(p[1], no)
    onLine(raw, state && { state, cond })
  })
  if (state) throw new TemplateError(file, openLine, '@if 未闭合')
}

export function templateParams(text, file) {
  const names = new Set()
  scan(text, file, n => names.add(n), () => {})
  return [...names]
}

export function renderTemplate(text, params, file) {
  const out = []
  const known = n => Object.prototype.hasOwnProperty.call(params, n)
  scan(text, file, (n, no) => {
    if (!known(n)) throw new TemplateError(file, no, `未知参数 ${n}`)
  }, (raw, branch) => {
    if (branch) {
      const truthy = Boolean(params[branch.cond])
      if ((branch.state === 'if') !== truthy) return
    }
    out.push(raw.replace(PARAM, (_, n) => String(params[n])))
  })
  return out.join('\n').replace(/\n{3,}/g, '\n\n')
}
