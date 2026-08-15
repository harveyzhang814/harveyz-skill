# Skill 跨平台 Harness 第一期实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让同一个 skill 在 claude / pi / hermes 三个平台上以 native 与 inject 两种模式跑起来，产出结构一致的 `RunRecord`，并保证 jail 隔离有效、选择机制不掉覆盖率。**第一期不做任何评估。**

**Architecture:** `tools/skill-harness/` 下一套 ESM 模块。纯函数层（`select` / `parse` / `record` / `jail.buildEnv`）承担全部逻辑并被单测覆盖；副作用层（`launch` / `install` / `collect`）只做起进程与文件搬运。三个适配器各自持有 profile、jail 构造、install 策略、compensation，被 runner 按矩阵调度。

**Tech Stack:** Node ≥ 18，ESM，`fs-extra`、`chalk`（仓库已有依赖），`node:test` + `node:assert/strict` 作测试框架，`node:child_process` 起子进程。不引入新依赖。

**Spec:** [`docs/superpowers/specs/2026-08-14-skill-harness-adapter-design.md`](../specs/2026-08-14-skill-harness-adapter-design.md)
实测依据：[`docs/superpowers/specs/measurements/2026-08-14-native-vs-inject.md`](../specs/measurements/2026-08-14-native-vs-inject.md)

## Global Constraints

这些约束对**每一个** task 都生效，不再逐条重复：

- **代码风格**：ESM（`import`/`export`），**不写分号**，单引号，2 空格缩进，与 `lib/installer.js`、`lib/targets.js` 一致。
- **测试运行方式**：`node --test tests/harness/<file>.test.mjs`。断言用 `import assert from 'node:assert/strict'`，测试用 `import { test } from 'node:test'`。
- **工作目录**：worktree `/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/qm-research`，分支 `doc/qm-research`。所有命令从该目录运行，不 `cd` 到主仓。
- **提交规范**：Conventional Commits，类型限 `feat|fix|chore|docs|refactor|test|style|perf`，**首行 ≤ 80 字符**（仓库 hook 强制）。分支已存在，不新建分支。
- **`parse` 必须是纯函数**：不碰进程、不碰文件系统、不读 `process.env`。输入字符串，输出对象。这是 spec 唯一的硬约束。
- **jail 目录名必须中性**：`mkdtemp` 前缀固定为 `skill-harness-`，禁止出现 `jail` / `inject` / `probe` 等词（spec 风险 8：模型会因目录名把注入内容判为 prompt injection）。
- **凭证不得落盘**：`CLAUDE_CODE_OAUTH_TOKEN` / `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` / `MINIMAX_CN_API_KEY` 只在构造子进程 env 时现取，不写进 `RunRecord`、不写进任何 artifact、`dry-run` 输出一律打码为 `***`。
- **产物目录**：`$HOME/.hskill/skill-harness/<run-id>/`，不写进项目目录。
- **第一期平台集合**：`['claude', 'pi', 'hermes']`。模式集合：`['native', 'inject']`。
- **模型必填**：`--model` 无默认值，缺失即报错退出。

---

## File Structure

```
tools/skill-harness/
  select.js                    # 纯函数：默认 → matrix.json → CLI，产出格子清单
  matrix.json                  # 稀疏声明：只记不该全量跑的 skill，reason 必填
  jail.js                      # env 白名单构造（纯）+ mkdtemp/cleanup（副作用）+ 凭证取用
  profiles.js                  # 三张 PlatformProfile 表，L1 快照的对象
  record.js                    # RunRecord 规范化：null 填充、unavailable、stderr 尾部截断
  prompt.js                    # 纯函数：两种模式的 prompt 组装（含路径补偿行）
  parse/
    claude-code-jsonl.js       # claude 与 hermes trace 共用
    pi-jsonl.js                # pi --mode json
  adapters/
    claude.js                  # profile + jail + install + launch + collect(null) + parse
    pi.js
    hermes.js
  runner.js                    # 矩阵分发、并发、产物落盘
  coverage.js                  # 读历史产物 → 每格最近运行时间 + contentHash 是否过期
  report.js                    # 三态矩阵渲染
  cli.js                       # skill-harness run|dry-run|report|coverage
  probe/probe-anchor/          # 框架自检 skill（从 specs/measurements/ 复制）
    SKILL.md
    references/token.md

tests/harness/
  fixtures/
    claude/probe-anchor-native.jsonl   # 已存在（真实抓取）
    pi/probe-anchor-native.jsonl       # 已存在（真实抓取，已剔流式增量）
  select.test.mjs
  profile.test.mjs
  parse.test.mjs
  record.test.mjs
  prompt.test.mjs
  jail.test.mjs
  coverage.test.mjs
  e2e.test.mjs                 # 真模型端到端，默认 skip，靠环境变量开启
```

**为什么这样切**：纯函数各自独立成文件，每个都能被单测完全覆盖且不需要任何 mock；副作用集中在 `jail.js` / `adapters/*.js` / `runner.js` 三处。`parse/` 按格式分而不按平台分——claude 与 hermes 共用 Claude Code JSONL，这是 spec 认定的收敛点。

---

## Task 1: 选择器与 matrix 声明

**Files:**
- Create: `tools/skill-harness/select.js`
- Create: `tools/skill-harness/matrix.json`
- Create: `tests/harness/select.test.mjs`
- Modify: `package.json:10`（`scripts.test`）

**Interfaces:**
- Consumes: `skills-index.json`（仓库根，已存在，`skills[]` 每项有 `path` 与 `bundle`）
- Produces:
  - `PHASE1_PLATFORMS = ['claude', 'pi', 'hermes']`
  - `MODES = ['native', 'inject']`
  - `validateMatrix(matrix) -> string[]`（错误信息数组，空数组表示合法）
  - `selectCells({ skills, matrix, opts }) -> Cell[]`
  - `Cell = { skill, bundle, platform, mode, state, reason, overridesDeclaration }`
  - `state ∈ 'run' | 'declared-na' | 'not-run'`

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/select.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { selectCells, validateMatrix, PHASE1_PLATFORMS, MODES } from '../../tools/skill-harness/select.js'

const SKILLS = [
  { path: 'mint/learn-skill', bundle: 'mint' },
  { path: 'research/extract-url', bundle: 'research' },
  { path: 'mint/runby-opencode', bundle: 'mint' },
]

const EMPTY = { overrides: [] }

test('默认：全部 skill × 3 平台 × 2 模式，全部 run', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.every(c => c.state === 'run'))
})

test('声明 platforms: [] 使该 skill 全部平台变 declared-na 并带 reason', () => {
  const matrix = { overrides: [{ skill: 'mint/runby-opencode', platforms: [], reason: '它驱动的是 opencode' }] }
  const cells = selectCells({ skills: SKILLS, matrix })
  const mine = cells.filter(c => c.skill === 'mint/runby-opencode')
  assert.equal(mine.length, PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(mine.every(c => c.state === 'declared-na'))
  assert.ok(mine.every(c => c.reason === '它驱动的是 opencode'))
})

test('声明 platforms 白名单：表内平台 run，表外 declared-na', () => {
  const matrix = { overrides: [{ skill: 'research/extract-url', platforms: ['claude'], reason: '依赖 claude 后台通道' }] }
  const cells = selectCells({ skills: SKILLS, matrix })
  const mine = cells.filter(c => c.skill === 'research/extract-url')
  assert.ok(mine.filter(c => c.platform === 'claude').every(c => c.state === 'run'))
  assert.ok(mine.filter(c => c.platform !== 'claude').every(c => c.state === 'declared-na'))
})

test('--skill 过滤：未选中的格子是 not-run，不是被删掉', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { skills: ['mint/learn-skill'] } })
  assert.equal(cells.length, 3 * PHASE1_PLATFORMS.length * MODES.length)
  assert.ok(cells.filter(c => c.skill === 'mint/learn-skill').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.skill !== 'mint/learn-skill').every(c => c.state === 'not-run'))
})

test('--bundle 过滤复用 skills-index.json 的 bundle 字段', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { bundles: ['research'] } })
  assert.ok(cells.filter(c => c.bundle === 'research').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.bundle !== 'research').every(c => c.state === 'not-run'))
})

test('--platform 过滤', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { platforms: ['pi'] } })
  assert.ok(cells.filter(c => c.platform === 'pi').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.platform !== 'pi').every(c => c.state === 'not-run'))
})

test('--mode 过滤', () => {
  const cells = selectCells({ skills: SKILLS, matrix: EMPTY, opts: { modes: ['native'] } })
  assert.ok(cells.filter(c => c.mode === 'native').every(c => c.state === 'run'))
  assert.ok(cells.filter(c => c.mode === 'inject').every(c => c.state === 'not-run'))
})

test('CLI 显式指定平台可覆盖声明，但打 overridesDeclaration 标记', () => {
  const matrix = { overrides: [{ skill: 'mint/runby-opencode', platforms: [], reason: 'r' }] }
  const cells = selectCells({ skills: SKILLS, matrix, opts: { platforms: ['claude'] } })
  const mine = cells.filter(c => c.skill === 'mint/runby-opencode' && c.platform === 'claude')
  assert.ok(mine.every(c => c.state === 'run'))
  assert.ok(mine.every(c => c.overridesDeclaration === true))
})

test('validateMatrix: reason 缺失或空白即报错', () => {
  assert.deepEqual(validateMatrix({ overrides: [] }), [])
  const bad = { overrides: [{ skill: 'a/b', platforms: [] }] }
  assert.equal(validateMatrix(bad).length, 1)
  assert.match(validateMatrix(bad)[0], /reason/)
  const blank = { overrides: [{ skill: 'a/b', platforms: [], reason: '   ' }] }
  assert.equal(validateMatrix(blank).length, 1)
})

test('validateMatrix: platforms 必须是数组', () => {
  const bad = { overrides: [{ skill: 'a/b', platforms: 'claude', reason: 'r' }] }
  assert.ok(validateMatrix(bad).some(e => /platforms/.test(e)))
})

test('仓库自带的 matrix.json 合法', async () => {
  const { default: matrix } = await import('../../tools/skill-harness/matrix.json', { with: { type: 'json' } })
  assert.deepEqual(validateMatrix(matrix), [])
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/select.test.mjs`
Expected: FAIL —— `Cannot find module '.../tools/skill-harness/select.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/select.js`：

```js
export const PHASE1_PLATFORMS = ['claude', 'pi', 'hermes']
export const MODES = ['native', 'inject']

// 校验 matrix.json。返回错误信息数组，空数组表示合法。
// reason 必填是本模块唯一的硬约束：一条没有理由的排除，和忘了测无法区分。
export function validateMatrix(matrix) {
  const errors = []
  const overrides = matrix?.overrides ?? []
  overrides.forEach((o, i) => {
    const tag = `overrides[${i}]${o?.skill ? ` (${o.skill})` : ''}`
    if (!o?.skill) errors.push(`${tag}: "skill" is required`)
    if (!Array.isArray(o?.platforms)) errors.push(`${tag}: "platforms" must be an array`)
    if (!o?.reason || !String(o.reason).trim())
      errors.push(`${tag}: "reason" is required — an exclusion without a stated reason is indistinguishable from forgetting to test`)
  })
  return errors
}

// 纯函数。产出全矩阵每一格及其状态，被过滤掉的格子保留为 not-run 而非删除，
// 这样报告永远拿得到完整矩阵，"没跑"无法伪装成"通过"。
export function selectCells({ skills, matrix = { overrides: [] }, opts = {} }) {
  const declared = new Map((matrix.overrides ?? []).map(o => [o.skill, o]))
  const wantSkills = new Set(opts.skills ?? [])
  const wantBundles = new Set(opts.bundles ?? [])
  const wantPlatforms = new Set(opts.platforms ?? PHASE1_PLATFORMS)
  const wantModes = new Set(opts.modes ?? MODES)
  const explicitPlatform = Array.isArray(opts.platforms)
  const noSkillFilter = wantSkills.size === 0 && wantBundles.size === 0

  const cells = []
  for (const s of skills) {
    const override = declared.get(s.path)
    const skillSelected = noSkillFilter || wantSkills.has(s.path) || wantBundles.has(s.bundle)
    for (const platform of PHASE1_PLATFORMS) {
      const declaredOut = Boolean(override) && !override.platforms.includes(platform)
      for (const mode of MODES) {
        const cell = { skill: s.path, bundle: s.bundle, platform, mode, overridesDeclaration: false, reason: null }
        const cliSelected = skillSelected && wantPlatforms.has(platform) && wantModes.has(mode)
        if (declaredOut && explicitPlatform && wantPlatforms.has(platform) && skillSelected && wantModes.has(mode)) {
          cell.state = 'run'
          cell.overridesDeclaration = true
          cell.reason = override.reason
        } else if (declaredOut) {
          cell.state = 'declared-na'
          cell.reason = override.reason
        } else if (!cliSelected) {
          cell.state = 'not-run'
        } else {
          cell.state = 'run'
        }
        cells.push(cell)
      }
    }
  }
  return cells
}
```

- [ ] **Step 4: 写 matrix.json**

创建 `tools/skill-harness/matrix.json`：

```json
{
  "overrides": [
    {
      "skill": "mint/runby-opencode",
      "platforms": [],
      "reason": "这个 skill 的作用就是驱动 opencode 去跑别的 skill，被测对象是 opencode 而不是它自己，放进矩阵会自我指涉"
    }
  ]
}
```

- [ ] **Step 5: 接入 npm test**

修改 `package.json` 的 `scripts.test`，把 `node --test tests/mcp.test.mjs` 换成同时跑 harness 测试：

```json
"test": "bats tests/ && bash scripts/run-skill-tests.sh && node --test tests/mcp.test.mjs tests/harness/*.test.mjs"
```

- [ ] **Step 6: 运行测试确认通过**

Run: `node --test tests/harness/select.test.mjs`
Expected: PASS，11 个测试全绿

Run: `npm test`
Expected: 全绿（确认没有破坏既有测试）

- [ ] **Step 7: 提交**

```bash
git add tools/skill-harness/select.js tools/skill-harness/matrix.json tests/harness/select.test.mjs package.json
git commit -m "feat(harness): 选择器与 matrix 声明，reason 必填"
```

---

## Task 2: jail 环境构造

**Files:**
- Create: `tools/skill-harness/jail.js`
- Create: `tests/harness/jail.test.mjs`

**Interfaces:**
- Consumes: 无（不依赖前序 task）
- Produces:
  - `ENV_WHITELIST: string[]`
  - `SECRET_KEYS: Set<string>`
  - `buildEnv(source, extra) -> object`（纯函数）
  - `redactEnv(env) -> object`（纯函数）
  - `createJail() -> Promise<{ dir, cleanup }>`
  - `claudeOAuthToken() -> string`
  - `readEnvFile(path) -> object`（解析 `KEY=VALUE` 形式的 `.env`）

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/jail.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv, redactEnv, createJail, ENV_WHITELIST, SECRET_KEYS, readEnvFile } from '../../tools/skill-harness/jail.js'

test('buildEnv: 白名单内的变量透传', () => {
  const env = buildEnv({ PATH: '/usr/bin', LANG: 'en_US.UTF-8' })
  assert.equal(env.PATH, '/usr/bin')
  assert.equal(env.LANG, 'en_US.UTF-8')
})

test('buildEnv: 白名单外的变量一律不透传', () => {
  const env = buildEnv({ PATH: '/usr/bin', CLAUDECODE: '1', ANTHROPIC_MODEL: 'x', RANDOM_NEW_VAR: 'y' })
  assert.equal(env.CLAUDECODE, undefined)
  assert.equal(env.ANTHROPIC_MODEL, undefined)
  assert.equal(env.RANDOM_NEW_VAR, undefined)
})

test('buildEnv: source 里没有的白名单变量不会造出 undefined 键', () => {
  const env = buildEnv({ PATH: '/usr/bin' })
  assert.ok(!('HTTPS_PROXY' in env))
})

test('buildEnv: extra 覆盖并追加', () => {
  const env = buildEnv({ PATH: '/usr/bin' }, { HOME: '/tmp/x', CLAUDE_CONFIG_DIR: '/tmp/x/.claude' })
  assert.equal(env.HOME, '/tmp/x')
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/x/.claude')
  assert.equal(env.PATH, '/usr/bin')
})

test('ENV_WHITELIST 是整表快照，新增项必须来这里登记', () => {
  assert.deepEqual(ENV_WHITELIST, [
    'PATH', 'TMPDIR', 'LANG', 'LC_ALL',
    'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS',
    'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'ALL_PROXY',
  ])
})

test('redactEnv: 凭证打码，其余原样', () => {
  const red = redactEnv({ PATH: '/usr/bin', CLAUDE_CODE_OAUTH_TOKEN: 'sk-ant-oat01-secret', ANTHROPIC_API_KEY: 'k' })
  assert.equal(red.PATH, '/usr/bin')
  assert.equal(red.CLAUDE_CODE_OAUTH_TOKEN, '***')
  assert.equal(red.ANTHROPIC_API_KEY, '***')
})

test('SECRET_KEYS 覆盖四个凭证变量', () => {
  assert.deepEqual([...SECRET_KEYS].sort(), [
    'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'MINIMAX_CN_API_KEY',
  ])
})

test('createJail: 目录名中性，不含 jail/inject/probe', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const base = path.basename(dir)
    assert.match(base, /^skill-harness-/)
    assert.doesNotMatch(base, /jail|inject|probe/i)
    assert.ok(await fs.pathExists(dir))
  } finally {
    await cleanup()
  }
})

test('createJail: cleanup 之后目录消失', async () => {
  const { dir, cleanup } = await createJail()
  await cleanup()
  assert.equal(await fs.pathExists(dir), false)
})

test('readEnvFile: 解析 KEY=VALUE，忽略注释与空行，去掉引号', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const p = path.join(dir, '.env')
    await fs.writeFile(p, '# comment\n\nFOO=bar\nQUOTED="baz"\nSINGLE=\'qux\'\nWITH_EQ=a=b\n')
    const env = readEnvFile(p)
    assert.equal(env.FOO, 'bar')
    assert.equal(env.QUOTED, 'baz')
    assert.equal(env.SINGLE, 'qux')
    assert.equal(env.WITH_EQ, 'a=b')
    assert.equal(env['# comment'], undefined)
  } finally {
    await cleanup()
  }
})

test('readEnvFile: 文件不存在返回空对象', () => {
  assert.deepEqual(readEnvFile('/nonexistent/path/.env'), {})
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/jail.test.mjs`
Expected: FAIL —— `Cannot find module '.../tools/skill-harness/jail.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/jail.js`：

```js
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'

// 白名单，不是黑名单：新出现的环境变量默认不通过。分组抄 QM 的 CLAUDE_ENV_PASSTHROUGH。
export const ENV_WHITELIST = [
  'PATH', 'TMPDIR', 'LANG', 'LC_ALL',
  'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS',
  'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'ALL_PROXY',
]

export const SECRET_KEYS = new Set([
  'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'MINIMAX_CN_API_KEY',
])

export function buildEnv(source, extra = {}) {
  const env = {}
  for (const name of ENV_WHITELIST) {
    if (source[name] !== undefined) env[name] = source[name]
  }
  return { ...env, ...extra }
}

export function redactEnv(env) {
  return Object.fromEntries(
    Object.entries(env).map(([k, v]) => [k, SECRET_KEYS.has(k) ? '***' : v]),
  )
}

// 目录名必须中性：模型看得见 cwd，带 jail/inject 字样会被判成 prompt injection。
export async function createJail() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'skill-harness-'))
  return { dir, cleanup: () => fs.remove(dir) }
}

// HOME 重定向后 claude 读不到凭证文件也读不到 keychain，必须显式注入 token。
export function claudeOAuthToken() {
  const raw = execFileSync('security', ['find-generic-password', '-s', 'Claude Code-credentials', '-w'], { encoding: 'utf8' })
  return JSON.parse(raw).claudeAiOauth.accessToken
}

export function readEnvFile(file) {
  if (!fs.existsSync(file)) return {}
  const out = {}
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq < 1) continue
    const key = trimmed.slice(0, eq).trim()
    let value = trimmed.slice(eq + 1).trim()
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1)
    }
    out[key] = value
  }
  return out
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/jail.test.mjs`
Expected: PASS，12 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/jail.js tests/harness/jail.test.mjs
git commit -m "feat(harness): jail 环境白名单构造与凭证打码"
```

---

## Task 3: 差异表与 L1 整表快照

**Files:**
- Create: `tools/skill-harness/profiles.js`
- Create: `tests/harness/profile.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `claudeProfile` / `piProfile` / `hermesProfile`
  - `PROFILES = [claudeProfile, piProfile, hermesProfile]`（顺序固定，L1 断言依赖它）

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/profile.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PROFILES } from '../../tools/skill-harness/profiles.js'

// 整表 deepEqual，不是三个独立 equal。失败时一次看到全表；
// 新增平台必然让这些断言变红，强制作者来这里登记。这是注册表守卫模式。

test('L1: id 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.id), ['claude', 'pi', 'hermes'])
})

test('L1: skillChannel 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.skillChannel), ['skill-dir', 'explicit-flag', 'skill-dir'])
})

test('L1: builtinSkillFloor 整表（2026-08-14 实测，变了必须重新实测再改）', () => {
  assert.deepEqual(PROFILES.map(p => p.builtinSkillFloor), [16, 0, 0])
})

test('L1: injection 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.injection), ['append-system-prompt', 'append-system-prompt', 'prompt-only'])
})

test('L1: processChannel 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.processChannel), ['inline', 'inline', 'collect'])
})

test('L1: transcriptFormat 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.transcriptFormat), ['claude-code-jsonl', 'pi-jsonl', 'claude-code-jsonl'])
})

test('L1: compensation 逐字整表', () => {
  assert.deepEqual(PROFILES.map(p => p.compensation), ['', '', ''])
})

test('L1: capabilities 整表', () => {
  assert.deepEqual(
    PROFILES.map(p => [...p.capabilities].sort()),
    [
      ['cost-cap', 'structured-output', 'system-prompt-append', 'tool-allowlist', 'tool-trace', 'usage'],
      ['structured-output', 'system-prompt-append', 'tool-allowlist', 'tool-trace', 'usage'],
      ['structured-output', 'tool-allowlist', 'tool-trace', 'usage'],
    ],
  )
})

test('L1: isolation 整表', () => {
  assert.deepEqual(PROFILES.map(p => p.isolation), [
    ['HOME', 'CLAUDE_CONFIG_DIR', '--setting-sources user'],
    ['-ns', '-ne', '-np', '--no-themes', '-nc', '--session-dir'],
    ['HOME', '--safe-mode'],
  ])
})

test('每个 profile 的字段集合一致', () => {
  const keys = PROFILES.map(p => Object.keys(p).sort().join(','))
  assert.equal(new Set(keys).size, 1, `profiles have divergent field sets: ${keys.join(' | ')}`)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/profile.test.mjs`
Expected: FAIL —— `Cannot find module '.../tools/skill-harness/profiles.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/profiles.js`：

```js
// 差异表。capabilities 不驱动运行时分派——它是两件事：
// 写在代码里不会腐烂的可执行文档，以及配合 L1 整表快照的回归护栏。
// 唯一的生产消费者是 report.js（见 spec 风险 1：没有消费者的表会腐烂成谎言）。

export const claudeProfile = {
  id: 'claude',
  skillChannel: 'skill-dir',
  builtinSkillFloor: 16,
  injection: 'append-system-prompt',
  qualityChannel: 'stdout-json',
  processChannel: 'inline',
  transcriptFormat: 'claude-code-jsonl',
  isolation: ['HOME', 'CLAUDE_CONFIG_DIR', '--setting-sources user'],
  capabilities: new Set(['tool-trace', 'usage', 'cost-cap', 'tool-allowlist', 'structured-output', 'system-prompt-append']),
  compensation: '',
}

export const piProfile = {
  id: 'pi',
  skillChannel: 'explicit-flag',
  builtinSkillFloor: 0,
  injection: 'append-system-prompt',
  qualityChannel: 'stdout-json',
  processChannel: 'inline',
  transcriptFormat: 'pi-jsonl',
  isolation: ['-ns', '-ne', '-np', '--no-themes', '-nc', '--session-dir'],
  capabilities: new Set(['tool-trace', 'usage', 'tool-allowlist', 'structured-output', 'system-prompt-append']),
  compensation: '',
}

export const hermesProfile = {
  id: 'hermes',
  skillChannel: 'skill-dir',
  builtinSkillFloor: 0,
  injection: 'prompt-only',
  qualityChannel: 'stdout-text',
  processChannel: 'collect',
  transcriptFormat: 'claude-code-jsonl',
  isolation: ['HOME', '--safe-mode'],
  capabilities: new Set(['tool-trace', 'usage', 'tool-allowlist', 'structured-output']),
  compensation: '',
}

export const PROFILES = [claudeProfile, piProfile, hermesProfile]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/profile.test.mjs`
Expected: PASS，10 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/profiles.js tests/harness/profile.test.mjs
git commit -m "feat(harness): 三平台差异表与 L1 整表快照"
```

---

## Task 4: prompt 组装（两种模式）

**Files:**
- Create: `tools/skill-harness/prompt.js`
- Create: `tests/harness/prompt.test.mjs`

**Interfaces:**
- Consumes: 无
- Produces:
  - `stripFrontmatter(md) -> string`
  - `anchorLine(skillDir) -> string`
  - `buildPrompt({ mode, injection, skillBody, skillDir, compensation, task }) -> { systemAppend, positional }`

**说明**：native 模式 prompt 里没有 skill 正文（正文由平台原生通道加载）；inject 模式必须带路径补偿行——实测缺了它三个平台一律断锚。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/prompt.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildPrompt, stripFrontmatter, anchorLine } from '../../tools/skill-harness/prompt.js'

const MD = `---
name: probe-anchor
description: "d"
---

# Anchor Probe

body text here
`

test('stripFrontmatter: 去掉 YAML frontmatter，保留正文', () => {
  const body = stripFrontmatter(MD)
  assert.ok(body.includes('# Anchor Probe'))
  assert.ok(body.includes('body text here'))
  assert.ok(!body.includes('name: probe-anchor'))
  assert.ok(!body.includes('---'))
})

test('stripFrontmatter: 无 frontmatter 时原样返回', () => {
  assert.equal(stripFrontmatter('# Just A Title\n').trim(), '# Just A Title')
})

test('anchorLine: 输出绝对路径', () => {
  assert.equal(anchorLine('/tmp/x/probe-anchor'), 'This skill directory is: /tmp/x/probe-anchor')
})

test('native: systemAppend 只含 compensation，不含正文', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'native', injection: 'append-system-prompt',
    skillBody: stripFrontmatter(MD), skillDir: '/tmp/x/probe-anchor',
    compensation: 'COMP', task: 'run anchor probe',
  })
  assert.equal(systemAppend, 'COMP')
  assert.equal(positional, 'run anchor probe')
  assert.ok(!systemAppend.includes('body text here'))
})

test('native: compensation 为空时 systemAppend 为 null', () => {
  const { systemAppend } = buildPrompt({
    mode: 'native', injection: 'append-system-prompt',
    skillBody: 'x', skillDir: '/d', compensation: '', task: 't',
  })
  assert.equal(systemAppend, null)
})

test('native + prompt-only: 正文不进 positional', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'native', injection: 'prompt-only',
    skillBody: stripFrontmatter(MD), skillDir: '/d', compensation: 'COMP', task: 'do it',
  })
  assert.equal(systemAppend, null)
  assert.equal(positional, 'COMP\n\ndo it')
  assert.ok(!positional.includes('body text here'))
})

test('inject + append-system-prompt: 补偿行 + 正文进 system，任务进 positional', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'inject', injection: 'append-system-prompt',
    skillBody: stripFrontmatter(MD), skillDir: '/tmp/x/probe-anchor',
    compensation: 'COMP', task: 'run anchor probe',
  })
  assert.ok(systemAppend.includes('COMP'))
  assert.ok(systemAppend.includes('This skill directory is: /tmp/x/probe-anchor'))
  assert.ok(systemAppend.includes('body text here'))
  assert.equal(positional, 'run anchor probe')
})

test('inject: 路径补偿行必须存在——缺了它三平台一律断锚', () => {
  const { systemAppend } = buildPrompt({
    mode: 'inject', injection: 'append-system-prompt',
    skillBody: 'b', skillDir: '/abs/dir', compensation: '', task: 't',
  })
  assert.ok(systemAppend.includes('This skill directory is: /abs/dir'))
})

test('inject + prompt-only: 全部拼进 positional，用 --- 分隔任务', () => {
  const { systemAppend, positional } = buildPrompt({
    mode: 'inject', injection: 'prompt-only',
    skillBody: 'BODY', skillDir: '/abs/dir', compensation: 'COMP', task: 'TASK',
  })
  assert.equal(systemAppend, null)
  assert.ok(positional.startsWith('COMP'))
  assert.ok(positional.includes('This skill directory is: /abs/dir'))
  assert.ok(positional.includes('BODY'))
  assert.ok(positional.endsWith('TASK'))
  assert.ok(positional.includes('\n---\n'))
})

test('未知 mode 抛错', () => {
  assert.throws(() => buildPrompt({ mode: 'bogus', injection: 'prompt-only', skillBody: 'b', skillDir: '/d', compensation: '', task: 't' }), /bogus/)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/prompt.test.mjs`
Expected: FAIL —— `Cannot find module '.../tools/skill-harness/prompt.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/prompt.js`：

```js
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
    const parts = head.length ? [head.join('\n\n'), '---', task] : [task]
    return { systemAppend: null, positional: parts.join('\n') }
  }

  return { systemAppend: head.length ? head.join('\n\n') : null, positional: task }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/prompt.test.mjs`
Expected: PASS，10 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/prompt.js tests/harness/prompt.test.mjs
git commit -m "feat(harness): 两种模式的 prompt 组装与路径补偿"
```

---

## Task 5: Claude Code JSONL 解析器（claude 与 hermes 共用）

**Files:**
- Create: `tools/skill-harness/parse/claude-code-jsonl.js`
- Create: `tests/harness/parse.test.mjs`
- Read (已存在，真实抓取): `tests/harness/fixtures/claude/probe-anchor-native.jsonl`

**Interfaces:**
- Consumes: 无
- Produces: `parseClaudeCodeJsonl(raw, { skillName }) -> Partial<RunRecord>`

返回字段（后续 task 依赖这些确切名字，与 `parsePiJsonl` 保持同名同型）：
`{ sessionId, model, provider, reply, triggered, toolCalls, turns, usage, visibleSkills, isError }`
其中 `toolCalls: Array<{ name, args, ok, seq }>`，
`usage: { input, output, cacheRead, cacheWrite, totalTokens, costUsd }`。
`provider` 在 claude 的输出里不存在，恒为 `null`——显式给出而不是让它 `undefined`，
这样两个解析器的返回形状严格一致，`makeRecord` 不需要为平台分支。

**fixture 字段依据**（2026-08-14 真实抓取，见 measurements 文档）：
`system` 行有 `session_id` / `model` / `skills[]`；`assistant` 行 `message.content[]` 内 `tool_use` 块有 `name` / `input`；`result` 行有 `result` / `usage` / `total_cost_usd` / `num_turns` / `is_error`。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/parse.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseClaudeCodeJsonl } from '../../tools/skill-harness/parse/claude-code-jsonl.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const CLAUDE_FIXTURES = path.join(here, 'fixtures/claude')

function fixture(name) {
  return fs.readFileSync(path.join(CLAUDE_FIXTURES, name), 'utf8')
}

test('空集合保险：claude fixture 目录非空', () => {
  const files = fs.readdirSync(CLAUDE_FIXTURES).filter(f => f.endsWith('.jsonl'))
  assert.ok(files.length > 0, 'expected at least one claude fixture')
})

test('claude: 解析出 sessionId 与 model', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.match(r.sessionId, /^[0-9a-f-]{36}$/)
  assert.equal(r.model, 'claude-sonnet-5')
})

test('claude: reply 取 result 行的 result 字段', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.reply, 'BODY=BODY-4B21E8\nFILE=ANCHOR-7F3A9C')
})

test('claude: triggered 判据是 Skill 工具且 input.skill 匹配', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.triggered, true)
})

test('claude: skillName 不匹配时 triggered 为 false（负向）', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'some-other-skill' })
  assert.equal(r.triggered, false)
})

test('claude: toolCalls 按出现顺序编号，含 Skill 与 Read', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.deepEqual(r.toolCalls.map(t => t.name), ['Skill', 'Read'])
  assert.deepEqual(r.toolCalls.map(t => t.seq), [0, 1])
  assert.equal(r.toolCalls[0].args.skill, 'probe-anchor')
})

test('claude: turns 取 num_turns', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.turns, 4)
})

test('claude: usage 归一化字段名', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.usage.input, 5)
  assert.equal(r.usage.output, 222)
  assert.equal(r.usage.cacheRead, 95002)
  assert.equal(r.usage.cacheWrite, 3512)
  assert.equal(r.usage.totalTokens, 5 + 222 + 95002 + 3512)
  assert.ok(r.usage.costUsd > 0)
})

test('claude: visibleSkills 来自 system 行，是 builtinSkillFloor 的 ground truth', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.ok(Array.isArray(r.visibleSkills))
  assert.equal(r.visibleSkills.length, 17)
  assert.ok(r.visibleSkills.includes('probe-anchor'))
})

test('claude: provider 恒为 null，与 pi 解析器形状一致', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.provider, null)
})

test('claude: isError 取 result 行的 is_error', () => {
  const r = parseClaudeCodeJsonl(fixture('probe-anchor-native.jsonl'), { skillName: 'probe-anchor' })
  assert.equal(r.isError, false)
})

test('claude: 空输入不抛错，字段全 null', () => {
  const r = parseClaudeCodeJsonl('', { skillName: 'x' })
  assert.equal(r.reply, null)
  assert.equal(r.sessionId, null)
  assert.equal(r.usage, null)
  assert.deepEqual(r.toolCalls, [])
})

test('claude: 非法 JSON 行被跳过而不是让整个解析崩掉', () => {
  const raw = 'not json\n' + fixture('probe-anchor-native.jsonl')
  const r = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  assert.equal(r.reply, 'BODY=BODY-4B21E8\nFILE=ANCHOR-7F3A9C')
})

test('parse 是纯函数：同一输入两次调用结果 deepEqual', () => {
  const raw = fixture('probe-anchor-native.jsonl')
  const a = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  const b = parseClaudeCodeJsonl(raw, { skillName: 'probe-anchor' })
  assert.deepEqual(a, b)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/parse.test.mjs`
Expected: FAIL —— `Cannot find module '.../parse/claude-code-jsonl.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/parse/claude-code-jsonl.js`：

```js
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

  const triggered = toolCalls.some(t => t.name === 'Skill' && t.args?.skill === skillName)

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
    toolCalls,
    turns: result?.num_turns ?? null,
    usage,
    visibleSkills: system?.skills ?? null,
    isError: result?.is_error ?? null,
  }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/parse.test.mjs`
Expected: PASS，14 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/parse/claude-code-jsonl.js tests/harness/parse.test.mjs
git commit -m "feat(harness): Claude Code JSONL 解析器，claude 与 hermes 共用"
```

---

## Task 6: pi JSONL 解析器

**Files:**
- Create: `tools/skill-harness/parse/pi-jsonl.js`
- Modify: `tests/harness/parse.test.mjs`（追加 pi 段）
- Read (已存在，真实抓取): `tests/harness/fixtures/pi/probe-anchor-native.jsonl`

**Interfaces:**
- Consumes: 无
- Produces: `parsePiJsonl(raw, { skillDir }) -> Partial<RunRecord>`
  返回字段与 `parseClaudeCodeJsonl` **同名同型**：`{ sessionId, model, reply, triggered, toolCalls, turns, usage, visibleSkills, isError }`。

**关键差异**：pi 没有 `Skill` 工具。它把 skill 索引放进 system prompt，由模型自己用 `read` 工具读 `SKILL.md`（实测确认，与 QM `materialize.ts:402` 一致）。因此 `triggered` 判据是 `toolName === 'read'` 且 `args.path` 以 `<skillDir>/SKILL.md` 结尾。`visibleSkills` 在 pi 输出里没有，恒为 `null`。

- [ ] **Step 1: 写失败测试**

在 `tests/harness/parse.test.mjs` 末尾追加：

```js
import { parsePiJsonl } from '../../tools/skill-harness/parse/pi-jsonl.js'

const PI_FIXTURES = path.join(here, 'fixtures/pi')
const PROBE_DIR = '/private/tmp/claude-501/-Users-harveyzhang96-Projects-harveyz-skill/aa316c5f-1656-4440-98b6-368ccbffcced/scratchpad/probe/probe-anchor'

function piFixture(name) {
  return fs.readFileSync(path.join(PI_FIXTURES, name), 'utf8')
}

test('空集合保险：pi fixture 目录非空', () => {
  const files = fs.readdirSync(PI_FIXTURES).filter(f => f.endsWith('.jsonl'))
  assert.ok(files.length > 0, 'expected at least one pi fixture')
})

test('pi: 解析出 sessionId', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.match(r.sessionId, /^[0-9a-f-]{36}$/)
})

test('pi: model 与 provider 从 message_end 读', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.model, 'MiniMax-M2.7')
  assert.equal(r.provider, 'minimax-cn')
})

test('pi: reply 取最后一条 assistant 消息的 text 块', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.ok(r.reply.includes('BODY=BODY-4B21E8'))
  assert.ok(r.reply.includes('FILE=ANCHOR-7F3A9C'))
})

test('pi: reply 不含 thinking 块', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.ok(!r.reply.includes('Now I need to print'))
})

test('pi: triggered 判据是 read 了该 skill 的 SKILL.md', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.triggered, true)
})

test('pi: skillDir 不匹配时 triggered 为 false（负向）', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: '/some/other/skill' })
  assert.equal(r.triggered, false)
})

test('pi: toolCalls 来自 tool_execution_start，ok 来自 tool_execution_end.isError', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.deepEqual(r.toolCalls.map(t => t.name), ['read', 'read'])
  assert.deepEqual(r.toolCalls.map(t => t.seq), [0, 1])
  assert.ok(r.toolCalls.every(t => t.ok === true))
  assert.ok(r.toolCalls[0].args.path.endsWith('SKILL.md'))
  assert.ok(r.toolCalls[1].args.path.endsWith('references/token.md'))
})

test('pi: usage 字段名已与规范一致，直接取末条 message_end', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.usage.input, 466)
  assert.equal(r.usage.output, 61)
  assert.equal(r.usage.cacheRead, 10720)
  assert.equal(r.usage.cacheWrite, 0)
  assert.equal(r.usage.totalTokens, 11247)
  assert.ok(r.usage.costUsd > 0)
})

test('pi: turns 取 turn_start 计数', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.turns, 3)
})

test('pi: visibleSkills 恒为 null——该平台不暴露这个信息', () => {
  const r = parsePiJsonl(piFixture('probe-anchor-native.jsonl'), { skillDir: PROBE_DIR })
  assert.equal(r.visibleSkills, null)
})

test('pi: message_update 流式增量被跳过，不产生额外 toolCalls', () => {
  const raw = piFixture('probe-anchor-native.jsonl')
  assert.ok(raw.includes('"message_update"'), 'fixture 应保留至少一条 message_update 以验证跳过逻辑')
  const r = parsePiJsonl(raw, { skillDir: PROBE_DIR })
  assert.equal(r.toolCalls.length, 2)
})

test('pi: 空输入不抛错', () => {
  const r = parsePiJsonl('', { skillDir: '/x' })
  assert.equal(r.reply, null)
  assert.deepEqual(r.toolCalls, [])
})

test('pi parse 是纯函数：同一输入两次调用 deepEqual', () => {
  const raw = piFixture('probe-anchor-native.jsonl')
  assert.deepEqual(parsePiJsonl(raw, { skillDir: PROBE_DIR }), parsePiJsonl(raw, { skillDir: PROBE_DIR }))
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/parse.test.mjs`
Expected: FAIL —— `Cannot find module '.../parse/pi-jsonl.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/parse/pi-jsonl.js`：

```js
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/parse.test.mjs`
Expected: PASS，28 个测试全绿（14 claude + 14 pi）

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/parse/pi-jsonl.js tests/harness/parse.test.mjs
git commit -m "feat(harness): pi JSONL 解析器，触发判据为 read SKILL.md"
```

---

## Task 7: RunRecord 规范化

**Files:**
- Create: `tools/skill-harness/record.js`
- Create: `tests/harness/record.test.mjs`

**Interfaces:**
- Consumes: `parseClaudeCodeJsonl` / `parsePiJsonl` 的输出形状（Task 5、6）
- Produces:
  - `STDERR_LIMIT = 16384`
  - `tailBytes(s, limit) -> string`
  - `makeRecord(input) -> RunRecord`
  - `RunRecord` 字段：`platform skill contentHash task repeat mode sessionId model provider modelMismatch builtinSkillFloor reply triggered toolCalls turns usage durationMs exitCode stderr unavailable`

`contentHash` 取自 `skills-index.json` 该 skill 的同名字段，随记录落盘。
`coverage.js`（Task 12）靠它判断「这条结论是不是已经过期」——skill 改过之后，
上次运行的结论就不再代表当前内容。缺了这个字段，coverage 的 stale 判定无从谈起。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/record.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { makeRecord, tailBytes, STDERR_LIMIT } from '../../tools/skill-harness/record.js'

const BASE = {
  platform: 'claude', skill: 'mint/learn-skill', contentHash: 'aaaa',
  task: 'do it', repeat: 0, mode: 'native',
  requestedModel: 'MiniMax-M2.7', durationMs: 1234, exitCode: 0, stderr: '',
  parsed: {
    sessionId: 's-1', model: 'MiniMax-M2.7', provider: null, reply: 'ok', triggered: true,
    toolCalls: [{ name: 'Read', args: {}, ok: true, seq: 0 }], turns: 2,
    usage: { input: 1, output: 2, cacheRead: 3, cacheWrite: 4, totalTokens: 10, costUsd: 0.5 },
    visibleSkills: ['mint/learn-skill', 'a', 'b'], isError: false,
  },
}

test('tailBytes: 短字符串原样返回', () => {
  assert.equal(tailBytes('abc', 10), 'abc')
})

test('tailBytes: 超长保留尾部而不是头部', () => {
  const s = 'x'.repeat(100) + 'TAIL'
  assert.ok(tailBytes(s, 10).endsWith('TAIL'))
  assert.equal(tailBytes(s, 10).length, 10)
})

test('STDERR_LIMIT 是 16KB', () => {
  assert.equal(STDERR_LIMIT, 16 * 1024)
})

test('makeRecord: 完整输入时 unavailable 为空', () => {
  const r = makeRecord(BASE)
  assert.deepEqual(r.unavailable, [])
  assert.equal(r.reply, 'ok')
  assert.equal(r.triggered, true)
  assert.equal(r.turns, 2)
})

test('makeRecord: 缺失字段进 unavailable，且值为 null 而非伪造', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, toolCalls: null, turns: null, usage: null } })
  assert.deepEqual(r.unavailable.sort(), ['toolCalls', 'turns', 'usage'])
  assert.equal(r.toolCalls, null)
  assert.equal(r.turns, null)
  assert.equal(r.usage, null)
})

test('makeRecord: triggered 为 null 时进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, triggered: null } })
  assert.ok(r.unavailable.includes('triggered'))
})

test('makeRecord: inject 模式 triggered 恒为 null 且不算缺失', () => {
  const r = makeRecord({ ...BASE, mode: 'inject', parsed: { ...BASE.parsed, triggered: false } })
  assert.equal(r.triggered, null)
  assert.ok(!r.unavailable.includes('triggered'))
})

test('makeRecord: model 一致时 modelMismatch 为 false', () => {
  assert.equal(makeRecord(BASE).modelMismatch, false)
})

test('makeRecord: model 不一致时 modelMismatch 为 true', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, model: 'claude-sonnet-5' } })
  assert.equal(r.modelMismatch, true)
})

test('makeRecord: model 为 null 时不判 mismatch，进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, model: null } })
  assert.equal(r.modelMismatch, false)
  assert.ok(r.unavailable.includes('model'))
})

test('makeRecord: builtinSkillFloor = visibleSkills 数减去被测 skill', () => {
  const r = makeRecord({ ...BASE, skillName: 'mint/learn-skill' })
  assert.equal(r.builtinSkillFloor, 2)
})

test('makeRecord: visibleSkills 为 null 时 builtinSkillFloor 为 null 并进 unavailable', () => {
  const r = makeRecord({ ...BASE, parsed: { ...BASE.parsed, visibleSkills: null } })
  assert.equal(r.builtinSkillFloor, null)
  assert.ok(r.unavailable.includes('builtinSkillFloor'))
})

test('makeRecord: stderr 截断到 16KB 尾部', () => {
  const r = makeRecord({ ...BASE, stderr: 'y'.repeat(STDERR_LIMIT + 500) + 'END' })
  assert.equal(r.stderr.length, STDERR_LIMIT)
  assert.ok(r.stderr.endsWith('END'))
})

test('makeRecord: 记录里不出现任何凭证字段', () => {
  const r = makeRecord(BASE)
  const json = JSON.stringify(r)
  assert.ok(!/OAUTH|API_KEY|AUTH_TOKEN/i.test(json))
})

test('makeRecord: contentHash 透传，coverage 的 stale 判定靠它', () => {
  assert.equal(makeRecord(BASE).contentHash, 'aaaa')
  assert.equal(makeRecord({ ...BASE, contentHash: undefined }).contentHash, null)
})

test('makeRecord: 字段集合固定，新增字段必须来这里登记', () => {
  assert.deepEqual(Object.keys(makeRecord(BASE)).sort(), [
    'builtinSkillFloor', 'contentHash', 'durationMs', 'exitCode', 'mode', 'model',
    'modelMismatch', 'platform', 'provider', 'reply', 'repeat', 'sessionId', 'skill',
    'stderr', 'task', 'toolCalls', 'triggered', 'turns', 'unavailable', 'usage',
  ])
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/record.test.mjs`
Expected: FAIL —— `Cannot find module '.../record.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/record.js`：

```js
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
  platform, skill, skillName, contentHash, task, repeat, mode,
  requestedModel, durationMs, exitCode, stderr, parsed,
}) {
  const p = parsed ?? {}
  const unavailable = []

  const triggered = mode === 'inject' ? null : (p.triggered ?? null)
  if (mode !== 'inject' && triggered === null) unavailable.push('triggered')

  for (const field of ['toolCalls', 'turns', 'usage', 'model']) {
    if (p[field] === null || p[field] === undefined) unavailable.push(field)
  }

  const shortName = (skillName ?? skill ?? '').split('/').pop()
  const builtinSkillFloor = Array.isArray(p.visibleSkills)
    ? p.visibleSkills.filter(n => n !== shortName && n !== skillName && n !== skill).length
    : null
  if (builtinSkillFloor === null) unavailable.push('builtinSkillFloor')

  return {
    platform, skill, task, repeat, mode,
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
    unavailable,
  }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/record.test.mjs`
Expected: PASS，16 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/record.js tests/harness/record.test.mjs
git commit -m "feat(harness): RunRecord 规范化与 unavailable 归因"
```

---

## Task 8: claude 适配器

**Files:**
- Create: `tools/skill-harness/adapters/claude.js`
- Create: `tools/skill-harness/probe/probe-anchor/SKILL.md`（从 `docs/superpowers/specs/measurements/probe-anchor/` 复制）
- Create: `tools/skill-harness/probe/probe-anchor/references/token.md`（同上）
- Modify: `tests/harness/jail.test.mjs`（追加 claude 适配器段）

**Interfaces:**
- Consumes: `jail.js` 的 `buildEnv`/`createJail`/`claudeOAuthToken`；`prompt.js` 的 `buildPrompt`；`profiles.js` 的 `claudeProfile`；`parse/claude-code-jsonl.js` 的 `parseClaudeCodeJsonl`
- Produces: `claudeAdapter` 对象，字段：
  - `profile`
  - `jailEnv({ jailDir, model, baseUrl, apiKey }) -> object`
  - `install({ jailDir, skillPath }) -> Promise<string[]>`
  - `args({ model, systemAppend, positional, sessionId }) -> string[]`
  - `collect() -> null`
  - `parse(raw, ctx) -> object`
  - `compensation: string`

- [ ] **Step 1: 复制探针 skill 到框架目录**

```bash
mkdir -p tools/skill-harness/probe/probe-anchor/references
cp docs/superpowers/specs/measurements/probe-anchor/SKILL.md tools/skill-harness/probe/probe-anchor/SKILL.md
cp docs/superpowers/specs/measurements/probe-anchor/references/token.md tools/skill-harness/probe/probe-anchor/references/token.md
```

- [ ] **Step 2: 写失败测试**

在 `tests/harness/jail.test.mjs` 末尾追加：

```js
import { claudeAdapter } from '../../tools/skill-harness/adapters/claude.js'

test('claude: jailEnv 重定向 HOME 与 CLAUDE_CONFIG_DIR', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: { PATH: '/usr/bin' }, oauthToken: 'tok' })
  assert.equal(env.HOME, '/tmp/h')
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/h/.claude')
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'tok')
  assert.equal(env.PATH, '/usr/bin')
})

test('claude: jailEnv 不透传宿主的 CLAUDECODE 等变量', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: { CLAUDECODE: '1', CLAUDE_CONFIG_DIR: '/real' }, oauthToken: 't' })
  assert.equal(env.CLAUDECODE, undefined)
  assert.equal(env.CLAUDE_CONFIG_DIR, '/tmp/h/.claude')
})

test('claude: 走第三方端点时用 baseUrl + apiKey 而非 oauth', () => {
  const env = claudeAdapter.jailEnv({ jailDir: '/tmp/h', source: {}, baseUrl: 'https://x/anthropic', apiKey: 'k' })
  assert.equal(env.ANTHROPIC_BASE_URL, 'https://x/anthropic')
  assert.equal(env.ANTHROPIC_API_KEY, 'k')
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, undefined)
})

test('claude: install 把 skill 复制进 jail 的 .claude/skills/，返回空 args', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const extraArgs = await claudeAdapter.install({ jailDir: dir, skillPath: 'tools/skill-harness/probe/probe-anchor' })
    assert.deepEqual(extraArgs, [])
    assert.ok(await fs.pathExists(path.join(dir, '.claude/skills/probe-anchor/SKILL.md')))
    assert.ok(await fs.pathExists(path.join(dir, '.claude/skills/probe-anchor/references/token.md')))
  } finally {
    await cleanup()
  }
})

test('claude: args 含 --setting-sources user 与 stream-json', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: null, positional: 'go', sessionId: 'sid' })
  assert.ok(a.includes('-p'))
  assert.ok(a.includes('--setting-sources'))
  assert.equal(a[a.indexOf('--setting-sources') + 1], 'user')
  assert.ok(a.includes('--output-format'))
  assert.equal(a[a.indexOf('--output-format') + 1], 'stream-json')
  assert.ok(a.includes('--verbose'))
  assert.equal(a[a.indexOf('--model') + 1], 'M')
  assert.equal(a[a.indexOf('--session-id') + 1], 'sid')
  assert.equal(a[a.length - 1], 'go')
})

test('claude: systemAppend 为 null 时不出现 --append-system-prompt', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: null, positional: 'go', sessionId: 's' })
  assert.ok(!a.includes('--append-system-prompt'))
})

test('claude: systemAppend 非空时紧跟其值', () => {
  const a = claudeAdapter.args({ model: 'M', systemAppend: 'COMP', positional: 'go', sessionId: 's' })
  assert.equal(a[a.indexOf('--append-system-prompt') + 1], 'COMP')
})

test('claude: collect 返回 null——过程数据在 stdout 里', () => {
  assert.equal(claudeAdapter.collect(), null)
})
```

- [ ] **Step 3: 运行测试确认失败**

Run: `node --test tests/harness/jail.test.mjs`
Expected: FAIL —— `Cannot find module '.../adapters/claude.js'`

- [ ] **Step 4: 写实现**

创建 `tools/skill-harness/adapters/claude.js`：

```js
import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv } from '../jail.js'
import { claudeProfile } from '../profiles.js'
import { parseClaudeCodeJsonl } from '../parse/claude-code-jsonl.js'

// HOME 重定向后 claude 既读不到 ~/.claude/.credentials.json 也认不了 keychain
// （实测报 "Not logged in · Please run /login"），凭证必须经环境变量注入。
export const claudeAdapter = {
  profile: claudeProfile,
  compensation: '',

  jailEnv({ jailDir, source = {}, oauthToken, baseUrl, apiKey }) {
    const extra = { HOME: jailDir, CLAUDE_CONFIG_DIR: path.join(jailDir, '.claude') }
    if (baseUrl) extra.ANTHROPIC_BASE_URL = baseUrl
    if (apiKey) extra.ANTHROPIC_API_KEY = apiKey
    else if (oauthToken) extra.CLAUDE_CODE_OAUTH_TOKEN = oauthToken
    return buildEnv(source, extra)
  },

  async install({ jailDir, skillPath }) {
    const dest = path.join(jailDir, '.claude/skills', path.basename(skillPath))
    await fs.ensureDir(path.dirname(dest))
    await fs.copy(skillPath, dest)
    return []
  },

  args({ model, systemAppend, positional, sessionId }) {
    const a = [
      '-p',
      '--setting-sources', 'user',
      '--permission-mode', 'bypassPermissions',
      '--output-format', 'stream-json',
      '--verbose',
      '--model', model,
      '--session-id', sessionId,
    ]
    if (systemAppend) a.push('--append-system-prompt', systemAppend)
    a.push(positional)
    return a
  },

  collect() {
    return null
  },

  parse(raw, ctx) {
    return parseClaudeCodeJsonl(raw, ctx)
  },
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `node --test tests/harness/jail.test.mjs`
Expected: PASS，20 个测试全绿（12 jail + 8 claude）

- [ ] **Step 6: 提交**

```bash
git add tools/skill-harness/adapters/claude.js tools/skill-harness/probe tests/harness/jail.test.mjs
git commit -m "feat(harness): claude 适配器与自检探针 skill"
```

---

## Task 9: pi 适配器

**Files:**
- Create: `tools/skill-harness/adapters/pi.js`
- Modify: `tests/harness/jail.test.mjs`（追加 pi 段）

**Interfaces:**
- Consumes: `jail.js` 的 `buildEnv`；`profiles.js` 的 `piProfile`；`parse/pi-jsonl.js` 的 `parsePiJsonl`
- Produces: `piAdapter`，字段与 `claudeAdapter` 同名同型

**关键差异**：pi 不需要 HOME 重定向。`-ns --skill <path>` 实测即可得到「恰好一个 skill」的环境，`install` 不复制文件，只返回 `['--skill', <绝对路径>]`。

- [ ] **Step 1: 写失败测试**

在 `tests/harness/jail.test.mjs` 末尾追加：

```js
import { piAdapter } from '../../tools/skill-harness/adapters/pi.js'

test('pi: install 不复制文件，返回 --skill 绝对路径', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const extraArgs = await piAdapter.install({ jailDir: dir, skillPath: 'tools/skill-harness/probe/probe-anchor' })
    assert.equal(extraArgs[0], '--skill')
    assert.ok(path.isAbsolute(extraArgs[1]))
    assert.ok(extraArgs[1].endsWith('probe-anchor'))
    assert.equal(await fs.pathExists(path.join(dir, '.pi')), false)
  } finally {
    await cleanup()
  }
})

test('pi: args 含全部隔离开关', () => {
  const a = piAdapter.args({ model: 'M', provider: 'P', systemAppend: null, positional: 'go', jailDir: '/tmp/h' })
  for (const flag of ['-p', '-ns', '-ne', '-np', '--no-themes', '-nc', '--mode']) {
    assert.ok(a.includes(flag), `missing ${flag}`)
  }
  assert.equal(a[a.indexOf('--mode') + 1], 'json')
  assert.equal(a[a.indexOf('--model') + 1], 'M')
  assert.equal(a[a.indexOf('--provider') + 1], 'P')
  assert.equal(a[a.indexOf('--session-dir') + 1], '/tmp/h/sessions')
  assert.equal(a[a.length - 1], 'go')
})

test('pi: -ns 与 --skill 可共存——实测 -ns 不影响显式加载', () => {
  const a = [...piAdapter.args({ model: 'M', provider: 'P', systemAppend: null, positional: 'go', jailDir: '/tmp/h' }), '--skill', '/abs/x']
  assert.ok(a.includes('-ns'))
  assert.ok(a.includes('--skill'))
})

test('pi: systemAppend 为 null 时不出现 --append-system-prompt', () => {
  const a = piAdapter.args({ model: 'M', provider: 'P', systemAppend: null, positional: 'go', jailDir: '/tmp/h' })
  assert.ok(!a.includes('--append-system-prompt'))
})

test('pi: collect 返回 null', () => {
  assert.equal(piAdapter.collect(), null)
})

test('pi: jailEnv 不重定向 HOME——pi 的 jail 靠命令行开关', () => {
  const env = piAdapter.jailEnv({ jailDir: '/tmp/h', source: { PATH: '/usr/bin', HOME: '/real/home' } })
  assert.equal(env.HOME, undefined)
  assert.equal(env.PATH, '/usr/bin')
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/jail.test.mjs`
Expected: FAIL —— `Cannot find module '.../adapters/pi.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/adapters/pi.js`：

```js
import path from 'node:path'
import { buildEnv } from '../jail.js'
import { piProfile } from '../profiles.js'
import { parsePiJsonl } from '../parse/pi-jsonl.js'

// pi 是三个平台里 jail 最轻的：-ns 关闭发现、--skill 显式加载，
// 二者实测可共存，得到「恰好一个 skill」的环境，无需 HOME 重定向。
export const piAdapter = {
  profile: piProfile,
  compensation: '',

  jailEnv({ source = {} }) {
    return buildEnv(source, {})
  },

  async install({ skillPath }) {
    return ['--skill', path.resolve(skillPath)]
  },

  args({ model, provider, systemAppend, positional, jailDir }) {
    const a = [
      '-p',
      '-ns', '-ne', '-np', '--no-themes', '-nc',
      '--session-dir', path.join(jailDir, 'sessions'),
      '--mode', 'json',
      '--model', model,
      '--provider', provider,
    ]
    if (systemAppend) a.push('--append-system-prompt', systemAppend)
    a.push(positional)
    return a
  },

  collect() {
    return null
  },

  parse(raw, ctx) {
    return parsePiJsonl(raw, ctx)
  },
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/jail.test.mjs`
Expected: PASS，26 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/adapters/pi.js tests/harness/jail.test.mjs
git commit -m "feat(harness): pi 适配器，-ns 与 --skill 组合"
```

---

## Task 10: hermes 适配器（含 collect）

**Files:**
- Create: `tools/skill-harness/adapters/hermes.js`
- Modify: `tests/harness/jail.test.mjs`（追加 hermes 段）

**Interfaces:**
- Consumes: `jail.js` 的 `buildEnv`/`readEnvFile`；`profiles.js` 的 `hermesProfile`；`parse/claude-code-jsonl.js` 的 `parseClaudeCodeJsonl`
- Produces: `hermesAdapter`，额外多两个函数：
  - `seedJail({ jailDir, hermesHome }) -> Promise<void>`（复制 `.env`/`auth.json`/`config.yaml`）
  - `collectArgs(sessionId) -> string[]`
  - `parseSessionId(listOutput) -> string | null`

**关键差异**：`-z` 不打印 session id（其文档明确「no session_id line」），collect 必须先 `hermes sessions list` 取 jail 内唯一会话。

- [ ] **Step 1: 写失败测试**

在 `tests/harness/jail.test.mjs` 末尾追加：

```js
import { hermesAdapter } from '../../tools/skill-harness/adapters/hermes.js'

test('hermes: jailEnv 重定向 HOME', () => {
  const env = hermesAdapter.jailEnv({ jailDir: '/tmp/h', source: { PATH: '/usr/bin' } })
  assert.equal(env.HOME, '/tmp/h')
  assert.equal(env.PATH, '/usr/bin')
})

test('hermes: seedJail 只复制三个凭证/配置文件', async () => {
  const { dir: fakeHome, cleanup: c1 } = await createJail()
  const { dir: jailDir, cleanup: c2 } = await createJail()
  try {
    const src = path.join(fakeHome, '.hermes')
    await fs.ensureDir(path.join(src, 'skills/should-not-be-copied'))
    await fs.writeFile(path.join(src, '.env'), 'MINIMAX_CN_API_KEY=k\n')
    await fs.writeFile(path.join(src, 'auth.json'), '{}')
    await fs.writeFile(path.join(src, 'config.yaml'), 'model:\n  default: M\n')
    await fs.writeFile(path.join(src, 'SOUL.md'), 'should not be copied')

    await hermesAdapter.seedJail({ jailDir, hermesHome: src })

    assert.ok(await fs.pathExists(path.join(jailDir, '.hermes/.env')))
    assert.ok(await fs.pathExists(path.join(jailDir, '.hermes/auth.json')))
    assert.ok(await fs.pathExists(path.join(jailDir, '.hermes/config.yaml')))
    assert.equal(await fs.pathExists(path.join(jailDir, '.hermes/SOUL.md')), false)
    assert.equal(await fs.pathExists(path.join(jailDir, '.hermes/skills/should-not-be-copied')), false)
  } finally {
    await c1(); await c2()
  }
})

test('hermes: install 复制进 jail 的 .hermes/skills/，返回空 args', async () => {
  const { dir, cleanup } = await createJail()
  try {
    const extraArgs = await hermesAdapter.install({ jailDir: dir, skillPath: 'tools/skill-harness/probe/probe-anchor' })
    assert.deepEqual(extraArgs, [])
    assert.ok(await fs.pathExists(path.join(dir, '.hermes/skills/probe-anchor/SKILL.md')))
  } finally {
    await cleanup()
  }
})

test('hermes: args 用 -z 与 --safe-mode', () => {
  const a = hermesAdapter.args({ model: 'M', provider: 'P', positional: 'go', jailDir: '/tmp/h' })
  assert.ok(a.includes('--safe-mode'))
  assert.ok(a.includes('--yolo'))
  assert.equal(a[a.indexOf('-z') + 1], 'go')
  assert.equal(a[a.indexOf('-m') + 1], 'M')
  assert.equal(a[a.indexOf('--provider') + 1], 'P')
  assert.equal(a[a.indexOf('--usage-file') + 1], '/tmp/h/usage.json')
})

test('hermes: 不接受 systemAppend——该平台无 system prompt 追加通道', () => {
  assert.throws(() => hermesAdapter.args({ model: 'M', provider: 'P', positional: 'go', jailDir: '/t', systemAppend: 'X' }), /prompt-only/)
})

test('hermes: parseSessionId 从 sessions list 输出取 UUID', () => {
  const out = [
    '                 Recent Sessions',
    '┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┓',
    '┃ ID                                   ┃ Msgs ┃',
    '┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━┩',
    '│ 3f6c9c1e-2f2a-4a1b-9c3d-8e7f6a5b4c3d │ 6    │',
    '└──────────────────────────────────────┴──────┘',
  ].join('\n')
  assert.equal(hermesAdapter.parseSessionId(out), '3f6c9c1e-2f2a-4a1b-9c3d-8e7f6a5b4c3d')
})

test('hermes: parseSessionId 无会话时返回 null', () => {
  assert.equal(hermesAdapter.parseSessionId('no sessions found'), null)
})

test('hermes: collectArgs 走 trace 格式导出到 stdout', () => {
  assert.deepEqual(hermesAdapter.collectArgs('sid-1'), [
    'sessions', 'export', '--format', 'trace', '--session-id', 'sid-1', '-',
  ])
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/jail.test.mjs`
Expected: FAIL —— `Cannot find module '.../adapters/hermes.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/adapters/hermes.js`：

```js
import fs from 'fs-extra'
import path from 'node:path'
import { buildEnv } from '../jail.js'
import { hermesProfile } from '../profiles.js'
import { parseClaudeCodeJsonl } from '../parse/claude-code-jsonl.js'

// 白名单，不是整目录复制：只带凭证与模型配置，不带用户的 skills/SOUL.md/memory。
const SEED_FILES = ['.env', 'auth.json', 'config.yaml']

const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i

export const hermesAdapter = {
  profile: hermesProfile,
  compensation: '',

  jailEnv({ jailDir, source = {} }) {
    return buildEnv(source, { HOME: jailDir })
  },

  async seedJail({ jailDir, hermesHome }) {
    const dest = path.join(jailDir, '.hermes')
    await fs.ensureDir(dest)
    for (const name of SEED_FILES) {
      const src = path.join(hermesHome, name)
      if (await fs.pathExists(src)) await fs.copy(src, path.join(dest, name))
    }
  },

  async install({ jailDir, skillPath }) {
    const dest = path.join(jailDir, '.hermes/skills', path.basename(skillPath))
    await fs.ensureDir(path.dirname(dest))
    await fs.copy(skillPath, dest)
    return []
  },

  args({ model, provider, positional, jailDir, systemAppend }) {
    if (systemAppend) throw new Error('hermes is prompt-only: systemAppend must be folded into the positional prompt')
    return [
      '-z', positional,
      '--safe-mode',
      '--yolo',
      '--usage-file', path.join(jailDir, 'usage.json'),
      '-m', model,
      '--provider', provider,
    ]
  },

  // -z 不打印 session id，所以 collect 先 sessions list。
  // jail 里每次运行都是全新 store，有且只有一个会话，因此这个做法是确定性的。
  parseSessionId(listOutput) {
    const m = String(listOutput).match(UUID_RE)
    return m ? m[0] : null
  },

  collectArgs(sessionId) {
    return ['sessions', 'export', '--format', 'trace', '--session-id', sessionId, '-']
  },

  parse(raw, ctx) {
    return parseClaudeCodeJsonl(raw, ctx)
  },
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/jail.test.mjs`
Expected: PASS，34 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/adapters/hermes.js tests/harness/jail.test.mjs
git commit -m "feat(harness): hermes 适配器与 trace collect 通道"
```

---

## Task 11: runner 矩阵分发

**Files:**
- Create: `tools/skill-harness/runner.js`
- Create: `tests/harness/runner.test.mjs`

**Interfaces:**
- Consumes: 三个适配器（Task 8/9/10）、`select.js`、`prompt.js`、`record.js`、`jail.js`
- Produces:
  - `ADAPTERS = { claude, pi, hermes }`
  - `planCell(cell, ctx) -> { argv, env, jailPlan }`（纯函数，dry-run 直接用它）
  - `runMatrix(cells, ctx) -> Promise<RunRecord[]>`
  - `runId() -> string`
  - `artifactDir(runId) -> string`

**并发**：默认 3（每平台一个），可经 `ctx.concurrency` 覆盖。同一 jail 不复用，每格独立 `createJail`。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/runner.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import os from 'node:os'
import path from 'node:path'
import { ADAPTERS, planCell, runId, artifactDir } from '../../tools/skill-harness/runner.js'

const CTX = {
  model: 'MiniMax-M2.7',
  provider: 'minimax-cn',
  task: 'run anchor probe',
  skillBody: 'BODY TEXT',
  skillDir: '/abs/probe-anchor',
  source: { PATH: '/usr/bin' },
  oauthToken: 'tok',
  jailDir: '/tmp/skill-harness-x',
  sessionId: '11111111-1111-1111-1111-111111111111',
}

test('ADAPTERS 有且只有三个平台，键与 profile.id 一致', () => {
  assert.deepEqual(Object.keys(ADAPTERS).sort(), ['claude', 'hermes', 'pi'])
  for (const [k, a] of Object.entries(ADAPTERS)) assert.equal(a.profile.id, k)
})

test('planCell: claude native 的 argv 不含 skill 正文', () => {
  const { argv } = planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.ok(!argv.some(a => String(a).includes('BODY TEXT')))
  assert.ok(argv.includes('--setting-sources'))
})

test('planCell: claude inject 的 argv 含正文与路径补偿行', () => {
  const { argv } = planCell({ platform: 'claude', mode: 'inject', skill: 'probe-anchor' }, CTX)
  const sys = argv[argv.indexOf('--append-system-prompt') + 1]
  assert.ok(sys.includes('BODY TEXT'))
  assert.ok(sys.includes('This skill directory is: /abs/probe-anchor'))
})

test('planCell: hermes inject 把一切拼进 -z，不产生 --append-system-prompt', () => {
  const { argv } = planCell({ platform: 'hermes', mode: 'inject', skill: 'probe-anchor' }, CTX)
  assert.ok(!argv.includes('--append-system-prompt'))
  const z = argv[argv.indexOf('-z') + 1]
  assert.ok(z.includes('BODY TEXT'))
  assert.ok(z.includes('This skill directory is: /abs/probe-anchor'))
  assert.ok(z.trimEnd().endsWith('run anchor probe'))
})

test('planCell: pi native 的 argv 含 -ns，且不含正文', () => {
  const { argv } = planCell({ platform: 'pi', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.ok(argv.includes('-ns'))
  assert.ok(!argv.some(a => String(a).includes('BODY TEXT')))
})

test('planCell: env 里凭证存在但 redacted 版本已打码', () => {
  const { env, redactedEnv } = planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, CTX)
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'tok')
  assert.equal(redactedEnv.CLAUDE_CODE_OAUTH_TOKEN, '***')
})

test('planCell: 模型缺失时抛错，不静默用平台默认值', () => {
  assert.throws(
    () => planCell({ platform: 'claude', mode: 'native', skill: 'probe-anchor' }, { ...CTX, model: undefined }),
    /model/,
  )
})

test('planCell 是纯函数：两次调用 argv deepEqual', () => {
  const cell = { platform: 'pi', mode: 'inject', skill: 'probe-anchor' }
  assert.deepEqual(planCell(cell, CTX).argv, planCell(cell, CTX).argv)
})

test('runId: 形如 YYYYMMDD-HHMMSS-<4 hex>', () => {
  assert.match(runId(), /^\d{8}-\d{6}-[0-9a-f]{4}$/)
})

test('artifactDir: 落在 $HOME/.hskill/skill-harness/ 下', () => {
  const d = artifactDir('20260815-101112-abcd')
  assert.equal(d, path.join(os.homedir(), '.hskill/skill-harness/20260815-101112-abcd'))
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/runner.test.mjs`
Expected: FAIL —— `Cannot find module '.../runner.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/runner.js`：

```js
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import crypto from 'node:crypto'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { claudeAdapter } from './adapters/claude.js'
import { piAdapter } from './adapters/pi.js'
import { hermesAdapter } from './adapters/hermes.js'
import { buildPrompt } from './prompt.js'
import { makeRecord } from './record.js'
import { createJail, redactEnv } from './jail.js'

const execFileAsync = promisify(execFile)

export const ADAPTERS = { claude: claudeAdapter, pi: piAdapter, hermes: hermesAdapter }

const BIN = { claude: 'claude', pi: 'pi', hermes: 'hermes' }

export function runId() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
  return `${stamp}-${crypto.randomBytes(2).toString('hex')}`
}

export function artifactDir(id) {
  return path.join(os.homedir(), '.hskill/skill-harness', id)
}

// 纯函数。dry-run 直接消费它，因此不许有任何副作用。
export function planCell(cell, ctx) {
  if (!ctx.model) throw new Error('model is required — refusing to fall back to the platform default, which would confound platform with model')
  const adapter = ADAPTERS[cell.platform]
  const { systemAppend, positional } = buildPrompt({
    mode: cell.mode,
    injection: adapter.profile.injection,
    skillBody: ctx.skillBody,
    skillDir: ctx.skillDir,
    compensation: adapter.compensation,
    task: ctx.task,
  })

  const env = adapter.jailEnv({
    jailDir: ctx.jailDir, source: ctx.source,
    oauthToken: ctx.oauthToken, baseUrl: ctx.baseUrl, apiKey: ctx.apiKey,
  })

  const argv = adapter.args({
    model: ctx.model, provider: ctx.provider,
    systemAppend, positional,
    jailDir: ctx.jailDir, sessionId: ctx.sessionId,
  })

  return { argv, env, redactedEnv: redactEnv(env), systemAppend, positional }
}

async function runOne(cell, ctx) {
  const adapter = ADAPTERS[cell.platform]
  const { dir: jailDir, cleanup } = await createJail()
  const started = Date.now()
  try {
    if (cell.platform === 'hermes') {
      await adapter.seedJail({ jailDir, hermesHome: path.join(ctx.source.HOME ?? os.homedir(), '.hermes') })
    }
    const extraArgs = cell.mode === 'native'
      ? await adapter.install({ jailDir, skillPath: ctx.skillPath })
      : []

    const plan = planCell(cell, { ...ctx, jailDir })
    const argv = [...plan.argv, ...extraArgs]

    let stdout = ''
    let stderr = ''
    let exitCode = 0
    try {
      const r = await execFileAsync(BIN[cell.platform], argv, {
        cwd: jailDir, env: plan.env, maxBuffer: 64 * 1024 * 1024, timeout: ctx.timeoutMs ?? 300000,
      })
      stdout = r.stdout
      stderr = r.stderr
    } catch (e) {
      stdout = e.stdout ?? ''
      stderr = e.stderr ?? String(e.message)
      exitCode = e.code ?? 1
    }

    let raw = stdout
    const collected = adapter.collect ? adapter.collect() : null
    if (collected === null && cell.platform === 'hermes') {
      const list = await execFileAsync(BIN.hermes, ['sessions', 'list'], { cwd: jailDir, env: plan.env }).catch(() => ({ stdout: '' }))
      const sid = adapter.parseSessionId(list.stdout)
      if (sid) {
        const exp = await execFileAsync(BIN.hermes, adapter.collectArgs(sid), { cwd: jailDir, env: plan.env, maxBuffer: 64 * 1024 * 1024 }).catch(() => ({ stdout: '' }))
        raw = exp.stdout || stdout
      }
    }

    const parsed = adapter.parse(raw, { skillName: path.basename(ctx.skillPath), skillDir: ctx.skillDir })
    return makeRecord({
      platform: cell.platform, skill: cell.skill, skillName: path.basename(ctx.skillPath),
      contentHash: ctx.contentHash ?? null,
      task: ctx.task, repeat: cell.repeat ?? 0, mode: cell.mode,
      requestedModel: ctx.model, durationMs: Date.now() - started,
      exitCode, stderr, parsed,
    })
  } finally {
    await cleanup()
  }
}

export async function runMatrix(cells, ctx) {
  const todo = cells.filter(c => c.state === 'run')
  const limit = ctx.concurrency ?? 3
  const records = []
  let i = 0
  async function worker() {
    while (i < todo.length) {
      const cell = todo[i++]
      records.push(await runOne(cell, ctx))
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker))

  const id = ctx.runId ?? runId()
  const dir = artifactDir(id)
  await fs.ensureDir(dir)
  await fs.writeJson(path.join(dir, 'records.json'), records, { spaces: 2 })
  await fs.writeJson(path.join(dir, 'cells.json'), cells, { spaces: 2 })
  return { runId: id, dir, records }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/runner.test.mjs`
Expected: PASS，10 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/runner.js tests/harness/runner.test.mjs
git commit -m "feat(harness): runner 矩阵分发与产物落盘"
```

---

## Task 12: coverage 视图

**Files:**
- Create: `tools/skill-harness/coverage.js`
- Create: `tests/harness/coverage.test.mjs`

**Interfaces:**
- Consumes: `runner.js` 落盘的 `records.json`；`skills-index.json` 的 `contentHash`
- Produces:
  - `loadRuns(baseDir) -> Promise<Array<{ runId, at, records }>>`
  - `buildCoverage({ runs, skills, now }) -> Cell[]`
    `Cell = { skill, platform, lastRunAt, ageDays, stale, state }`
    `state ∈ 'never' | 'fresh' | 'stale'`
  - `renderCoverage(cells) -> string`

**stale 判据**：该 skill 在 `skills-index.json` 里的 `contentHash` 与最近一次运行时记录的 hash 不同 → 结论已过期。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/coverage.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildCoverage, renderCoverage } from '../../tools/skill-harness/coverage.js'

const SKILLS = [
  { path: 'mint/learn-skill', contentHash: 'aaaa' },
  { path: 'research/extract-url', contentHash: 'bbbb' },
]

const NOW = new Date('2026-08-15T00:00:00Z')

const RUNS = [
  {
    runId: '20260812-100000-0001',
    at: new Date('2026-08-12T00:00:00Z'),
    records: [
      { skill: 'mint/learn-skill', platform: 'claude', contentHash: 'aaaa' },
      { skill: 'mint/learn-skill', platform: 'pi', contentHash: 'aaaa' },
      { skill: 'research/extract-url', platform: 'claude', contentHash: 'OLD' },
    ],
  },
]

test('从未跑过的格子是 never', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'mint/learn-skill' && x.platform === 'hermes')
  assert.equal(c.state, 'never')
  assert.equal(c.lastRunAt, null)
})

test('跑过且 contentHash 一致的格子是 fresh', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'mint/learn-skill' && x.platform === 'claude')
  assert.equal(c.state, 'fresh')
  assert.equal(c.ageDays, 3)
})

test('contentHash 变过的格子是 stale——结论已过期', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  const c = cells.find(x => x.skill === 'research/extract-url' && x.platform === 'claude')
  assert.equal(c.state, 'stale')
  assert.equal(c.stale, true)
})

test('矩阵是完整的：skill 数 × 平台数', () => {
  const cells = buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW })
  assert.equal(cells.length, 2 * 3)
})

test('多次运行取最近一次', () => {
  const runs = [
    ...RUNS,
    { runId: '20260814-100000-0002', at: new Date('2026-08-14T00:00:00Z'), records: [{ skill: 'mint/learn-skill', platform: 'claude', contentHash: 'aaaa' }] },
  ]
  const c = buildCoverage({ runs, skills: SKILLS, now: NOW }).find(x => x.skill === 'mint/learn-skill' && x.platform === 'claude')
  assert.equal(c.ageDays, 1)
})

test('renderCoverage: never 渲染成 never，不是对勾', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  assert.ok(out.includes('never'))
  assert.ok(!out.includes('✓'))
})

test('renderCoverage: stale 带标记', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  assert.ok(/3d ago/.test(out))
  assert.ok(/陈/.test(out))
})

test('renderCoverage: 表头含三个平台名', () => {
  const out = renderCoverage(buildCoverage({ runs: RUNS, skills: SKILLS, now: NOW }))
  for (const p of ['claude', 'pi', 'hermes']) assert.ok(out.includes(p))
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/coverage.test.mjs`
Expected: FAIL —— `Cannot find module '.../coverage.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/coverage.js`：

```js
import fs from 'fs-extra'
import path from 'node:path'
import { PHASE1_PLATFORMS } from './select.js'

export async function loadRuns(baseDir) {
  if (!await fs.pathExists(baseDir)) return []
  const entries = await fs.readdir(baseDir)
  const runs = []
  for (const id of entries.sort()) {
    const file = path.join(baseDir, id, 'records.json')
    if (!await fs.pathExists(file)) continue
    const stat = await fs.stat(file)
    runs.push({ runId: id, at: stat.mtime, records: await fs.readJson(file) })
  }
  return runs
}

// 允许挑着跑，就必须同时提供「哪些格子很久没跑 / 结论已过期」的视图，
// 否则选择机制会在半年内把覆盖率悄悄掏空，而没有任何一次运行会报错。
export function buildCoverage({ runs, skills, now = new Date() }) {
  const latest = new Map()
  for (const run of runs) {
    for (const rec of run.records) {
      const key = `${rec.skill} ${rec.platform}`
      const prev = latest.get(key)
      if (!prev || run.at > prev.at) latest.set(key, { at: run.at, contentHash: rec.contentHash ?? null })
    }
  }

  const cells = []
  for (const s of skills) {
    for (const platform of PHASE1_PLATFORMS) {
      const hit = latest.get(`${s.path} ${platform}`)
      if (!hit) {
        cells.push({ skill: s.path, platform, lastRunAt: null, ageDays: null, stale: false, state: 'never' })
        continue
      }
      const stale = hit.contentHash !== s.contentHash
      cells.push({
        skill: s.path, platform,
        lastRunAt: hit.at,
        ageDays: Math.floor((now - hit.at) / 86400000),
        stale,
        state: stale ? 'stale' : 'fresh',
      })
    }
  }
  return cells
}

export function renderCoverage(cells) {
  const skills = [...new Set(cells.map(c => c.skill))]
  const width = Math.max(24, ...skills.map(s => s.length)) + 2
  const head = 'skill'.padEnd(width) + PHASE1_PLATFORMS.map(p => p.padEnd(12)).join('')
  const rows = skills.map(skill => {
    const cols = PHASE1_PLATFORMS.map(platform => {
      const c = cells.find(x => x.skill === skill && x.platform === platform)
      if (!c || c.state === 'never') return 'never'.padEnd(12)
      return `${c.ageDays}d ago${c.stale ? '·陈' : ''}`.padEnd(12)
    })
    return skill.padEnd(width) + cols.join('')
  })
  return [head, ...rows].join('\n')
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/coverage.test.mjs`
Expected: PASS，8 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/coverage.js tests/harness/coverage.test.mjs
git commit -m "feat(harness): coverage 视图与 contentHash 过期判定"
```

---

## Task 13: 三态报告

**Files:**
- Create: `tools/skill-harness/report.js`
- Create: `tests/harness/report.test.mjs`

**Interfaces:**
- Consumes: `select.js` 的 `Cell[]`、`record.js` 的 `RunRecord[]`、`profiles.js` 的 `PROFILES`
- Produces: `renderReport({ cells, records, model, provider }) -> string`

**三态硬约束**：`not-run` 渲染成空格，绝不渲染成对勾；`declared-na` 渲染成 `n/a` 并在脚注列出 reason。报告页眉必须打印模型。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/report.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { renderReport } from '../../tools/skill-harness/report.js'

const CELLS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', state: 'run' },
  { skill: 'a/x', platform: 'pi', mode: 'native', state: 'not-run' },
  { skill: 'a/x', platform: 'hermes', mode: 'native', state: 'declared-na', reason: '无等价机制' },
]

const RECORDS = [
  { skill: 'a/x', platform: 'claude', mode: 'native', exitCode: 0, triggered: true, modelMismatch: false, unavailable: [], reply: 'ok' },
]

test('页眉打印模型——没写模型的跨平台报告不可解读', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'MiniMax-M2.7', provider: 'minimax-cn' })
  assert.ok(out.includes('MiniMax-M2.7'))
  assert.ok(out.includes('minimax-cn'))
})

test('not-run 渲染成空格，绝不是对勾', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(!out.includes('✓'), 'not-run must never render as a checkmark')
  const row = out.split('\n').find(l => l.startsWith('a/x'))
  // 列宽 12：claude 列是 'pass'，pi 列必须整列空白，hermes 列是 'n/a'
  const cols = [0, 1, 2].map(i => row.slice(26 + i * 12, 26 + (i + 1) * 12))
  assert.equal(cols[0].trim(), 'pass')
  assert.equal(cols[1].trim(), '')
  assert.equal(cols[2].trim(), 'n/a')
  assert.ok(out.includes('not-run: 1'))
})

test('capabilities 表有生产消费者——报告读它说明各平台拿不到什么', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(/hermes/.test(out))
  assert.ok(/collect/.test(out), '报告须说明 hermes 的过程数据走 collect 通道')
  assert.ok(/cost-cap/.test(out), '报告须说明只有 claude 有成本上限能力')
})

test('declared-na 渲染成 n/a 并在脚注给出 reason', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(out.includes('n/a'))
  assert.ok(out.includes('无等价机制'))
})

test('跑过并成功的格子渲染成 pass', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(out.includes('pass'))
})

test('exitCode 非零渲染成 fail', () => {
  const bad = [{ ...RECORDS[0], exitCode: 1 }]
  const out = renderReport({ cells: CELLS, records: bad, model: 'M', provider: 'P' })
  assert.ok(out.includes('fail'))
})

test('modelMismatch 单列，不混进普通失败', () => {
  const mism = [{ ...RECORDS[0], modelMismatch: true }]
  const out = renderReport({ cells: CELLS, records: mism, model: 'M', provider: 'P' })
  assert.ok(/model mismatch/i.test(out))
})

test('unavailable 字段在报告里显式说明，不静默省略', () => {
  const un = [{ ...RECORDS[0], unavailable: ['toolCalls', 'triggered'] }]
  const out = renderReport({ cells: CELLS, records: un, model: 'M', provider: 'P' })
  assert.ok(out.includes('toolCalls'))
  assert.ok(out.includes('triggered'))
})

test('builtinSkillFloor 不对称在报告里给出归因提示', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.ok(/builtinSkillFloor/.test(out))
  assert.ok(/16/.test(out))
})

test('矩阵行数等于 skill 数，不省略任何行列', () => {
  const out = renderReport({ cells: CELLS, records: RECORDS, model: 'M', provider: 'P' })
  assert.equal(out.split('\n').filter(l => l.startsWith('a/x')).length, 1)
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/report.test.mjs`
Expected: FAIL —— `Cannot find module '.../report.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/report.js`：

```js
import { PHASE1_PLATFORMS } from './select.js'
import { PROFILES } from './profiles.js'

// 三态：pass/fail 是真跑了；declared-na 是声明排除；not-run 是本次没覆盖。
// not-run 永远不得折叠进 pass，也不得从矩阵里省略行列——
// 这是 QM residual 那条纪律的直接应用：没有 residual 的归因表一定在撒谎。
function cellLabel(cell, records) {
  if (cell.state === 'declared-na') return 'n/a'
  if (cell.state === 'not-run') return ''
  const rec = records.find(r => r.skill === cell.skill && r.platform === cell.platform && r.mode === cell.mode)
  if (!rec) return ''
  return rec.exitCode === 0 ? 'pass' : 'fail'
}

export function renderReport({ cells, records, model, provider }) {
  const skills = [...new Set(cells.map(c => c.skill))]
  const width = Math.max(24, ...skills.map(s => s.length)) + 2

  const lines = []
  lines.push(`model:    ${model}`)
  lines.push(`provider: ${provider}`)
  lines.push('')
  lines.push('skill'.padEnd(width) + PHASE1_PLATFORMS.map(p => p.padEnd(12)).join(''))

  for (const skill of skills) {
    const cols = PHASE1_PLATFORMS.map(platform => {
      const c = cells.find(x => x.skill === skill && x.platform === platform)
      return (c ? cellLabel(c, records) : '').padEnd(12)
    })
    lines.push(skill.padEnd(width) + cols.join(''))
  }

  const counts = { pass: 0, fail: 0, 'declared-na': 0, 'not-run': 0 }
  for (const c of cells) {
    if (c.state === 'declared-na') counts['declared-na']++
    else if (c.state === 'not-run') counts['not-run']++
    else {
      const rec = records.find(r => r.skill === c.skill && r.platform === c.platform && r.mode === c.mode)
      if (!rec) counts['not-run']++
      else if (rec.exitCode === 0) counts.pass++
      else counts.fail++
    }
  }
  lines.push('')
  lines.push(`pass: ${counts.pass}  fail: ${counts.fail}  declared-na: ${counts['declared-na']}  not-run: ${counts['not-run']}`)

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

  const na = cells.filter(c => c.state === 'declared-na')
  if (na.length) {
    lines.push('')
    lines.push('declared n/a:')
    const seen = new Set()
    for (const c of na) {
      const key = `${c.skill}@${c.platform}`
      if (seen.has(key)) continue
      seen.add(key)
      lines.push(`  ${key}: ${c.reason}`)
    }
  }

  // capabilities 与 profile 必须有生产消费者，否则会腐烂成谎言（spec 风险 1）：
  // 表靠一条测试守着、而那条测试断言的正是声明本身，就是自己证明自己。
  // 让表错了体现在给人看的输出里，才有代价。
  const floors = PROFILES.map(p => `${p.id}=${p.builtinSkillFloor}`).join(' ')
  lines.push('')
  lines.push(`builtinSkillFloor: ${floors} — 触发失败先归因到这一格，各平台候选数不同`)

  lines.push('')
  lines.push('platform notes:')
  const ALL_CAPS = ['tool-trace', 'usage', 'cost-cap', 'tool-allowlist', 'structured-output', 'system-prompt-append']
  for (const p of PROFILES) {
    const missing = ALL_CAPS.filter(c => !p.capabilities.has(c))
    const chan = p.processChannel === 'collect' ? '过程数据走 collect 通道，导出失败则 toolCalls 缺失' : '过程数据在 stdout 内联'
    lines.push(`  ${p.id}: ${chan}${missing.length ? `；缺能力 ${missing.join(', ')}` : ''}`)
  }

  return lines.join('\n')
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/report.test.mjs`
Expected: PASS，10 个测试全绿

- [ ] **Step 5: 提交**

```bash
git add tools/skill-harness/report.js tests/harness/report.test.mjs
git commit -m "feat(harness): 三态报告渲染，not-run 不得伪装成通过"
```

---

## Task 14: CLI 与 dry-run

**Files:**
- Create: `tools/skill-harness/cli.js`
- Create: `tests/harness/cli.test.mjs`

**Interfaces:**
- Consumes: 前面全部模块
- Produces: 可执行 CLI，四个子命令 `run` / `dry-run` / `report` / `coverage`
  - `parseArgs(argv) -> { command, opts }`（纯函数，被单测覆盖）
  - `renderDryRun(cells, ctx) -> string`

**dry-run 必须打印**：完整 prompt + 完整 argv + jail 内将写入的文件清单 + 打码后的 env。native 模式 prompt 里没有正文，所以必须打印 `install` 会往 jail 写什么，否则这个模式在 dry-run 里近乎空白。

- [ ] **Step 1: 写失败测试**

创建 `tests/harness/cli.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseArgs, renderDryRun } from '../../tools/skill-harness/cli.js'

test('parseArgs: 子命令识别', () => {
  assert.equal(parseArgs(['run', '--model', 'M']).command, 'run')
  assert.equal(parseArgs(['dry-run', '--model', 'M']).command, 'dry-run')
  assert.equal(parseArgs(['coverage']).command, 'coverage')
  assert.equal(parseArgs(['report']).command, 'report')
})

test('parseArgs: --skill 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--skill', 'a/b', '--skill', 'c/d'])
  assert.deepEqual(opts.skills, ['a/b', 'c/d'])
})

test('parseArgs: --platform 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--platform', 'pi', '--platform', 'claude'])
  assert.deepEqual(opts.platforms, ['pi', 'claude'])
})

test('parseArgs: --bundle 可重复', () => {
  const { opts } = parseArgs(['run', '--model', 'M', '--bundle', 'research'])
  assert.deepEqual(opts.bundles, ['research'])
})

test('parseArgs: --mode both 展开成两种模式', () => {
  assert.deepEqual(parseArgs(['run', '--model', 'M', '--mode', 'both']).opts.modes, ['native', 'inject'])
  assert.deepEqual(parseArgs(['run', '--model', 'M', '--mode', 'native']).opts.modes, ['native'])
})

test('parseArgs: --mode 缺省即 both', () => {
  assert.deepEqual(parseArgs(['run', '--model', 'M']).opts.modes, ['native', 'inject'])
})

test('parseArgs: --repeat 转成数字，缺省为 1', () => {
  assert.equal(parseArgs(['run', '--model', 'M', '--repeat', '5']).opts.repeat, 5)
  assert.equal(parseArgs(['run', '--model', 'M']).opts.repeat, 1)
})

test('parseArgs: run 缺 --model 抛错，不静默用平台默认值', () => {
  assert.throws(() => parseArgs(['run']), /--model is required/)
})

test('parseArgs: coverage 不要求 --model', () => {
  assert.doesNotThrow(() => parseArgs(['coverage']))
})

test('parseArgs: 未知平台名抛错', () => {
  assert.throws(() => parseArgs(['run', '--model', 'M', '--platform', 'cursor']), /cursor/)
})

test('renderDryRun: 打印 argv、prompt、env（打码）与 jail 写入清单', () => {
  const cells = [{ skill: 'probe-anchor', platform: 'claude', mode: 'native', state: 'run' }]
  const ctx = {
    model: 'M', provider: 'P', task: 'go', skillBody: 'BODY', skillDir: '/abs/probe-anchor',
    skillPath: '/abs/probe-anchor', source: { PATH: '/usr/bin' }, oauthToken: 'SECRET',
    jailDir: '/tmp/skill-harness-x', sessionId: '11111111-1111-1111-1111-111111111111',
  }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('claude/native'))
  assert.ok(out.includes('--setting-sources'))
  assert.ok(out.includes('/tmp/skill-harness-x/.claude/skills/probe-anchor'))
  assert.ok(out.includes('***'))
  assert.ok(!out.includes('SECRET'))
})

test('renderDryRun: native 模式明确标出正文不在 prompt 里', () => {
  const cells = [{ skill: 'probe-anchor', platform: 'claude', mode: 'native', state: 'run' }]
  const ctx = { model: 'M', provider: 'P', task: 'go', skillBody: 'BODYTEXT', skillDir: '/d', skillPath: '/d', source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's' }
  const out = renderDryRun(cells, ctx)
  assert.ok(!out.includes('BODYTEXT'))
  assert.ok(/loaded natively/i.test(out))
})

test('renderDryRun: 只渲染 state 为 run 的格子', () => {
  const cells = [
    { skill: 'a', platform: 'claude', mode: 'native', state: 'not-run' },
    { skill: 'b', platform: 'pi', mode: 'native', state: 'run' },
  ]
  const ctx = { model: 'M', provider: 'P', task: 'go', skillBody: 'B', skillDir: '/d', skillPath: '/d', source: {}, jailDir: '/tmp/skill-harness-x', sessionId: 's' }
  const out = renderDryRun(cells, ctx)
  assert.ok(out.includes('pi/native'))
  assert.ok(!out.includes('claude/native'))
})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `node --test tests/harness/cli.test.mjs`
Expected: FAIL —— `Cannot find module '.../cli.js'`

- [ ] **Step 3: 写实现**

创建 `tools/skill-harness/cli.js`：

```js
#!/usr/bin/env node
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { selectCells, validateMatrix, PHASE1_PLATFORMS, MODES } from './select.js'
import { planCell, runMatrix, ADAPTERS } from './runner.js'
import { loadRuns, buildCoverage, renderCoverage } from './coverage.js'
import { renderReport } from './report.js'
import { stripFrontmatter } from './prompt.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(here, '../..')

const COMMANDS = new Set(['run', 'dry-run', 'report', 'coverage'])
const REPEATABLE = { '--skill': 'skills', '--platform': 'platforms', '--bundle': 'bundles' }

export function parseArgs(argv) {
  const command = argv[0]
  if (!COMMANDS.has(command)) throw new Error(`unknown command: ${command} (expected one of ${[...COMMANDS].join(', ')})`)

  const opts = { modes: [...MODES], repeat: 1 }
  for (let i = 1; i < argv.length; i++) {
    const flag = argv[i]
    const value = argv[++i]
    if (REPEATABLE[flag]) {
      const key = REPEATABLE[flag]
      opts[key] = [...(opts[key] ?? []), value]
    } else if (flag === '--mode') {
      opts.modes = value === 'both' ? [...MODES] : [value]
    } else if (flag === '--model') opts.model = value
    else if (flag === '--provider') opts.provider = value
    else if (flag === '--base-url') opts.baseUrl = value
    else if (flag === '--task') opts.task = value
    else if (flag === '--repeat') opts.repeat = Number(value)
    else throw new Error(`unknown flag: ${flag}`)
  }

  for (const p of opts.platforms ?? []) {
    if (!PHASE1_PLATFORMS.includes(p)) throw new Error(`unknown platform: ${p} (phase 1 supports ${PHASE1_PLATFORMS.join(', ')})`)
  }
  for (const m of opts.modes) {
    if (!MODES.includes(m)) throw new Error(`unknown mode: ${m}`)
  }
  if ((command === 'run' || command === 'dry-run') && !opts.model) {
    throw new Error('--model is required — falling back to each platform default would confound platform with model')
  }
  return { command, opts }
}

export function renderDryRun(cells, ctx) {
  const out = []
  for (const cell of cells) {
    if (cell.state !== 'run') continue
    const adapter = ADAPTERS[cell.platform]
    const plan = planCell(cell, ctx)
    out.push(`=== ${cell.platform}/${cell.mode} · ${cell.skill} ===`)
    out.push('argv:')
    out.push(plan.argv.map(a => `  ${a}`).join('\n'))
    out.push('env (redacted):')
    out.push(Object.entries(plan.redactedEnv).map(([k, v]) => `  ${k}=${v}`).join('\n'))
    if (cell.mode === 'native') {
      const dest = adapter.profile.skillChannel === 'skill-dir'
        ? path.join(ctx.jailDir, cell.platform === 'claude' ? '.claude/skills' : '.hermes/skills', path.basename(ctx.skillPath))
        : '(none — loaded via explicit flag)'
      out.push(`jail writes: ${dest}`)
      out.push('skill body: not in the prompt — loaded natively by the platform')
    }
    out.push('systemAppend:')
    out.push(plan.systemAppend ?? '  (none)')
    out.push('positional:')
    out.push(plan.positional)
    out.push('')
  }
  return out.join('\n')
}

async function main() {
  const { command, opts } = parseArgs(process.argv.slice(2))
  const index = await fs.readJson(path.join(REPO_ROOT, 'skills-index.json'))
  const matrix = await fs.readJson(path.join(here, 'matrix.json'))

  const errors = validateMatrix(matrix)
  if (errors.length) {
    console.error(errors.join('\n'))
    process.exit(1)
  }

  if (command === 'coverage') {
    const runs = await loadRuns(path.join(os.homedir(), '.hskill/skill-harness'))
    console.log(renderCoverage(buildCoverage({ runs, skills: index.skills })))
    return
  }

  const cells = selectCells({ skills: index.skills, matrix, opts })
  const skillPath = path.join(REPO_ROOT, 'tools/skill-harness/probe/probe-anchor')
  const ctx = {
    model: opts.model,
    provider: opts.provider,
    baseUrl: opts.baseUrl,
    apiKey: opts.baseUrl ? process.env.MINIMAX_CN_API_KEY : undefined,
    task: opts.task ?? 'run anchor probe',
    skillPath,
    skillDir: skillPath,
    skillBody: stripFrontmatter(await fs.readFile(path.join(skillPath, 'SKILL.md'), 'utf8')),
    contentHash: index.skills.find(s => s.path === opts.skills?.[0])?.contentHash ?? null,
    source: process.env,
    jailDir: '<created at run time>',
    sessionId: '00000000-0000-0000-0000-000000000000',
  }

  if (command === 'dry-run') {
    console.log(renderDryRun(cells, ctx))
    return
  }

  if (command === 'run') {
    const { records } = await runMatrix(cells, ctx)
    console.log(renderReport({ cells, records, model: opts.model, provider: opts.provider }))
    return
  }

  if (command === 'report') {
    const runs = await loadRuns(path.join(os.homedir(), '.hskill/skill-harness'))
    const last = runs[runs.length - 1]
    if (!last) {
      console.error('no runs found')
      process.exit(1)
    }
    console.log(renderReport({ cells, records: last.records, model: opts.model, provider: opts.provider }))
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(e => {
    console.error(e.message)
    process.exit(1)
  })
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `node --test tests/harness/cli.test.mjs`
Expected: PASS，13 个测试全绿

- [ ] **Step 5: 手工验证 dry-run 输出六份**

Run:
```bash
node tools/skill-harness/cli.js dry-run --model MiniMax-M2.7 --provider minimax-cn --skill mint/learn-skill
```
Expected: 输出 6 段（3 平台 × 2 模式），每段含 argv、打码 env、systemAppend、positional；native 段含 `jail writes:` 与 `loaded natively`，且不含 skill 正文。

- [ ] **Step 6: 提交**

```bash
git add tools/skill-harness/cli.js tests/harness/cli.test.mjs
git commit -m "feat(harness): CLI 四子命令与 dry-run 六组输出"
```

---

## Task 15: L3 jail 有效性与端到端验收

**Files:**
- Create: `tests/harness/e2e.test.mjs`
- Modify: `docs/reference/testing-guide.md`（追加 harness 一节）

**Interfaces:**
- Consumes: 全部模块
- Produces: 端到端测试，默认 `skip`，靠 `SKILL_HARNESS_E2E=1` 开启（真模型有成本，不能进默认 `npm test`）

**L3 的两条断言**（对宿主取证，不往用户目录写任何东西）：
1. 宿主 skill 不可见——读用户真实 skill 目录的名字清单，断言运行结果里一个都没出现（claude 的 16 个内置名除外）
2. anchor probe 在 native 模式三平台全部 `FILE=ANCHOR-7F3A9C`

- [ ] **Step 1: 写测试**

创建 `tests/harness/e2e.test.mjs`：

```js
import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'fs-extra'
import os from 'node:os'
import path from 'node:path'
import { runMatrix } from '../../tools/skill-harness/runner.js'
import { stripFrontmatter } from '../../tools/skill-harness/prompt.js'
import { claudeOAuthToken, readEnvFile } from '../../tools/skill-harness/jail.js'

const ENABLED = process.env.SKILL_HARNESS_E2E === '1'
const MODEL = process.env.SKILL_HARNESS_MODEL ?? 'MiniMax-M2.7'
const PROVIDER = process.env.SKILL_HARNESS_PROVIDER ?? 'minimax-cn'
const BASE_URL = 'https://api.minimaxi.com/anthropic'

const SKILL_PATH = path.resolve('tools/skill-harness/probe/probe-anchor')

// claude 的 16 个内置 skill 不算宿主泄漏——jail 挡不住它们，这是已知不对称。
const CLAUDE_BUILTINS = new Set([
  'deep-research', 'design-sync', 'dataviz', 'update-config', 'verify', 'debug',
  'code-review', 'simplify', 'batch', 'fewer-permission-prompts', 'doctor',
  'loop', 'schedule', 'claude-api', 'run', 'run-skill-generator',
])

async function baseCtx() {
  return {
    model: MODEL,
    provider: PROVIDER,
    baseUrl: BASE_URL,
    apiKey: readEnvFile(path.join(os.homedir(), '.hermes/.env')).MINIMAX_CN_API_KEY,
    oauthToken: claudeOAuthToken(),
    task: 'run anchor probe',
    skillPath: SKILL_PATH,
    skillDir: SKILL_PATH,
    skillBody: stripFrontmatter(await fs.readFile(path.join(SKILL_PATH, 'SKILL.md'), 'utf8')),
    source: process.env,
    sessionId: '00000000-0000-0000-0000-000000000000',
    concurrency: 3,
  }
}

function cells(mode, task) {
  return ['claude', 'pi', 'hermes'].map(platform => ({
    skill: 'probe-anchor', platform, mode, state: 'run', repeat: 0, task,
  }))
}

test('E2E native: 三平台都读到 references/token.md', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  assert.equal(records.length, 3)
  for (const r of records) {
    assert.ok(r.reply.includes('ANCHOR-7F3A9C'), `${r.platform}: FILE unreachable — ${r.reply}`)
    assert.ok(r.reply.includes('BODY-4B21E8'), `${r.platform}: BODY missing`)
  }
})

test('E2E native: 三平台 triggered 都为 true', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) assert.equal(r.triggered, true, `${r.platform}: skill not triggered`)
})

test('E2E inject: 带路径补偿行时三平台也都读到', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('inject'), await baseCtx())
  for (const r of records) {
    assert.ok(r.reply.includes('ANCHOR-7F3A9C'), `${r.platform}: compensation line failed to restore the anchor`)
  }
})

test('E2E native + 非触发 prompt: 三平台 triggered 都为 false', { skip: !ENABLED }, async () => {
  const ctx = { ...(await baseCtx()), task: 'what is 2+2? answer with just the number' }
  const { records } = await runMatrix(cells('native'), ctx)
  for (const r of records) assert.equal(r.triggered, false, `${r.platform}: skill fired on a non-matching prompt`)
})

test('E2E L3: 宿主 skill 不可见', { skip: !ENABLED }, async () => {
  const hostDirs = [
    path.join(os.homedir(), '.claude/skills'),
    path.join(os.homedir(), '.hermes/skills'),
    path.join(os.homedir(), '.pi/agent/skills'),
  ]
  const hostSkills = new Set()
  for (const d of hostDirs) {
    if (!await fs.pathExists(d)) continue
    for (const n of await fs.readdir(d)) if (!CLAUDE_BUILTINS.has(n)) hostSkills.add(n)
  }
  assert.ok(hostSkills.size > 0, 'expected the host to have skills installed, otherwise this assertion is vacuous')

  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) {
    const seen = new Set([...(r.toolCalls ?? []).map(t => JSON.stringify(t.args)), r.reply].join(' ').match(/[a-z0-9-]+/g) ?? [])
    for (const name of hostSkills) {
      assert.ok(!seen.has(name), `jail breach: ${r.platform} saw host skill '${name}'; the run's result is not attributable to the skill under test`)
    }
  }
})

test('E2E: claude 的 builtinSkillFloor 实测值仍是 16', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  const claude = records.find(r => r.platform === 'claude')
  assert.equal(claude.builtinSkillFloor, 16, 'upstream changed its builtin skill set — update profiles.js and the L1 snapshot')
})

test('E2E: 三平台实测 model 与请求一致', { skip: !ENABLED }, async () => {
  const { records } = await runMatrix(cells('native'), await baseCtx())
  for (const r of records) {
    assert.equal(r.modelMismatch, false, `${r.platform}: requested ${MODEL}, got ${r.model}`)
  }
})
```

- [ ] **Step 2: 运行确认默认跳过**

Run: `node --test tests/harness/e2e.test.mjs`
Expected: PASS，7 个测试全部 `skipped`（真模型有成本，默认不跑）

- [ ] **Step 3: 开启真跑一次**

Run:
```bash
SKILL_HARNESS_E2E=1 node --test tests/harness/e2e.test.mjs
```
Expected: 7 个测试全绿。任一 `FILE unreachable` 都是框架 bug 而非被测 skill 的问题。

若 `E2E: claude 的 builtinSkillFloor 实测值仍是 16` 变红，说明上游改了内置 skill 集合——回到 `profiles.js` 与 `tests/harness/profile.test.mjs` 更新实测值，并在 `docs/superpowers/specs/measurements/` 追加记录，**不要**直接改断言了事。

- [ ] **Step 4: 补文档**

在 `docs/reference/testing-guide.md` 末尾追加一节：

```markdown
---

## tests/harness/ — 跨平台 harness 测试

三层，前两层零成本零 LLM，进默认 `npm test`；第三层真跑模型，默认 skip。

| 文件 | 层 | 测什么 |
|---|---|---|
| `select.test.mjs` | L2 | 选择器纯函数 + `matrix.json` 的 `reason` 必填 |
| `profile.test.mjs` | L1 | 三平台差异表整表 `deepEqual` 快照 |
| `parse.test.mjs` | L2 | 两个解析器，喂真实抓取的 fixture |
| `record.test.mjs` | L2 | `RunRecord` 规范化与 `unavailable` 归因 |
| `prompt.test.mjs` | L2 | 两种模式的 prompt 组装 |
| `jail.test.mjs` | L2/L3 | env 白名单、凭证打码、三个适配器的 args 与 install |
| `runner.test.mjs` | L2 | `planCell` 纯函数 |
| `coverage.test.mjs` | L2 | 覆盖率视图与 `contentHash` 过期判定 |
| `report.test.mjs` | L2 | 三态渲染 |
| `cli.test.mjs` | L2 | 参数解析与 dry-run |
| `e2e.test.mjs` | L3 | 真模型端到端，`SKILL_HARNESS_E2E=1` 开启 |

**fixtures 是真实抓取的，不是手写的。** 重新抓取的命令见
`docs/superpowers/specs/measurements/2026-08-14-native-vs-inject.md`。

**L1 快照变红时不要直接改断言。** 那些数（`builtinSkillFloor` 等）是实测值，
变了说明上游变了，应当重新实测并在 measurements 目录追加记录。
```

- [ ] **Step 5: 全量测试**

Run: `npm test`
Expected: 全绿，e2e 全部 skipped

- [ ] **Step 6: 提交**

```bash
git add tests/harness/e2e.test.mjs docs/reference/testing-guide.md
git commit -m "test(harness): L3 jail 有效性与端到端验收"
```

---

## 第一期验收清单

全部 task 完成后逐条核对（对应 spec「分期与验收 · 第一期」）：

- [ ] 同一个 skill + 任务，三平台 × 两模式各产出一份 `RunRecord`，`unavailable` 如实填写
- [ ] anchor probe 在 native 模式下三平台全部 `FILE` 通过；inject 模式下带补偿行也全部通过
- [ ] anchor probe 在 native 模式 + 非触发 prompt 下，三平台 `triggered` 均为 `false`
- [ ] `dry-run` 输出六份完整 prompt（3 平台 × 2 模式），可人工核对
- [ ] jail 探针未被触碰（L3 断言通过）；claude 的 `builtinSkillFloor = 16` 被 L1 快照钉住
- [ ] 选择器可用：`--skill` / `--bundle` / `--platform` / `--mode` 四个维度各有单测；`matrix.json` 中 `reason` 缺失时 `npm test` 变红
- [ ] `skill-harness coverage` 能对当前 39 个 skill 输出完整三态矩阵，`not-run` 显示为空格
- [ ] `npm test` 全绿，且 L2 fixture 数 > 0
- [ ] 全部 `RunRecord` 与 artifact 中不含任何凭证字符串
