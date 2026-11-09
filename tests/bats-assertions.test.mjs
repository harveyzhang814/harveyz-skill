// bats 跑在 macOS 自带的 bash 3.2 上：失败的 [[ ]] 只要不是测试的最后一条命令，就不会让
// 测试失败（bash < 4.1 的 errexit 不认复合命令 [[ ]]）。这里扫描所有在用的 bats 文件，
// 要求断言行上的每个 [[ ]] 都带 `|| false`，防止再写出永远不生效的断言。
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, existsSync } from 'node:fs'
import { resolve, dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function batsFiles() {
  const files = readdirSync(join(root, 'tests')).filter(f => f.endsWith('.bats')).map(f => join(root, 'tests', f))
  for (const group of readdirSync(join(root, 'skills'), { withFileTypes: true })) {
    if (!group.isDirectory() || group.name === 'archived') continue
    const groupDir = join(root, 'skills', group.name)
    for (const skill of readdirSync(groupDir, { withFileTypes: true }).filter(d => d.isDirectory())) {
      const testsDir = join(groupDir, skill.name, 'tests')
      if (!existsSync(testsDir)) continue
      for (const f of readdirSync(testsDir)) if (f.endsWith('.bats')) files.push(join(testsDir, f))
    }
  }
  return files
}

// 返回不带 `|| false` 的断言行（跳过 heredoc 正文）
export function ineffectiveAssertions(text) {
  const hits = []
  let term = null
  text.split('\n').forEach((line, i) => {
    if (term) {
      if (line.trim() === term) term = null
      return
    }
    const here = line.match(/<<-?\s*['"]?(\w+)['"]?/)
    if (here) term = here[1]
    if (/^\s+\[/.test(line) && /\]\](?! \|\| false)\s*(;|$)/.test(line)) hits.push(`${i + 1}: ${line.trim()}`)
  })
  return hits
}

test('the detector flags a bare [[ ]] assertion and accepts one guarded by || false', () => {
  assert.deepEqual(ineffectiveAssertions('  [[ "$output" == *x* ]]\n  true'), ['1: [[ "$output" == *x* ]]'])
  assert.deepEqual(ineffectiveAssertions('  [ "$status" -eq 0 ]; [[ "$output" == *x* ]] || false'), [])
  assert.deepEqual(ineffectiveAssertions('cat <<EOF\n  [[ inside heredoc ]]\nEOF'), [])
})

test('every [[ ]] assertion in active bats files is guarded by || false', () => {
  const offenders = []
  for (const file of batsFiles()) {
    for (const hit of ineffectiveAssertions(readFileSync(file, 'utf8'))) offenders.push(`${relative(root, file)}:${hit}`)
  }
  assert.deepEqual(offenders, [])
})
