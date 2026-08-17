# Skill 跨平台 Harness · 质量评估 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 harness 能回答「同一个 skill 在三个平台上跑出来，哪一条质量断言不一样」，而不只是「装得上吗」。

**Architecture:** 三段接力。run 阶段在 jail 被删之前把 transcript 与 agent 产出文件捞到 `~/.hskill/skill-harness/<runId>/cells/<cell>/`；grade 阶段离线读这些落盘产物，用 `claude -p` 跑一个独立 pin 模型的 grader，逐条断言产出三态 `verdict`；report 阶段渲染断言 × 平台矩阵。grade 不信任 run 的内存，report 不信任 grader 的自我报告。

**Tech Stack:** Node.js ESM（`type: module`）、`fs-extra`、`node:test` + `node:assert/strict`。无新依赖。

**Spec:** [../specs/2026-08-17-skill-harness-quality-eval-design.md](../specs/2026-08-17-skill-harness-quality-eval-design.md)

## Global Constraints

- **三态纪律**：`unavailable` 不得渲染成 `0`，不得渲染成 `✓`；`not-run` 渲染成空格。没有 residual 的归因表一定在撒谎。
- **计数去重**：`blocked-upstream` 按 `(skill, platform, mode)` 计一次，绝不按断言条数计。
- **不存 `pass_rate`**，不存任何合成比率。
- **模型必须 pin**：`--grader-model` 必填，无默认值，不得回落到平台默认。
- **采集故障不得判成 fail**：采集不到 → 记明 → 相关断言判 `unavailable`。
- **测试文件位置** `tests/harness/*.test.mjs`，被 `npm test` 的 `node --test tests/harness/*.test.mjs` 自动收集，无需注册。
- **测试名写「为什么」**，跟随现有 `tests/harness/report.test.mjs` 的中文惯例，不写 `test('renders correctly')`。
- **commit message**：Conventional Commits，类型限 `feat|fix|chore|docs|refactor|test|style|perf`，**首行 ≤ 80 字符**（hook 强制）。
- **分支**：全部提交落在当前分支 `doc/harness-quality-eval-design`，不新建分支，不 merge 到 staging。

---

## File Structure

**新建：**

| 文件 | 职责 |
|---|---|
| `tools/skill-harness/harvest.js` | jail 文件快照、差集、transcript 截断、落盘到 cell 目录 |
| `tools/skill-harness/declarations.js` | 加载与校验 `evals.json` 新格式；`source` 累进层级判定 |
| `tools/skill-harness/grade/prompt.js` | 组装 grader prompt，按 `source` 决定塞什么材料 |
| `tools/skill-harness/grade/parse.js` | 解析 grader 输出，失败路径产出全 `unavailable` |
| `tools/skill-harness/grade/index.js` | grade 编排：选格、调用、重试、写 `gradings.json` |
| `tools/skill-harness/variance.js` | 按 repeat 聚合 verdict，标 `unstable` |
| `tools/skill-harness/quality-report.js` | 断言级矩阵渲染 |

**修改：**

| 文件 | 改动 |
|---|---|
| `tools/skill-harness/profiles.js` | 三个 profile 各加 `artifactChannel` 字段 |
| `tools/skill-harness/adapters/pi.js:12` | `jailEnv` 重定向 HOME |
| `tools/skill-harness/runner.js:106-157` | `runOne` 接入 harvest，在 `finally` 之前 |
| `tools/skill-harness/record.js:12` | `makeRecord` 接收并记录 `harvest` 结果 |
| `tools/skill-harness/cli.js` | 新增 `grade` 命令与 `--grader-model` / `--only` 旗标 |
| `skills/{mint/learn-skill,coding/handoff,research/extract-cognition,coding/setup-debug}/evals/evals.json` | 迁移到新格式 |

**测试：** `tests/harness/{harvest,declarations,grade-prompt,grade-parse,variance,quality-report}.test.mjs`

---

## Task 1: pi 的 HOME 重定向与 `artifactChannel`

采集层的前置。pi 目前不重定向 HOME，而仓库约定 skill 把产出写到 `$HOME/.hskill/` 和 `~/Documents/notes/`——pi 会写进真实 HOME，既污染用户环境，产出物也不在 jail 里。

`artifactChannel` 编码"这个平台的产出物捞不捞得到"，让 pi 认证失败时有一条诚实的降级路径，而不是让 pi 列静默变 fail。它必须有生产消费者（Task 8 与 Task 10 消费），否则会腐烂成谎言。

**Files:**
- Modify: `tools/skill-harness/profiles.js`
- Modify: `tools/skill-harness/adapters/pi.js:12`
- Test: `tests/harness/profile.test.mjs`（已存在，追加）

**Interfaces:**
- Consumes: 无
- Produces: `piProfile.artifactChannel` / `claudeProfile.artifactChannel` / `hermesProfile.artifactChannel`，取值 `'jail' | 'none'`

- [ ] **Step 1: 写失败测试**

追加到 `tests/harness/profile.test.mjs`：

```js
import { PROFILES } from '../../tools/skill-harness/profiles.js'
import { piAdapter } from '../../tools/skill-harness/adapters/pi.js'

test('每个 profile 都要声明 artifactChannel——捞不捞得到产出物决定质量断言能不能判', () => {
  for (const p of PROFILES) {
    assert.ok(['jail', 'none'].includes(p.artifactChannel), `${p.id} 缺 artifactChannel`)
  }
})

test('pi 必须重定向 HOME——否则 skill 的产出会写进真实 HOME，既污染环境又采不到', () => {
  const env = piAdapter.jailEnv({ jailDir: '/tmp/jail-x', source: { PATH: '/usr/bin', HOME: '/Users/real' } })
  assert.equal(env.HOME, '/tmp/jail-x')
  assert.notEqual(env.HOME, '/Users/real')
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/profile.test.mjs`
Expected: FAIL —— `pi 缺 artifactChannel`，以及 `env.HOME` 为 `undefined`

- [ ] **Step 3: 加 `artifactChannel` 到三个 profile**

在 `tools/skill-harness/profiles.js` 中，为每个 profile 对象加一行（放在 `transcriptFormat` 之后）：

```js
  artifactChannel: 'jail',
```

三个 profile（`claudeProfile`、`piProfile`、`hermesProfile`）都先设为 `'jail'`。Step 6 的实测若判定 pi 认证不通，再把 `piProfile` 改成 `'none'`。

- [ ] **Step 4: 改 pi 的 `jailEnv` 重定向 HOME**

把 `tools/skill-harness/adapters/pi.js` 的 `jailEnv` 整个替换为：

```js
  // 仓库约定 skill 把产出写到 $HOME/.hskill/ 与 ~/Documents/notes/。
  // 不重定向 HOME，pi 跑的 skill 会写进真实 HOME——既污染用户环境，
  // 产出物也不在 jail 里，质量断言无从判起。
  jailEnv({ jailDir, source = {} }) {
    return buildEnv(source, { HOME: jailDir })
  },
```

- [ ] **Step 5: 跑测试确认通过**

Run: `node --test tests/harness/profile.test.mjs`
Expected: PASS

- [ ] **Step 6: 实测 pi 在重定向 HOME 下能否认证**

Run:

```bash
node tools/skill-harness/cli.js run --platform pi --mode native \
  --model MiniMax-M2.7 --provider minimax-cn --skill mint/learn-skill
```

读输出里 pi 那一格：`exitCode` 为 0 且 `reply` 非空 → 认证通过，`artifactChannel: 'jail'` 保持。
`exitCode` 非 0 或 stderr 含认证类错误 → 认证不通，执行 Step 7。

- [ ] **Step 7: 仅当 Step 6 判定认证不通时执行——降级**

把 `adapters/pi.js` 的 `jailEnv` 改回 `return buildEnv(source, {})`，把 `piProfile.artifactChannel` 改成 `'none'`，删掉 Step 1 里那条 HOME 断言测试，并把这条测试换成：

```js
test('pi 未重定向 HOME，故 artifactChannel 为 none——产出物类断言对 pi 只能判 unavailable', () => {
  assert.equal(piProfile.artifactChannel, 'none')
})
```

同时更新 spec 未确认项汇总表中 pi 那一行的档位，从「没查」改为「已查，认证不通」。

- [ ] **Step 8: 提交**

```bash
git add tools/skill-harness/profiles.js tools/skill-harness/adapters/pi.js tests/harness/profile.test.mjs
git commit -m "feat(harness): pi 重定向 HOME，profile 声明 artifactChannel"
```

---

## Task 2: harvest.js 的纯函数部分

快照、差集、transcript 截断。全部是纯函数或只读 I/O，独立可测。

差集而非启发式是关键：内置 skill 副本、session 目录、认证文件在跑之前就存在，快照里有它们，差集自然排除。但 harness 自己写的 `stdout.log` / `stderr.log` 在跑之前就创建、跑的过程中被写入，会出现在差集里——必须显式排除，否则它们会被当成 agent 的产出物。

**Files:**
- Create: `tools/skill-harness/harvest.js`
- Test: `tests/harness/harvest.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `snapshot(dir): Promise<Map<string, string>>` —— 相对路径 → `"<mtimeMs>:<size>"`
  - `diffSnapshots(before: Map, after: Map): string[]` —— 变化的相对路径，已排序、已排除 harness 自身文件
  - `capTranscript(raw: string, limit?: number): { text: string, truncated: boolean }`
  - `cellDirName({ skill, platform, mode, repeat }): string`
  - `TRANSCRIPT_LIMIT: number`
  - `HARNESS_FILES: Set<string>`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/harvest.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import {
  snapshot, diffSnapshots, capTranscript, cellDirName,
  TRANSCRIPT_LIMIT, HARNESS_FILES,
} from '../../tools/skill-harness/harvest.js'

test('差集只留 agent 真正写的东西——跑之前就在的内置 skill 副本不该被当成产出物', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, '.claude/skills/builtin/SKILL.md'), 'pre-existing')
  const before = await snapshot(dir)

  await fs.outputFile(path.join(dir, 'Documents/notes/report.md'), 'agent wrote this')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['Documents/notes/report.md'])
  await fs.remove(dir)
})

test('内容变了但大小相同的文件也要被认出来——只比 size 会漏掉原地改写', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  const f = path.join(dir, 'a.txt')
  await fs.outputFile(f, 'aaaa')
  const before = await snapshot(dir)
  await new Promise(r => setTimeout(r, 10))
  await fs.outputFile(f, 'bbbb')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['a.txt'])
  await fs.remove(dir)
})

test('harness 自己写的 stdout.log 不是 agent 的产出物，必须排除', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-test-'))
  await fs.outputFile(path.join(dir, 'stdout.log'), '')
  const before = await snapshot(dir)
  await fs.outputFile(path.join(dir, 'stdout.log'), 'lots of output')
  await fs.outputFile(path.join(dir, 'out.md'), 'agent')
  const after = await snapshot(dir)

  assert.deepEqual(diffSnapshots(before, after), ['out.md'])
  assert.ok(HARNESS_FILES.has('stdout.log'))
  await fs.remove(dir)
})

test('transcript 截断了必须说——把不完整的原料当完整的用，比没有原料更危险', () => {
  const raw = 'x'.repeat(TRANSCRIPT_LIMIT + 100)
  const { text, truncated } = capTranscript(raw)
  assert.equal(truncated, true)
  assert.equal(text.length, TRANSCRIPT_LIMIT)

  const small = capTranscript('short')
  assert.equal(small.truncated, false)
  assert.equal(small.text, 'short')
})

test('cell 目录名把 skill 路径里的斜杠压掉——否则会在 cells/ 下建出意外的子目录层级', () => {
  assert.equal(
    cellDirName({ skill: 'mint/learn-skill', platform: 'pi', mode: 'native', repeat: 0 }),
    'mint-learn-skill__pi__native__r0',
  )
  assert.equal(
    cellDirName({ skill: 'a/b', platform: 'claude', mode: 'inject' }),
    'a-b__claude__inject__r0',
  )
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/harvest.test.mjs`
Expected: FAIL —— `Cannot find module '.../harvest.js'`

- [ ] **Step 3: 实现 harvest.js 的纯函数部分**

创建 `tools/skill-harness/harvest.js`：

```js
import fs from 'fs-extra'
import path from 'node:path'

// 4 MB。超限截断而非丢弃：一份被截断且标明截断的原料，仍比没有原料有用。
export const TRANSCRIPT_LIMIT = 4 * 1024 * 1024

// harness 自己往 jail 里写的文件。它们在 spawn 之前就被创建、运行期间被写入，
// 必然出现在差集里——不排除就会被当成 agent 的产出物。
export const HARNESS_FILES = new Set([
  'stdout.log', 'stderr.log',
  'hermes-list-stdout.log', 'hermes-list-stderr.log',
  'hermes-export-stdout.log', 'hermes-export-stderr.log',
])

// 签名带 mtime 与 size 两项：只比 size 会漏掉「改写成等长内容」，
// 只比 mtime 会被时钟精度坑到。
export async function snapshot(dir) {
  const out = new Map()
  async function walk(cur) {
    let entries
    try {
      entries = await fs.readdir(cur, { withFileTypes: true })
    } catch {
      return
    }
    for (const e of entries) {
      const full = path.join(cur, e.name)
      if (e.isDirectory()) await walk(full)
      else if (e.isFile()) {
        try {
          const st = await fs.stat(full)
          out.set(path.relative(dir, full), `${st.mtimeMs}:${st.size}`)
        } catch {
          // 运行期间文件可能被删掉，忽略即可
        }
      }
    }
  }
  await walk(dir)
  return out
}

export function diffSnapshots(before, after) {
  const changed = []
  for (const [rel, sig] of after) {
    if (HARNESS_FILES.has(rel)) continue
    if (before.get(rel) !== sig) changed.push(rel)
  }
  return changed.sort()
}

export function capTranscript(raw, limit = TRANSCRIPT_LIMIT) {
  if (typeof raw !== 'string') return { text: '', truncated: false }
  if (raw.length <= limit) return { text: raw, truncated: false }
  return { text: raw.slice(0, limit), truncated: true }
}

export function cellDirName({ skill, platform, mode, repeat }) {
  return `${String(skill).replace(/\//g, '-')}__${platform}__${mode}__r${repeat ?? 0}`
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/harvest.test.mjs`
Expected: PASS，5 个 test 全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/harvest.js tests/harness/harvest.test.mjs
git commit -m "feat(harness): 采集层纯函数——快照差集与 transcript 截断"
```

---

## Task 3: harvestCell 落盘 + 接入 runner

把差集结果和 transcript 真正写到 `~/.hskill/skill-harness/<runId>/cells/<cell>/`，并在 `runner.js` 的 `finally` 之前调用。

时序是这个任务的全部要害：`runOne` 的 `finally` 一执行，`jail.js:34` 的 `fs.remove` 就把 jail 连同 agent 产出的文件删干净。采集必须在它之前完成。

**Files:**
- Modify: `tools/skill-harness/harvest.js`
- Modify: `tools/skill-harness/runner.js:106-157`
- Modify: `tools/skill-harness/record.js:12`
- Test: `tests/harness/harvest.test.mjs`（追加）
- Test: `tests/harness/record.test.mjs`（追加）

**Interfaces:**
- Consumes: Task 2 的 `capTranscript` / `cellDirName`
- Produces:
  - `harvestCell({ jailDir, destDir, raw, changedFiles }): Promise<{ truncated: boolean, errors: string[] }>`
  - `makeRecord` 新增入参 `harvest`，输出新增字段 `transcriptTruncated: boolean`、`harvestErrors: string[]`

- [ ] **Step 1: 写失败测试**

追加到 `tests/harness/harvest.test.mjs`：

```js
import { harvestCell } from '../../tools/skill-harness/harvest.js'

test('产出物按原相对路径落到 artifacts/ 下——扁平化会让同名文件互相覆盖', async () => {
  const jail = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-jail-'))
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))
  await fs.outputFile(path.join(jail, 'Documents/notes/a.md'), 'AAA')
  await fs.outputFile(path.join(jail, '.hskill/x/a.md'), 'BBB')

  const r = await harvestCell({
    jailDir: jail, destDir: dest, raw: '{"k":1}\n',
    changedFiles: ['Documents/notes/a.md', '.hskill/x/a.md'],
  })

  assert.deepEqual(r.errors, [])
  assert.equal(await fs.readFile(path.join(dest, 'artifacts/Documents/notes/a.md'), 'utf8'), 'AAA')
  assert.equal(await fs.readFile(path.join(dest, 'artifacts/.hskill/x/a.md'), 'utf8'), 'BBB')
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), '{"k":1}\n')
  await fs.remove(jail); await fs.remove(dest)
})

test('采集不到的文件记进 errors 而不是抛出——采集故障不得让整格运行失败', async () => {
  const jail = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-jail-'))
  const dest = await fs.mkdtemp(path.join(os.tmpdir(), 'harvest-dest-'))

  const r = await harvestCell({
    jailDir: jail, destDir: dest, raw: 'x',
    changedFiles: ['does/not/exist.md'],
  })

  assert.equal(r.errors.length, 1)
  assert.match(r.errors[0], /does\/not\/exist\.md/)
  assert.equal(await fs.readFile(path.join(dest, 'transcript.jsonl'), 'utf8'), 'x')
  await fs.remove(jail); await fs.remove(dest)
})
```

追加到 `tests/harness/record.test.mjs`：

```js
test('采集出错要进 record——采集故障若不记，会伪装成被测方的质量问题', () => {
  const rec = makeRecord({ ...BASE, harvest: { truncated: true, errors: ['artifact a.md: ENOENT'] } })
  assert.equal(rec.transcriptTruncated, true)
  assert.deepEqual(rec.harvestErrors, ['artifact a.md: ENOENT'])
})

test('没传 harvest 时字段有确定默认值，不是 undefined', () => {
  const rec = makeRecord(BASE)
  assert.equal(rec.transcriptTruncated, false)
  assert.deepEqual(rec.harvestErrors, [])
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/harvest.test.mjs tests/harness/record.test.mjs`
Expected: FAIL —— `harvestCell is not a function`；`rec.transcriptTruncated` 为 `undefined`

- [ ] **Step 3: 实现 harvestCell**

追加到 `tools/skill-harness/harvest.js` 末尾：

```js
// 每个错误单独 catch 并收集，不中断后续采集：
// 少捞到一个文件，剩下的仍有价值；抛出去则整格白跑。
export async function harvestCell({ jailDir, destDir, raw, changedFiles }) {
  const errors = []
  await fs.ensureDir(destDir)

  const { text, truncated } = capTranscript(raw)
  try {
    await fs.writeFile(path.join(destDir, 'transcript.jsonl'), text)
  } catch (e) {
    errors.push(`transcript: ${e.message}`)
  }

  for (const rel of changedFiles ?? []) {
    try {
      await fs.copy(path.join(jailDir, rel), path.join(destDir, 'artifacts', rel))
    } catch (e) {
      errors.push(`artifact ${rel}: ${e.message}`)
    }
  }

  return { truncated, errors }
}
```

- [ ] **Step 4: 改 record.js 接收 harvest**

在 `tools/skill-harness/record.js` 的 `makeRecord` 参数解构里，把 `requestedModel, durationMs, exitCode, stderr, parsed,` 那一行改成：

```js
  requestedModel, durationMs, exitCode, stderr, parsed, harvest,
```

在返回对象里，`stderr: tailBytes(stderr ?? ''),` 之后加两行：

```js
    transcriptTruncated: Boolean(harvest?.truncated),
    harvestErrors: harvest?.errors ?? [],
```

- [ ] **Step 5: 接入 runner.js**

在 `tools/skill-harness/runner.js` 顶部 import 区加：

```js
import { snapshot, diffSnapshots, harvestCell, cellDirName } from './harvest.js'
```

`runOne` 的签名改为接收 `runDir`：把 `async function runOne(cell, ctx) {` 改成 `async function runOne(cell, ctx, runDir) {`。

在 `const plan = planCell(cell, { ...ctx, jailDir })` 这一行**之后**、`const r = await runCaptured(...)` 之前插入：

```js
    const before = await snapshot(jailDir)
```

在 `const parsed = adapter.parse(raw, {...})` 这一行**之前**插入：

```js
    const after = await snapshot(jailDir)
    const harvest = await harvestCell({
      jailDir,
      destDir: path.join(runDir, 'cells', cellDirName({ ...cell, repeat: cell.repeat ?? 0 })),
      raw,
      changedFiles: diffSnapshots(before, after),
    })
```

在 `makeRecord({...})` 的入参里，`exitCode, stderr, parsed,` 改成：

```js
      exitCode, stderr, parsed, harvest,
```

- [ ] **Step 6: 改 runMatrix 先建 runDir 再跑**

把 `tools/skill-harness/runMatrix` 整个函数体替换为——注意 `runDir` 必须在 worker 启动**之前**算出并建好，否则 `runOne` 无处落盘：

```js
export async function runMatrix(cells, ctx) {
  const todo = cells.filter(c => c.state === 'run')
  const limit = ctx.concurrency ?? 3
  const id = ctx.runId ?? runId()
  const dir = artifactDir(id)
  await fs.ensureDir(dir)

  const records = []
  let i = 0
  async function worker() {
    while (i < todo.length) {
      const cell = todo[i++]
      records.push(await runOne(cell, ctx, dir))
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker))

  await fs.writeJson(path.join(dir, 'records.json'), records, { spaces: 2 })
  await fs.writeJson(path.join(dir, 'cells.json'), cells, { spaces: 2 })
  return { runId: id, dir, records }
}
```

- [ ] **Step 7: 跑测试确认通过**

Run: `node --test tests/harness/harvest.test.mjs tests/harness/record.test.mjs tests/harness/runner.test.mjs`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add tools/skill-harness/harvest.js tools/skill-harness/runner.js tools/skill-harness/record.js tests/harness/harvest.test.mjs tests/harness/record.test.mjs
git commit -m "feat(harness): jail 删除前捞出 transcript 与 agent 产出物"
```

---

## Task 4: declarations.js —— 新格式加载与校验

`source` 的累进层级是这个模块的核心：`artifact` 含 `reply`，`transcript` 含前两者。这样一条同时需要 reply 和产出物的断言不必拆成两条。

**Files:**
- Create: `tools/skill-harness/declarations.js`
- Test: `tests/harness/declarations.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `SOURCE_LEVELS: string[]` —— `['reply', 'artifact', 'transcript']`，顺序即层级
  - `sourceIncludes(declared: string, needed: string): boolean`
  - `maxSourceLevel(assertions: object[]): string`
  - `validateDeclaration(doc: object, skillPath: string): string[]` —— 错误消息数组，空数组表示合法
  - `loadDeclaration(repoRoot: string, skill: string): Promise<object|null>`
  - `isFrozen(evalDef: object): boolean`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/declarations.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  SOURCE_LEVELS, sourceIncludes, maxSourceLevel,
  validateDeclaration, isFrozen,
} from '../../tools/skill-harness/declarations.js'

test('source 是累进层级不是互斥集合——artifact 含 reply，否则同时要两者的断言得拆成两条', () => {
  assert.equal(sourceIncludes('artifact', 'reply'), true)
  assert.equal(sourceIncludes('transcript', 'artifact'), true)
  assert.equal(sourceIncludes('transcript', 'reply'), true)
  assert.equal(sourceIncludes('reply', 'artifact'), false)
  assert.equal(sourceIncludes('artifact', 'transcript'), false)
  assert.deepEqual(SOURCE_LEVELS, ['reply', 'artifact', 'transcript'])
})

test('取最高层级——一条要 transcript 就得喂 transcript，其余条不必各喂一份', () => {
  assert.equal(maxSourceLevel([{ source: 'reply' }, { source: 'transcript' }, { source: 'artifact' }]), 'transcript')
  assert.equal(maxSourceLevel([{ source: 'reply' }, {}]), 'reply')
  assert.equal(maxSourceLevel([]), 'reply')
})

test('skill_name 与目录名不符要报错——learn-skill 那份写成 inspect-skill 就是没有这道闸门的结果', () => {
  const errs = validateDeclaration({ skill_name: 'inspect-skill', evals: [] }, 'skills/mint/learn-skill')
  assert.equal(errs.length, 1)
  assert.match(errs[0], /inspect-skill/)
  assert.match(errs[0], /learn-skill/)
})

test('裸字符串断言要报错——没有稳定 id 就无法跨 runId 对齐行', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: ['报告要有四个维度'] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /裸字符串/)
})

test('同一 eval 内 id 重复要报错——重复 id 会让两条断言在矩阵里抢同一行', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: [{ id: 'a', text: 't' }, { id: 'a', text: 'u' }] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /重复/)
})

test('未知 source 要报错，不静默当成 reply', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, assertions: [{ id: 'a', text: 't', source: 'stdout' }] }] },
    'skills/a/x',
  )
  assert.equal(errs.length, 1)
  assert.match(errs[0], /stdout/)
})

test('合法声明零错误', () => {
  const errs = validateDeclaration(
    { skill_name: 'x', evals: [{ id: 1, frozen: '2026-08-17', assertions: [{ id: 'a', text: 't', source: 'artifact' }] }] },
    'skills/a/x',
  )
  assert.deepEqual(errs, [])
})

test('未冻结的声明认得出来——冻结前不得据其下平台结论', () => {
  assert.equal(isFrozen({ frozen: '2026-08-17' }), true)
  assert.equal(isFrozen({}), false)
  assert.equal(isFrozen({ frozen: '' }), false)
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/declarations.test.mjs`
Expected: FAIL —— `Cannot find module '.../declarations.js'`

- [ ] **Step 3: 实现 declarations.js**

创建 `tools/skill-harness/declarations.js`：

```js
import fs from 'fs-extra'
import path from 'node:path'

// 顺序即层级，不是集合：artifact 含 reply，transcript 含前两者。
// 这样「同时需要回复与产出物」的断言不必拆成两条，也不必把字段做成数组。
export const SOURCE_LEVELS = ['reply', 'artifact', 'transcript']

export function sourceIncludes(declared, needed) {
  return SOURCE_LEVELS.indexOf(declared) >= SOURCE_LEVELS.indexOf(needed)
}

export function maxSourceLevel(assertions) {
  let max = 'reply'
  for (const a of assertions ?? []) {
    const lv = a.source ?? 'reply'
    if (SOURCE_LEVELS.indexOf(lv) > SOURCE_LEVELS.indexOf(max)) max = lv
  }
  return max
}

export function isFrozen(evalDef) {
  return Boolean(evalDef?.frozen)
}

// 返回错误消息数组而非抛出：一次列全所有问题，迁移时能一遍改完。
export function validateDeclaration(doc, skillPath) {
  const errors = []
  const expected = path.basename(skillPath)
  if (doc?.skill_name !== expected) {
    errors.push(`skill_name "${doc?.skill_name}" 与目录名 "${expected}" 不符`)
  }
  for (const ev of doc?.evals ?? []) {
    const seen = new Set()
    for (const a of ev.assertions ?? []) {
      if (typeof a === 'string') {
        errors.push(`eval ${ev.id}: assertion 仍是裸字符串，缺稳定 id`)
        continue
      }
      if (!a.id) errors.push(`eval ${ev.id}: assertion 缺 id`)
      else if (seen.has(a.id)) errors.push(`eval ${ev.id}: assertion id 重复 "${a.id}"`)
      else seen.add(a.id)
      if (a.source && !SOURCE_LEVELS.includes(a.source)) {
        errors.push(`eval ${ev.id}/${a.id}: 未知 source "${a.source}"`)
      }
    }
  }
  return errors
}

export async function loadDeclaration(repoRoot, skill) {
  const file = path.join(repoRoot, 'skills', skill, 'evals/evals.json')
  if (!await fs.pathExists(file)) return null
  return fs.readJson(file)
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/declarations.test.mjs`
Expected: PASS，8 个 test 全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/declarations.js tests/harness/declarations.test.mjs
git commit -m "feat(harness): 质量声明加载与校验，source 为累进层级"
```

---

## Task 5: 迁移 4 份 evals.json

数据迁移 + 一条守着全仓库的校验测试。这条测试是防腐烂的闸门——没有它，`skill_name` 写错这类事会再次发生。

**Files:**
- Modify: `skills/mint/learn-skill/evals/evals.json`
- Modify: `skills/coding/handoff/evals/evals.json`
- Modify: `skills/research/extract-cognition/evals/evals.json`
- Modify: `skills/coding/setup-debug/evals/evals.json`
- Test: `tests/harness/declarations.test.mjs`（追加）

**Interfaces:**
- Consumes: Task 4 的 `validateDeclaration`
- Produces: 4 份合法的新格式声明

- [ ] **Step 1: 写失败测试**

追加到 `tests/harness/declarations.test.mjs`：

```js
import fs from 'fs-extra'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { validateDeclaration } from '../../tools/skill-harness/declarations.js'

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')

test('仓库里每一份 evals.json 都必须合法——这是防止声明跟着 skill 一起腐烂的闸门', async () => {
  const skillsDir = path.join(REPO_ROOT, 'skills')
  const found = []
  for (const cat of await fs.readdir(skillsDir)) {
    const catDir = path.join(skillsDir, cat)
    if (!(await fs.stat(catDir)).isDirectory()) continue
    for (const name of await fs.readdir(catDir)) {
      const file = path.join(catDir, name, 'evals/evals.json')
      if (await fs.pathExists(file)) found.push({ file, skillPath: path.join(catDir, name) })
    }
  }

  assert.ok(found.length >= 4, `预期至少 4 份 evals.json，实际找到 ${found.length}`)
  for (const { file, skillPath } of found) {
    const errs = validateDeclaration(await fs.readJson(file), skillPath)
    assert.deepEqual(errs, [], `${path.relative(REPO_ROOT, file)}:\n  ${errs.join('\n  ')}`)
  }
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/declarations.test.mjs`
Expected: FAIL —— 至少报出 `skills/mint/learn-skill/evals/evals.json` 的 `skill_name "inspect-skill" 与目录名 "learn-skill" 不符` 与三条裸字符串错误

- [ ] **Step 3: 迁移 learn-skill**

把 `skills/mint/learn-skill/evals/evals.json` 的 `skill_name` 从 `"inspect-skill"` 改成 `"learn-skill"`，并把三个 eval 里各自的 `assertions` 裸字符串数组替换为下面这个数组（三个 eval 的断言内容原本就完全相同，逐个 eval 各贴一份，**不做 `$ref` 共享**）：

```json
      "frozen": "2026-08-17",
      "assertions": [
        { "id": "philosophy-first", "source": "reply",
          "text": "报告包含四个维度，且设计哲学（Design Philosophy）是第一个出现的维度标题" },
        { "id": "no-score-labels", "source": "reply",
          "text": "报告不包含评分标签（Excellent / Good / Needs Work / Poor 或数字评分）" },
        { "id": "no-extra-review-sections", "source": "reply",
          "text": "报告不包含额外评估段落（如 '## 问题与改进建议'、'## 发布评估'、'## 改进建议'、'## 总体结论' 等评审性标题）" },
        { "id": "zh-body", "source": "reply",
          "text": "报告主体叙述使用中文" },
        { "id": "closing-question", "source": "reply",
          "text": "报告结尾包含收尾问句（询问用户是否想深入了解某部分），而不是以改进建议或评审内容结束" }
      ]
```

保留每个 eval 原有的 `id` / `prompt` / `expected_output` / `files` 不变。

- [ ] **Step 4: 迁移 extract-cognition（最轻，只补两个字段）**

`skills/research/extract-cognition/evals/evals.json` 的 `skill_name` 已正确，`assertions` 已经是带 `id` + `text` 的对象数组，**内容一条都不要改**。只做两件事：

1. 三个 eval 各加一行 `"frozen": "2026-08-17",`
2. 每条 assertion 各加一个 `"source"`：eval 0 与 eval 1 的全部断言判的都是产出的 `.md` 文件 → `"artifact"`；eval 2 的 `hard_stop_triggered` 判的是 skill 的拒绝回复 → `"reply"`，`no_files_produced` 判的是产出物树 → `"artifact"`。

注意 eval 0 与 eval 1 都有 `every_move_has_anchor` 等同名 id——**这是合法的**，`validateDeclaration` 的唯一性只在单个 eval 内检查，跨 eval 同名不冲突。

- [ ] **Step 5: 迁移 handoff（无 assertions，需新写）**

`skills/coding/handoff/evals/evals.json` 的 `skill_name` 已正确。四个 eval 都只有整段 `expected_output`、没有 `assertions`——这正是决定 4 要改掉的形态。保留 `expected_output` 原文不动（它降级为给人看的描述），为每个 eval 加 `"frozen": "2026-08-17"` 和下面对应的 `assertions`。

eval 0 `author-high-to-low-model`：

```json
      "assertions": [
        { "id": "file-in-output-dir", "source": "artifact",
          "text": "在 docs/commute/ 下生成了文件名形如 YYYY-MM-DD-<topic>-handoff.md 的文档" },
        { "id": "header-has-status-and-purpose", "source": "artifact",
          "text": "文档抬头同时含状态字段与交接目的两项" },
        { "id": "purpose-is-continuation", "source": "artifact",
          "text": "交接目的描述为「接手方续做同一实现任务」一类，而不是仅传递背景" },
        { "id": "continuation-sections-present", "source": "artifact",
          "text": "文档含范围铁律与相关文档索引两节" },
        { "id": "anchor-is-falsifiable", "source": "artifact",
          "text": "最小验收锚点是硬判据，有明确的对错判定，不是「让它工作」这类无法证伪的软标准" }
      ]
```

eval 1 `author-cross-device-continuation`：

```json
      "assertions": [
        { "id": "file-in-output-dir", "source": "artifact",
          "text": "在 docs/commute/ 下生成了文件名形如 YYYY-MM-DD-<topic>-handoff.md 的文档" },
        { "id": "status-is-pending", "source": "artifact",
          "text": "状态字段的值是「待执行」" },
        { "id": "background-describes-progress", "source": "artifact",
          "text": "背景与现状章节写明了当前做到哪一步" },
        { "id": "anchor-references-original-criteria", "source": "artifact",
          "text": "最小验收锚点引用原任务的成功判据，且是硬判据" }
      ]
```

eval 2 `accept-catches-failing-criterion`：

```json
      "assertions": [
        { "id": "ran-criteria-not-just-read", "source": "transcript",
          "text": "执行轨迹显示实际运行了 slugify.js（如 Bash 调用 node slugify.js），而不是只读文档就下判断" },
        { "id": "status-set-to-rejected", "source": "artifact",
          "text": "fixture 交接文档的状态被置为「打回」，不是「已验收」" },
        { "id": "names-failing-criterion", "source": "artifact",
          "text": "验收记录点名了未达标的是「去标点」那一条判据，而不是笼统说没通过" },
        { "id": "record-appended-to-anchor-section", "source": "artifact",
          "text": "验收结果被追加在最小验收锚点章节末尾，而不是另起一节或写在文档开头" }
      ]
```

eval 3 `author-background-only-handoff`：

```json
      "assertions": [
        { "id": "purpose-is-background-only", "source": "artifact",
          "text": "交接目的写成「仅传递背景结论，不要求接手方产出可验收的实现」一类描述" },
        { "id": "has-purpose-and-anchor", "source": "artifact",
          "text": "交接目的与最小验收锚点两节均存在" },
        { "id": "no-continuation-sections", "source": "artifact",
          "text": "文档不含范围铁律、受影响文件、验证步骤、关键决定中的任何一节" },
        { "id": "anchor-is-soft", "source": "artifact",
          "text": "最小验收锚点是软判据（如「接手方能复述讨论结论要点」），不是硬判据" }
      ]
```

- [ ] **Step 6: 迁移 setup-debug（skill_name 腐烂 + 无 assertions）**

`skills/coding/setup-debug/evals/evals.json` 的 `skill_name` 是 `"full-stack-debug-env"`，目录名是 `setup-debug`——**这是仓库里第二处 skill_name 腐烂**，改成 `"setup-debug"`。两个 eval 各加 `"frozen": "2026-08-17"` 与下面的 `assertions`。

eval 1（Node + SPA）：

```json
      "assertions": [
        { "id": "log-dir-created", "source": "artifact",
          "text": "创建了 tmp/logs/ 目录" },
        { "id": "backend-and-browser-sources", "source": "artifact",
          "text": "日志来源规划中至少含 backend 与 browser 两个独立来源，各自有独立日志文件" },
        { "id": "verify-script-created", "source": "artifact",
          "text": "创建了 harness/debug/verify-logs.sh" },
        { "id": "both-docs-generated", "source": "artifact",
          "text": "同时生成了 harness/debug/README.md 与 docs/how-to/debug-env.md 两份文档" }
      ]
```

eval 2（Docker Compose 三容器）：

```json
      "assertions": [
        { "id": "three-sources-planned", "source": "artifact",
          "text": "规划了 api、worker、db 三个独立日志来源，各自有独立日志文件" },
        { "id": "worker-typed-async", "source": "artifact",
          "text": "worker 被识别为异步或任务驱动型来源，而不是与 api 同类处理" },
        { "id": "worker-skip-not-fail", "source": "artifact",
          "text": "verify-logs.sh 中 worker.log 的检查结果是 SKIP，不是 FAIL——异步来源在无任务时本就无日志" },
        { "id": "both-docs-generated", "source": "artifact",
          "text": "同时生成了 harness/debug/README.md 与 docs/how-to/debug-env.md 两份文档" }
      ]
```

- [ ] **Step 7: 跑测试确认通过**

Run: `node --test tests/harness/declarations.test.mjs`
Expected: PASS。若报 `skill_name 与目录名不符`，说明还有没改到的文件；若报 `裸字符串`，说明还有 eval 没加 `assertions`。

- [ ] **Step 8: 提交**

```bash
git add skills/mint/learn-skill/evals/evals.json skills/coding/handoff/evals/evals.json skills/research/extract-cognition/evals/evals.json skills/coding/setup-debug/evals/evals.json tests/harness/declarations.test.mjs
git commit -m "refactor(evals): 4 份声明迁移到带稳定 id 的 assertions 格式"
```

---

## Task 6: grade/prompt.js —— grader prompt 组装

三态在 prompt 里必须是个真出口。不给 grader 说「判不了」的机会，被迫二选一的 grader 会编证据——这是 `unavailable` 的主要价值，不只是渲染标记。

**Files:**
- Create: `tools/skill-harness/grade/prompt.js`
- Test: `tests/harness/grade-prompt.test.mjs`

**Interfaces:**
- Consumes: Task 4 的 `sourceIncludes` / `maxSourceLevel`
- Produces: `buildGradePrompt({ evalDef, materials }): string`，其中 `materials` 形如 `{ reply: string|null, artifacts: [{ path, content }], transcript: string|null }`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/grade-prompt.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildGradePrompt } from '../../tools/skill-harness/grade/prompt.js'

const EVAL_REPLY_ONLY = {
  id: 1, prompt: '分析这个 skill',
  assertions: [{ id: 'zh-body', text: '主体使用中文', source: 'reply' }],
}

const EVAL_ARTIFACT = {
  id: 2, prompt: '写一份交接',
  assertions: [
    { id: 'zh-body', text: '主体使用中文', source: 'reply' },
    { id: 'has-anchor', text: '文档含最小验收锚点章节', source: 'artifact' },
  ],
}

const MATERIALS = {
  reply: '已完成，文档在 docs/commute/x.md',
  artifacts: [{ path: 'docs/commute/x.md', content: '# 交接\n## 最小验收锚点\n...' }],
  transcript: '{"type":"tool_use","name":"Write"}',
}

test('prompt 必须给 grader 一个说「判不了」的出口——不给出口，被迫二选一的 grader 会编证据', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: MATERIALS })
  assert.ok(p.includes('unavailable'))
  assert.ok(/不要猜/.test(p))
})

test('要求 evidence 引原文而非复述——复述出来的证据无法核对', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: MATERIALS })
  assert.ok(/原文/.test(p))
})

test('全是 reply 级断言时不塞产出物和轨迹——source 是成本闸门，塞了就白花钱', () => {
  const p = buildGradePrompt({ evalDef: EVAL_REPLY_ONLY, materials: MATERIALS })
  assert.ok(!p.includes('docs/commute/x.md'))
  assert.ok(!p.includes('tool_use'))
  assert.ok(p.includes('已完成，文档在 docs/commute/x.md'))
})

test('有一条 artifact 级断言就把产出物一起喂——层级取最高，不是逐条各喂一份', () => {
  const p = buildGradePrompt({ evalDef: EVAL_ARTIFACT, materials: MATERIALS })
  assert.ok(p.includes('docs/commute/x.md'))
  assert.ok(p.includes('最小验收锚点'))
  assert.ok(!p.includes('tool_use'), 'transcript 未被任何断言声明，不该出现')
})

test('材料缺失时显式写「缺失」而不是留空——留空 grader 会以为材料就长这样', () => {
  const p = buildGradePrompt({
    evalDef: EVAL_ARTIFACT,
    materials: { reply: null, artifacts: [], transcript: null },
  })
  assert.ok(p.includes('(缺失)'))
})

test('每条断言的 id 都出现在 prompt 里——grader 要按 id 回填，对不上就没法归位', () => {
  const p = buildGradePrompt({ evalDef: EVAL_ARTIFACT, materials: MATERIALS })
  assert.ok(p.includes('zh-body'))
  assert.ok(p.includes('has-anchor'))
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/grade-prompt.test.mjs`
Expected: FAIL —— `Cannot find module '.../grade/prompt.js'`

- [ ] **Step 3: 实现 grade/prompt.js**

创建 `tools/skill-harness/grade/prompt.js`：

```js
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/grade-prompt.test.mjs`
Expected: PASS，6 个 test 全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/grade/prompt.js tests/harness/grade-prompt.test.mjs
git commit -m "feat(harness): grader prompt 组装，source 决定喂什么材料"
```

---

## Task 7: grade/parse.js —— grader 输出解析

量具坏了要看得出来。解析失败静默算 fail 是这套框架最危险的失效模式：它会把 grader 的故障渲染成被测平台的质量问题，而且看起来极其可信。

**Files:**
- Create: `tools/skill-harness/grade/parse.js`
- Test: `tests/harness/grade-parse.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `VERDICTS: Set<string>` —— `pass` / `fail` / `unavailable`
  - `extractJson(raw: string): string` —— 抛错表示找不到 JSON
  - `parseGraderOutput(raw: string, assertions: object[]): { ok: boolean, assertions: [{ id, verdict, evidence }] }`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/grade-parse.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseGraderOutput, extractJson, VERDICTS } from '../../tools/skill-harness/grade/parse.js'

const ASSERTIONS = [{ id: 'a', text: 'A' }, { id: 'b', text: 'B' }]

test('三态齐全——只有 pass/fail 的话 unavailable 无处安放，必然被压成其中之一', () => {
  assert.deepEqual([...VERDICTS].sort(), ['fail', 'pass', 'unavailable'])
})

test('围栏包裹的 JSON 要能取出来——grader 常自作主张加 ```json', () => {
  assert.equal(extractJson('前言\n```json\n{"a":1}\n```\n后记').trim(), '{"a":1}')
  assert.equal(extractJson('{"a":1}'), '{"a":1}')
  assert.equal(extractJson('废话 {"a":1} 废话'), '{"a":1}')
})

test('解析失败必须全判 unavailable——静默算 fail 会把量具故障伪装成平台质量问题', () => {
  const r = parseGraderOutput('模型今天不想输出 JSON', ASSERTIONS)
  assert.equal(r.ok, false)
  assert.equal(r.assertions.length, 2)
  for (const a of r.assertions) {
    assert.equal(a.verdict, 'unavailable')
    assert.match(a.evidence, /unparseable/)
  }
})

test('grader 漏判某条，那条判 unavailable，不牵连已判的条目', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"pass","evidence":"原文 X"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.ok, true)
  assert.equal(r.assertions[0].verdict, 'pass')
  assert.equal(r.assertions[0].evidence, '原文 X')
  assert.equal(r.assertions[1].verdict, 'unavailable')
  assert.match(r.assertions[1].evidence, /未给出/)
})

test('verdict 取值非法当作没判——"partially" 这种自造值不能悄悄当成 pass', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"partially","evidence":"e"},{"id":"b","verdict":"fail","evidence":"f"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.assertions[0].verdict, 'unavailable')
  assert.equal(r.assertions[1].verdict, 'fail')
})

test('输出顺序按声明顺序，不按 grader 返回顺序——矩阵的行顺序必须稳定', () => {
  const raw = '{"assertions":[{"id":"b","verdict":"fail","evidence":"f"},{"id":"a","verdict":"pass","evidence":"p"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.deepEqual(r.assertions.map(x => x.id), ['a', 'b'])
})

test('grader 编出声明里没有的断言 id，直接丢弃——不许它自己加行', () => {
  const raw = '{"assertions":[{"id":"a","verdict":"pass","evidence":"p"},{"id":"ghost","verdict":"pass","evidence":"x"}]}'
  const r = parseGraderOutput(raw, ASSERTIONS)
  assert.equal(r.assertions.length, 2)
  assert.ok(!r.assertions.some(x => x.id === 'ghost'))
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/grade-parse.test.mjs`
Expected: FAIL —— `Cannot find module '.../grade/parse.js'`

- [ ] **Step 3: 实现 grade/parse.js**

创建 `tools/skill-harness/grade/parse.js`：

```js
export const VERDICTS = new Set(['pass', 'fail', 'unavailable'])

const TAIL = 400

function tail(s) {
  const str = String(s ?? '')
  return str.length <= TAIL ? str : str.slice(str.length - TAIL)
}

// grader 常自作主张加 ```json 围栏或前后寒暄，这里只负责把 JSON 那段抠出来。
export function extractJson(raw) {
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(raw ?? '')
  if (fenced) return fenced[1]
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
    return { id: decl.id, verdict: got.verdict, evidence: String(got.evidence ?? '') }
  })

  return { ok: true, assertions: out }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/grade-parse.test.mjs`
Expected: PASS，7 个 test 全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/grade/parse.js tests/harness/grade-parse.test.mjs
git commit -m "feat(harness): grader 输出解析，失败路径产出全 unavailable"
```

---

## Task 8: grade/index.js 编排 + CLI `grade` 命令

把前两个纯函数模块接起来：选格、读材料、调 `claude -p`、重试一次、写 `gradings.json`。

**Files:**
- Create: `tools/skill-harness/grade/index.js`
- Modify: `tools/skill-harness/cli.js`
- Test: `tests/harness/grade-index.test.mjs`
- Test: `tests/harness/cli.test.mjs`（已存在，追加）

**Interfaces:**
- Consumes: Task 2 的 `cellDirName`；Task 4 的 `loadDeclaration` / `maxSourceLevel`；Task 6 的 `buildGradePrompt`；Task 7 的 `parseGraderOutput`
- Produces:
  - `selectGradeCells({ records, declarations, profiles }): [{ skill, platform, mode, repeat, evalDef, skip }]`
  - `readMaterials(cellDir, level): Promise<{ reply, artifacts, transcript }>`
  - `runGrade({ runDir, repoRoot, graderModel, only, invoke }): Promise<object>` —— `invoke(prompt, model)` 可注入，测试用假实现
  - CLI：`grade <runId>`，旗标 `--grader-model`（必填）、`--only`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/grade-index.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { selectGradeCells, readMaterials, runGrade } from '../../tools/skill-harness/grade/index.js'
import { cellDirName } from '../../tools/skill-harness/harvest.js'

const DECL = {
  skill_name: 'x',
  evals: [{ id: 1, prompt: 'do it', frozen: '2026-08-17',
    assertions: [{ id: 'a', text: 'A', source: 'artifact' }] }],
}

test('只评上游 pass 的格子——上游装不上就没有可判的东西，不是质量差', () => {
  const records = [
    { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' },
    { skill: 'a/x', platform: 'pi', mode: 'native', repeat: 0, exitCode: 1, reply: null },
    { skill: 'a/x', platform: 'hermes', mode: 'native', repeat: 0, exitCode: 0, reply: null },
  ]
  const cells = selectGradeCells({ records, declarations: new Map([['a/x', DECL]]) })
  assert.equal(cells.length, 1)
  assert.equal(cells[0].platform, 'claude')
})

test('没有声明的 skill 不评，也不报错——按需增量下这是常态', () => {
  const records = [{ skill: 'a/y', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }]
  const cells = selectGradeCells({ records, declarations: new Map() })
  assert.deepEqual(cells, [])
})

test('读材料时缺产出物不抛错——采集失败的格子要能一路走到 unavailable', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'transcript.jsonl'), '{"t":1}')
  const m = await readMaterials(dir, 'artifact')
  assert.deepEqual(m.artifacts, [])
  await fs.remove(dir)
})

test('产出物按相对路径读全，内容与路径一起交给 grader', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'artifacts/docs/a.md'), 'AAA')
  const m = await readMaterials(dir, 'artifact')
  assert.equal(m.artifacts.length, 1)
  assert.equal(m.artifacts[0].path, 'docs/a.md')
  assert.equal(m.artifacts[0].content, 'AAA')
  await fs.remove(dir)
})

test('reply 级不读产出物和轨迹——成本闸门要在读盘这一层就生效', async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-test-'))
  await fs.outputFile(path.join(dir, 'artifacts/a.md'), 'AAA')
  await fs.outputFile(path.join(dir, 'transcript.jsonl'), 'T')
  const m = await readMaterials(dir, 'reply')
  assert.deepEqual(m.artifacts, [])
  assert.equal(m.transcript, null)
  await fs.remove(dir)
})

test('grader 首次输出坏掉时重试一次；两次都坏才判 unavailable', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])
  await fs.outputFile(path.join(runDir, 'cells', cellDirName(rec), 'artifacts/a.md'), 'AAA')

  let calls = 0
  const invoke = async () => {
    calls++
    return calls === 1 ? '不是 JSON' : '{"assertions":[{"id":"a","verdict":"pass","evidence":"AAA"}]}'
  }

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke,
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(calls, 2)
  assert.equal(out.gradings[0].assertions[0].verdict, 'pass')
  await fs.remove(runDir)
})

test('两次都解析失败就判 unavailable，且 gradings.json 头部记下 grader 模型', async () => {
  const runDir = await fs.mkdtemp(path.join(os.tmpdir(), 'grade-run-'))
  const rec = { skill: 'a/x', platform: 'claude', mode: 'native', repeat: 0, exitCode: 0, reply: 'ok' }
  await fs.writeJson(path.join(runDir, 'records.json'), [rec])

  const out = await runGrade({
    runDir, graderModel: 'grader-m', invoke: async () => '始终不是 JSON',
    declarations: new Map([['a/x', DECL]]),
  })

  assert.equal(out.graderModel, 'grader-m')
  assert.equal(out.gradings[0].assertions[0].verdict, 'unavailable')
  assert.ok(await fs.pathExists(path.join(runDir, 'gradings.json')))
  await fs.remove(runDir)
})
```

追加到 `tests/harness/cli.test.mjs`：

```js
test('grade 缺 --grader-model 直接报错——不 pin 量具，跨平台差异就是平台⊗模型混合效应', () => {
  assert.throws(() => parseArgs(['grade', '20260817-120000-abcd']), /grader-model/)
})

test('grade 认得 runId 与 --only', () => {
  const { command, opts } = parseArgs(['grade', '20260817-120000-abcd', '--grader-model', 'm', '--only', 'a/x'])
  assert.equal(command, 'grade')
  assert.equal(opts.runId, '20260817-120000-abcd')
  assert.equal(opts.graderModel, 'm')
  assert.deepEqual(opts.only, ['a/x'])
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/grade-index.test.mjs tests/harness/cli.test.mjs`
Expected: FAIL —— `Cannot find module '.../grade/index.js'`；`unknown command: grade`

- [ ] **Step 3: 实现 grade/index.js**

创建 `tools/skill-harness/grade/index.js`：

```js
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { cellDirName } from '../harvest.js'
import { maxSourceLevel } from '../declarations.js'
import { buildGradePrompt } from './prompt.js'
import { parseGraderOutput } from './parse.js'
import { createJail } from '../jail.js'
import { claudeAdapter } from '../adapters/claude.js'

// 只评「上游 pass 且有声明」的格子。上游没跑通时没有可判的东西——
// 那是装不上，不是做得差，混为一谈会把安装失败伪装成质量问题。
export function selectGradeCells({ records, declarations, only }) {
  const out = []
  for (const rec of records) {
    if (only?.length && !only.includes(rec.skill)) continue
    if (rec.exitCode !== 0) continue
    if (rec.reply === null || rec.reply === undefined) continue
    const decl = declarations.get(rec.skill)
    if (!decl) continue
    for (const evalDef of decl.evals ?? []) {
      out.push({
        skill: rec.skill, platform: rec.platform, mode: rec.mode,
        repeat: rec.repeat ?? 0, evalDef, reply: rec.reply,
      })
    }
  }
  return out
}

async function readArtifacts(dir) {
  const root = path.join(dir, 'artifacts')
  if (!await fs.pathExists(root)) return []
  const out = []
  async function walk(cur) {
    for (const e of await fs.readdir(cur, { withFileTypes: true })) {
      const full = path.join(cur, e.name)
      if (e.isDirectory()) await walk(full)
      else if (e.isFile()) {
        out.push({ path: path.relative(root, full), content: await fs.readFile(full, 'utf8') })
      }
    }
  }
  await walk(root)
  return out.sort((a, b) => a.path.localeCompare(b.path))
}

// level 在读盘这一层就生效：成本闸门若只在拼 prompt 时生效，
// 大文件已经进了内存，省不下真正贵的那部分。
export async function readMaterials(cellDir, level, reply = null) {
  const m = { reply, artifacts: [], transcript: null }
  if (level === 'reply') return m
  m.artifacts = await readArtifacts(cellDir)
  if (level === 'transcript') {
    const f = path.join(cellDir, 'transcript.jsonl')
    m.transcript = await fs.pathExists(f) ? await fs.readFile(f, 'utf8') : null
  }
  return m
}

// grader 跑在空 jail 里、不装任何 skill：跑在宿主环境的话，
// ~/.claude/skills 那些会被加载，grader 可能被自己要判的 skill 触发，判定不可复现。
export async function invokeClaudeGrader(prompt, model, ctx = {}) {
  const { dir: jailDir, cleanup } = await createJail()
  try {
    const env = claudeAdapter.jailEnv({
      jailDir, source: ctx.source ?? process.env,
      oauthToken: ctx.oauthToken, baseUrl: ctx.baseUrl, apiKey: ctx.apiKey,
    })
    const argv = ['-p', '--model', model, '--setting-sources', 'user', prompt]
    return await new Promise(resolve => {
      let out = ''
      const child = spawn('claude', argv, { cwd: jailDir, env, stdio: ['ignore', 'pipe', 'ignore'] })
      child.stdout.on('data', d => { out += d })
      child.on('close', () => resolve(out))
      child.on('error', e => resolve(`grader spawn failed: ${e.message}`))
    })
  } finally {
    await cleanup()
  }
}

export async function runGrade({ runDir, graderModel, only, invoke, declarations }) {
  if (!graderModel) throw new Error('--grader-model is required — an unpinned grader confounds the measuring stick with the thing measured')
  const records = await fs.readJson(path.join(runDir, 'records.json'))
  const cells = selectGradeCells({ records, declarations, only })

  const gradings = []
  for (const c of cells) {
    const level = maxSourceLevel(c.evalDef.assertions)
    const cellDir = path.join(runDir, 'cells', cellDirName(c))
    const materials = await readMaterials(cellDir, level, c.reply)
    const prompt = buildGradePrompt({ evalDef: c.evalDef, materials })

    // 重试一次：量具偶发不吐 JSON 是常见的，重试成本远低于把整格记成 unavailable。
    let parsed = parseGraderOutput(await invoke(prompt, graderModel), c.evalDef.assertions)
    if (!parsed.ok) {
      parsed = parseGraderOutput(await invoke(prompt, graderModel), c.evalDef.assertions)
    }

    gradings.push({
      skill: c.skill, platform: c.platform, mode: c.mode,
      repeat: c.repeat, evalId: c.evalDef.id,
      frozen: c.evalDef.frozen ?? null,
      assertions: parsed.assertions,
    })
  }

  const subjectModel = records.find(r => r.model)?.model ?? null
  const out = { runId: path.basename(runDir), graderModel, subjectModel, gradings }
  await fs.writeJson(path.join(runDir, 'gradings.json'), out, { spaces: 2 })
  return out
}
```

- [ ] **Step 4: 接 CLI**

在 `tools/skill-harness/cli.js` 中：

把 `const COMMANDS = new Set(['run', 'dry-run', 'report', 'coverage'])` 改成：

```js
const COMMANDS = new Set(['run', 'dry-run', 'report', 'coverage', 'grade'])
```

在 `REPEATABLE` 常量里加一项 `--only`：

```js
const REPEATABLE = { '--skill': 'skills', '--platform': 'platforms', '--bundle': 'bundles', '--only': 'only' }
```

在 `parseArgs` 的 for 循环开始**之前**（`for (let i = 1; ...` 那行之前）插入位置参数读取：

```js
  // grade 的第一个位置参数是 runId，不是旗标
  let start = 1
  if (command === 'grade' && argv[1] && !argv[1].startsWith('--')) {
    opts.runId = argv[1]
    start = 2
  }
```

并把循环起点从 `let i = 1` 改成 `let i = start`。

在 flag 分支链里，`else if (flag === '--repeat') opts.repeat = Number(value)` 之后加一行：

```js
    else if (flag === '--grader-model') opts.graderModel = value
```

在 `parseArgs` 末尾 `return { command, opts }` 之前加：

```js
  if (command === 'grade') {
    if (!opts.runId) throw new Error('grade requires a runId: skill-harness grade <runId> --grader-model <model>')
    if (!opts.graderModel) throw new Error('--grader-model is required — an unpinned grader confounds the measuring stick with the thing measured')
  }
```

在 `main()` 里，`if (command === 'coverage') {` 那一段**之前**插入：

```js
  if (command === 'grade') {
    const runDir = path.join(os.homedir(), '.hskill/skill-harness', opts.runId)
    const declarations = new Map()
    for (const s of index.skills) {
      const decl = await loadDeclaration(REPO_ROOT, s.path)
      if (decl) declarations.set(s.path, decl)
    }
    const out = await runGrade({
      runDir, graderModel: opts.graderModel, only: opts.only, declarations,
      invoke: (prompt, model) => invokeClaudeGrader(prompt, model, {
        source: process.env,
        oauthToken: opts.baseUrl ? undefined : claudeOAuthToken(),
        baseUrl: opts.baseUrl,
        apiKey: opts.baseUrl ? process.env.MINIMAX_CN_API_KEY : undefined,
      }),
    })
    console.log(`graded ${out.gradings.length} (skill, eval) pairs -> ${path.join(runDir, 'gradings.json')}`)
    return
  }
```

并在 cli.js 的 import 区加两行：

```js
import { runGrade, invokeClaudeGrader } from './grade/index.js'
import { loadDeclaration } from './declarations.js'
```

- [ ] **Step 5: 跑测试确认通过**

Run: `node --test tests/harness/grade-index.test.mjs tests/harness/cli.test.mjs`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add tools/skill-harness/grade/index.js tools/skill-harness/cli.js tests/harness/grade-index.test.mjs tests/harness/cli.test.mjs
git commit -m "feat(harness): grade 子命令，离线判定并落 gradings.json"
```

---

## Task 9: variance.js —— repeat 聚合与 unstable

一把自己会漂的尺子量出来的平台差异，分不清是平台差异还是尺子在漂。`unstable` 就是给这种情况准备的显式标记。

**Files:**
- Create: `tools/skill-harness/variance.js`
- Test: `tests/harness/variance.test.mjs`

**Interfaces:**
- Consumes: Task 8 产出的 `gradings` 数组
- Produces: `aggregateVerdicts(gradings): [{ skill, platform, mode, evalId, assertionId, verdict, unstable, verdicts }]`，其中 `verdict` 在不一致时为 `'unstable'`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/variance.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { aggregateVerdicts } from '../../tools/skill-harness/variance.js'

const g = (repeat, verdict) => ({
  skill: 'a/x', platform: 'pi', mode: 'native', evalId: 1, repeat,
  assertions: [{ id: 'a', verdict, evidence: 'e' }],
})

test('五次一致就是稳定，verdict 取那个一致值', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'pass'), g(2, 'pass'), g(3, 'pass'), g(4, 'pass')])
  assert.equal(out.length, 1)
  assert.equal(out[0].verdict, 'pass')
  assert.equal(out[0].unstable, false)
})

test('有分歧就标 unstable，不取多数——多数决会把"尺子在漂"粉饰成一个确定结论', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'pass'), g(2, 'pass'), g(3, 'pass'), g(4, 'fail')])
  assert.equal(out[0].verdict, 'unstable')
  assert.equal(out[0].unstable, true)
  assert.deepEqual(out[0].verdicts.sort(), ['fail', 'pass', 'pass', 'pass', 'pass'])
})

test('unavailable 与 pass 混合也算不稳——判得了和判不了之间的摇摆同样是尺子在漂', () => {
  const out = aggregateVerdicts([g(0, 'pass'), g(1, 'unavailable')])
  assert.equal(out[0].verdict, 'unstable')
})

test('跑一次也能聚合，结果就是那一次——标定不是使用的前提', () => {
  const out = aggregateVerdicts([g(0, 'fail')])
  assert.equal(out[0].verdict, 'fail')
  assert.equal(out[0].unstable, false)
})

test('不同平台不聚合到一起——聚合键必须含 platform 和 mode', () => {
  const out = aggregateVerdicts([
    { skill: 'a/x', platform: 'pi', mode: 'native', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'pass' }] },
    { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'fail' }] },
    { skill: 'a/x', platform: 'pi', mode: 'inject', evalId: 1, repeat: 0, assertions: [{ id: 'a', verdict: 'fail' }] },
  ])
  assert.equal(out.length, 3)
  assert.ok(out.every(x => x.unstable === false))
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/variance.test.mjs`
Expected: FAIL —— `Cannot find module '.../variance.js'`

- [ ] **Step 3: 实现 variance.js**

创建 `tools/skill-harness/variance.js`：

```js
// 同一格重复跑，看的是 grader 的判定稳不稳，不是被测方稳不稳。
// 不一致时**不取多数决**：多数决会把「尺子在漂」粉饰成一个确定结论，
// 而这正是标定要暴露的东西。不稳的处置是换指标，不是加样本。
export function aggregateVerdicts(gradings) {
  const groups = new Map()
  for (const g of gradings ?? []) {
    for (const a of g.assertions ?? []) {
      const key = `${g.skill}|${g.platform}|${g.mode}|${g.evalId}|${a.id}`
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/variance.test.mjs`
Expected: PASS，5 个 test 全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/variance.js tests/harness/variance.test.mjs
git commit -m "feat(harness): repeat 聚合，判定有分歧标 unstable 不取多数决"
```

---

## Task 10: quality-report.js —— 断言级矩阵

计数去重是这个任务最容易做错、错了最难发现的地方：`blocked-upstream` 按断言条数计，会让「断言写得多的 skill」权重更大，平台差异变成断言条数的函数。

**Files:**
- Create: `tools/skill-harness/quality-report.js`
- Test: `tests/harness/quality-report.test.mjs`

**Interfaces:**
- Consumes: Task 9 的 `aggregateVerdicts` 输出；`records.json`；声明 Map
- Produces: `upstreamStatus(skill, platform, mode, records): string`、`renderQualityReport({ records, declarations, verdicts, allSkills, graderModel, subjectModel }): string`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/quality-report.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { renderQualityReport, upstreamStatus } from '../../tools/skill-harness/quality-report.js'

const DECL = {
  skill_name: 'x',
  evals: [{ id: 1, frozen: '2026-08-17', assertions: [
    { id: 'aa', text: 'A' }, { id: 'bb', text: 'B' },
  ] }],
}

const RECORDS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', exitCode: 0, reply: 'ok', model: 'subj-m', unavailable: [], modelMismatch: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', exitCode: 0, reply: 'ok', model: 'subj-m', unavailable: [], modelMismatch: false },
  { skill: 'a/x', platform: 'hermes', mode: 'native', exitCode: 1, reply: null, model: 'subj-m', unavailable: [], modelMismatch: false },
]

const VERDICTS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, assertionId: 'aa', verdict: 'pass', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'native', evalId: 1, assertionId: 'bb', verdict: 'fail', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', evalId: 1, assertionId: 'aa', verdict: 'unavailable', unstable: false },
  { skill: 'a/x', platform: 'claude', mode: 'inject', evalId: 1, assertionId: 'bb', verdict: 'unstable', unstable: true },
]

const BASE = {
  records: RECORDS, declarations: new Map([['a/x', DECL]]), verdicts: VERDICTS,
  allSkills: ['a/x', 'a/y', 'a/z'], graderModel: 'grader-m', subjectModel: 'subj-m',
}

test('upstream 行就是第一期矩阵——降级成前置检查，不是删掉', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('[upstream]'))
  assert.equal(upstreamStatus('a/x', 'claude', 'native', RECORDS), 'pass')
  assert.equal(upstreamStatus('a/x', 'hermes', 'native', RECORDS), 'fail')
  assert.equal(upstreamStatus('a/x', 'pi', 'native', RECORDS), 'not-run')
})

test('上游 fail 时断言行填 . 而不是 fail——一次安装失败不得放大成 N 条质量失败', () => {
  const out = renderQualityReport(BASE)
  const row = out.split('\n').find(l => l.trim().startsWith('aa'))
  assert.ok(row.includes('.'))
  assert.ok(!/\bfail\b.*\bfail\b.*\bfail\b/.test(row))
})

test('blocked-upstream 按 (skill,platform,mode) 计一次——按断言条数计会让平台差异变成断言条数的函数', () => {
  const out = renderQualityReport(BASE)
  // a/x 在 hermes/native 上游 fail，该 skill 有 2 条断言，只能计 1
  assert.ok(out.includes('blocked-upstream: 1'), out)
})

test('不打 pass_rate——合成比率会把三态压平，且太容易被单独摘出去引用', () => {
  const out = renderQualityReport(BASE)
  assert.ok(!/pass_rate/.test(out))
  assert.ok(!/通过率/.test(out))
  assert.ok(!/%/.test(out))
})

test('unavailable 既不渲染成 0 也不渲染成对勾', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('unavail'))
  assert.ok(!out.includes('✓'))
})

test('unstable 渲染成 ~，不算 pass 也不算 fail', () => {
  const out = renderQualityReport(BASE)
  assert.ok(/~/.test(out))
  assert.ok(out.includes('unstable: 1'))
})

test('无声明 skill 必须显式列出——稀疏矩阵最大的风险是把"没测"渲染成"没问题"', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('无声明 skill (2)'))
  assert.ok(out.includes('a/y'))
  assert.ok(out.includes('a/z'))
})

test('第一期的归因段落全部保留——降级的是矩阵层，不是归因层', () => {
  const out = renderQualityReport(BASE)
  assert.ok(out.includes('builtinSkillFloor'))
  assert.ok(out.includes('platform notes'))
})

test('量具与被测物同模型要打警告——否则差异可能只是自指伪影', () => {
  const same = renderQualityReport({ ...BASE, graderModel: 'subj-m' })
  assert.ok(/自指/.test(same))
  const diff = renderQualityReport(BASE)
  assert.ok(!/自指/.test(diff))
})

test('未冻结的声明要警告——冻结前不得据其下平台结论', () => {
  const unfrozen = new Map([['a/x', { ...DECL, evals: [{ id: 1, assertions: DECL.evals[0].assertions }] }]])
  const out = renderQualityReport({ ...BASE, declarations: unfrozen })
  assert.ok(/尚未 review/.test(out))
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/harness/quality-report.test.mjs`
Expected: FAIL —— `Cannot find module '.../quality-report.js'`

- [ ] **Step 3: 实现 quality-report.js**

创建 `tools/skill-harness/quality-report.js`：

```js
import { PHASE1_PLATFORMS, MODES } from './select.js'
import { PROFILES } from './profiles.js'

const COMBOS = PHASE1_PLATFORMS.flatMap(p => MODES.map(m => ({ platform: p, mode: m })))
const COL = 12

const LABEL = {
  pass: 'pass', fail: 'fail', unavailable: 'unavail',
  unstable: '~', 'declared-na': 'n/a', 'blocked-upstream': '.', 'not-run': '',
}

export function upstreamStatus(skill, platform, mode, records) {
  const rec = records.find(r => r.skill === skill && r.platform === platform && r.mode === mode)
  if (!rec) return 'not-run'
  if (rec.exitCode !== 0) return 'fail'
  if (rec.reply === null || rec.reply === undefined) return 'fail'
  return 'pass'
}

function assertionState({ skill, platform, mode, evalId, assertionId, assertion, verdicts, upstream }) {
  if (assertion.na_platforms?.includes(platform)) return 'declared-na'
  if (upstream !== 'pass') return upstream === 'not-run' ? 'not-run' : 'blocked-upstream'
  const v = verdicts.find(x =>
    x.skill === skill && x.platform === platform && x.mode === mode &&
    x.evalId === evalId && x.assertionId === assertionId)
  if (!v) return 'not-run'
  return v.unstable ? 'unstable' : v.verdict
}

export function renderQualityReport({ records, declarations, verdicts, allSkills, graderModel, subjectModel }) {
  const lines = []
  const graded = [...declarations.keys()].filter(s => allSkills.includes(s))
  const width = Math.max(24, ...graded.map(s => s.length + 4)) + 2

  lines.push(`grader: model=${graderModel}  subject=${subjectModel}`)
  if (graderModel === subjectModel) {
    lines.push('!! 量具与被测物同模型，差异可能是自指伪影，结论不可直接引用')
  }

  const unfrozen = graded.filter(s => (declarations.get(s).evals ?? []).some(e => !e.frozen))
  if (unfrozen.length) {
    lines.push(`!! 声明尚未 review（未冻结）：${unfrozen.join(', ')} —— 其平台结论不可引用`)
  }

  lines.push('')
  lines.push('skill / assertion'.padEnd(width) + COMBOS.map(c => `${c.platform}/${c.mode[0]}`.padEnd(COL)).join(''))

  const counts = { pass: 0, fail: 0, unavailable: 0, unstable: 0, 'declared-na': 0, 'not-run': 0 }
  const blocked = new Set()

  for (const skill of graded) {
    lines.push(skill)
    const ups = COMBOS.map(({ platform, mode }) => upstreamStatus(skill, platform, mode, records))
    lines.push('  [upstream]'.padEnd(width) + ups.map(s => (LABEL[s] ?? s).padEnd(COL)).join(''))

    for (const ev of declarations.get(skill).evals ?? []) {
      for (const a of ev.assertions ?? []) {
        const cols = COMBOS.map(({ platform, mode }, i) => {
          const state = assertionState({
            skill, platform, mode, evalId: ev.id, assertionId: a.id,
            assertion: a, verdicts, upstream: ups[i],
          })
          if (state === 'blocked-upstream') blocked.add(`${skill}|${platform}|${mode}`)
          else counts[state] = (counts[state] ?? 0) + 1
          return LABEL[state].padEnd(COL)
        })
        lines.push(`  ${a.id}`.padEnd(width) + cols.join(''))
      }
    }
  }

  lines.push('')
  lines.push('legend: .  = blocked-upstream, 见本组 [upstream] 行')
  lines.push('        (空) = not-run    n/a = 声明排除    unavail = 判不了    ~ = unstable')
  lines.push('')
  // 只打各态计数，不打任何合成比率——比率的分母里藏着「排除了多少 unavailable、
  // 多少 blocked」这些恰恰最该被看见的东西。
  lines.push(
    `pass: ${counts.pass}  fail: ${counts.fail}  unavailable: ${counts.unavailable}  ` +
    `unstable: ${counts.unstable}  declared-na: ${counts['declared-na']}  ` +
    `not-run: ${counts['not-run']}  blocked-upstream: ${blocked.size}`,
  )

  const unstableList = verdicts.filter(v => v.unstable)
  if (unstableList.length) {
    lines.push('')
    lines.push(`unstable assertions (${unstableList.length}):`)
    for (const v of unstableList) lines.push(`  ${v.skill}/${v.assertionId}@${v.platform}/${v.mode}`)
  }

  // 稀疏矩阵最大的风险是把「没测」静默渲染成「没问题」。
  const noDecl = allSkills.filter(s => !declarations.has(s))
  lines.push('')
  lines.push(`无声明 skill (${noDecl.length}): ${noDecl.join(', ')}`)

  const mism = records.filter(r => r.modelMismatch)
  if (mism.length) {
    lines.push('')
    lines.push(`model mismatch (${mism.length}): ${mism.map(r => `${r.skill}@${r.platform}`).join(', ')}`)
  }

  const un = records.filter(r => r.unavailable?.length)
  if (un.length) {
    lines.push('')
    lines.push('unavailable fields:')
    for (const r of un) lines.push(`  ${r.skill}@${r.platform}/${r.mode}: ${r.unavailable.join(', ')}`)
  }

  const harv = records.filter(r => r.harvestErrors?.length || r.transcriptTruncated)
  if (harv.length) {
    lines.push('')
    lines.push('harvest issues:')
    for (const r of harv) {
      const bits = [...(r.harvestErrors ?? [])]
      if (r.transcriptTruncated) bits.push('transcript truncated')
      lines.push(`  ${r.skill}@${r.platform}/${r.mode}: ${bits.join('; ')}`)
    }
  }

  lines.push('')
  lines.push(`builtinSkillFloor: ${PROFILES.map(p => `${p.id}=${p.builtinSkillFloor}`).join(' ')} — 触发失败先归因到这一格`)
  lines.push('')
  lines.push('platform notes:')
  for (const p of PROFILES) {
    const chan = p.processChannel === 'collect' ? '过程数据走 collect 通道' : '过程数据在 stdout 内联'
    lines.push(`  ${p.id}: ${chan}；产出物通道 ${p.artifactChannel}`)
  }

  return lines.join('\n')
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/harness/quality-report.test.mjs`
Expected: PASS，10 个 test 全绿

- [ ] **Step 5: 接进 CLI 的 grade 输出**

在 `tools/skill-harness/cli.js` 的 `grade` 分支里，把 `console.log(\`graded ...\`)` 那一行替换为：

```js
    const verdicts = aggregateVerdicts(out.gradings)
    console.log(renderQualityReport({
      records: await fs.readJson(path.join(runDir, 'records.json')),
      declarations, verdicts,
      allSkills: index.skills.map(s => s.path),
      graderModel: out.graderModel, subjectModel: out.subjectModel,
    }))
```

并在 cli.js import 区加：

```js
import { aggregateVerdicts } from './variance.js'
import { renderQualityReport } from './quality-report.js'
```

- [ ] **Step 6: 跑全量测试**

Run: `npm test`
Expected: 全绿

- [ ] **Step 7: 提交**

```bash
git add tools/skill-harness/quality-report.js tools/skill-harness/cli.js tests/harness/quality-report.test.mjs
git commit -m "feat(harness): 断言级质量报告，blocked 计数去重且不打比率"
```

---

## Task 11: 真实模型端到端验证

前十个任务都是单测。这一个用真实模型跑通整条链路，验证 spec 的 10 条验收判据里需要真实运行才能验的那几条。

**Files:**
- Create: `docs/superpowers/specs/measurements/2026-08-17-quality-eval-e2e.md`
- Modify: `docs/superpowers/specs/2026-08-17-skill-harness-quality-eval-design.md`（回填未确认项）

**Interfaces:**
- Consumes: Task 1-10 全部
- Produces: 实测记录文档

- [ ] **Step 1: 跑一格真实运行**

Run:

```bash
node tools/skill-harness/cli.js run \
  --skill mint/learn-skill --platform claude --mode native \
  --model claude-sonnet-5 --repeat 1
```

记下输出末尾的 runId。

- [ ] **Step 2: 核对采集层真的捞到了东西**

Run（把 `<runId>` 换成上一步的值）：

```bash
ls -R ~/.hskill/skill-harness/<runId>/cells/
```

Expected: 有 `mint-learn-skill__claude__native__r0/transcript.jsonl`，且 `artifacts/` 下有 learn-skill 实际写出的报告文件。
若 `artifacts/` 为空：learn-skill 可能只回复不写文件——改用 `--skill coding/handoff` 重跑本步骤，handoff 必然写文档。

- [ ] **Step 3: 确认 jail 已删但 grade 仍能跑**

Run:

```bash
ls /tmp/skill-harness-* 2>&1 | head -3
node tools/skill-harness/cli.js grade <runId> --grader-model claude-opus-5
```

Expected: 第一条命令报 `No such file or directory`（jail 已删）；第二条仍完整跑完并打印质量报告。这验证的是 spec 验收判据第 2 条。

- [ ] **Step 4: 验证自指警告**

Run:

```bash
node tools/skill-harness/cli.js grade <runId> --grader-model claude-sonnet-5
```

Expected: 报告顶部出现 `!! 量具与被测物同模型` 警告（被测模型就是 Step 1 的 `claude-sonnet-5`）。

- [ ] **Step 5: 验证 unstable 标定**

Run:

```bash
node tools/skill-harness/cli.js run \
  --skill mint/learn-skill --platform claude --mode native \
  --model claude-sonnet-5 --repeat 5
node tools/skill-harness/cli.js grade <新 runId> --grader-model claude-opus-5
```

Expected: 报告底部有 `unstable: N` 计数。N 为 0 说明该 skill 的断言在这个平台上判定稳定；N > 0 则对应断言出现在 `unstable assertions` 清单里。**两种结果都是有效结论**，记录即可，不要为了让 N 变成 0 去改断言——那是返修回路要做的事，且要人工过。

- [ ] **Step 6: 写实测记录**

创建 `docs/superpowers/specs/measurements/2026-08-17-quality-eval-e2e.md`，跟随同目录 `2026-08-14-native-vs-inject.md` 的体例，记录：每一步的完整复现命令、实际输出的关键片段、Step 5 的 unstable 计数与具体是哪几条断言不稳、以及 Task 1 Step 6 关于 pi 认证的判定结果。

- [ ] **Step 7: 回填 spec 的未确认项**

打开 `docs/superpowers/specs/2026-08-17-skill-harness-quality-eval-design.md` 的「未确认项汇总」表，把已经查实的行的档位从「没查」改成「已查」并写上结论，指向上一步的实测记录文件。至少这三行现在有答案了：pi 能否认证（Task 1 Step 6）、一次调用判整条断言清单的稳定性（Step 5）、transcript 单份体积（`ls -la` 看 transcript.jsonl 大小）。

- [ ] **Step 8: 跑全量测试并提交**

Run: `npm test`
Expected: 全绿

```bash
git add docs/superpowers/specs/measurements/2026-08-17-quality-eval-e2e.md docs/superpowers/specs/2026-08-17-skill-harness-quality-eval-design.md
git commit -m "docs(harness): 质量评估端到端实测记录，回填未确认项"
```

---

## Spec 覆盖对照

| Spec 章节 | 落在哪个 Task |
|---|---|
| 1 采集层 | Task 2（纯函数）、Task 3（落盘与接入） |
| 1 采集层 · pi HOME 前置任务 | Task 1 |
| 2 质量声明格式 | Task 4（校验）、Task 5（迁移） |
| 3 grade 子命令与 grader 契约 | Task 6（prompt）、Task 7（解析）、Task 8（编排与 CLI） |
| 4 报告形态 | Task 10 |
| 5 方差标定 | Task 9（聚合）、Task 11 Step 5（实跑） |
| 5 返修回路 | Task 9 + Task 10 的 unstable 清单与未冻结警告（产出工作清单）；人工返修本身不是代码 |
| 覆盖策略 · 按需增量 | Task 8 的 `selectGradeCells`（无声明即跳过） |
| 覆盖策略 · 冷启动覆盖 | Task 5 |
| 验收判据 1-10 | 1→Task 11 Step 2；2→Step 3；3→Task 5；4→Task 8 测试；5→Task 7 测试；6→Task 10 测试；7→Task 10 测试；8→Task 9 + Task 11 Step 5；9→Step 4；10→Task 10 Step 6 |

**未被任务覆盖的 spec 内容：** 「覆盖策略」里"skill 改动 → contentHash 变 → 声明自动解冻"这条。现有 `coverage.js` 已有 contentHash staleness 机制，但把它接到 `frozen` 字段上需要改写 evals.json（写回 `frozen: null`），属于写操作，风险与收益不匹配。**本轮只做到「未冻结则警告」（Task 10），自动解冻留到实际用起来之后再定。** 这是有意的缺口，不是遗漏。
