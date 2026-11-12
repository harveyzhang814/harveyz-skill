# compose-agentsmd 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** 新增 devflow skill `compose-agentsmd`：按标准骨架，从项目配置（参数 + 描述槽 + 所选模块包）确定性地生成 AGENTS.md，并能检查手改、版本落后与未重新生成。

**Architecture:** 三层纯函数库（模板渲染 → 骨架/包/配置解析 → 拼装与状态判定）加一个薄 CLI。发布包放在 skill 的 `assets/packs/`，项目本地包放在 `.hskill/compose-agentsmd/packs/`，两者同一格式。库函数接受 `packsDir` 参数以便测试注入合成包；CLI 固定用 skill 自带的 `assets/packs`。

**Tech Stack:** Node.js ≥18 ESM（`.mjs`），只用内置模块（`node:fs`、`node:path`、`node:crypto`、`node:url`）；测试用 `node:test` + `node:assert/strict`。

**Spec:** `.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-spec.md`

**Spec Version and Scope:** v0.4，2026-11-11 获批；范围为全文（含第 8 节 S1–S13）。

## Global Constraints

- skill 目录：`skills/devflow/compose-agentsmd/`；skill `version: "0.1.0"`；`devflow` 包 `VERSION` 内容为 `1.0.0\n`。
- 只用 Node 内置模块；脚本与库为 ESM `.mjs`；不使用 `import.meta.dirname`（Node 18 不支持），用 `fileURLToPath(import.meta.url)`。
- 参数语法 `@{name}`；条件指令独占一行：`<!-- @if name -->`、`<!-- @else -->`、`<!-- @endif -->`；单层，不可嵌套。
- 项目配置目录固定为 `<root>/.hskill/compose-agentsmd/`，配置文件 `config.json`，描述槽 `slots/<槽id>.md`，本地包 `packs/<名>/`。
- 生成文件首行严格为：`<!-- compose-agentsmd: packs=<列表> sha256=<64位小写hex>; generated from .hskill/compose-agentsmd/, do not edit -->`；`<列表>` 为逗号分隔、按包名（不含 `local:` 前缀与版本）升序排列的 `<名>@<版本>` / `local:<名>`；`sha256` 是首行之后全部内容（含首行后的 `\n` 之后的所有字节）的哈希。
- 槽标记：描述槽 `<!-- slot:<id> -->`，标准槽 `<!-- slot:<id> pack=<名>@<版本> -->` 或 `<!-- slot:<id> pack=local:<名> -->`。
- 换行统一 `\n`；文件以单个 `\n` 结尾；槽之间恰好一个空行；连续空行压成一行。
- 退出码：`init` 0 已建 / 1 已存在；`generate` 0 已写 / 1 拒绝覆盖 / 2 配置或模板错误；`check` 0 ok / 1 其他 / 2 配置或模板错误。用法错误按 2。
- CLI 标准输出每行一个 `key=value`；错误走 stderr。
- 骨架 10 个槽的 id、顺序、类型、标题按 Spec 5.2 表，逐字一致。
- 不修改 Agent Canvas 仓库；V3 用到的 Agent Canvas 配置只放临时目录，不提交。
- SKILL.md 的 `description` 为英文，正文为中文；不提交 git 的边界写进 SKILL.md。
- `devflow` 包正文沿用 Agent Canvas `AGENTS.md`（提交 `14dbe3e0b`）原文措辞，只做 Spec 5.4 / 5.4a 表与兜底规则允许的删改。

## Review Focus

- `agent_canvas: false` 时生成结果残留画布相关词或 Step 8 引用 → 不得出现 Spec V2 列出的任何词（Task 4 测试）。
- 目标 AGENTS.md 被手改或无首行标记时执行 `generate` → 不加 `--force` 退出 1 且文件字节不变（Task 3 测试）。
- 本地包与发布包同名、`slot_packs` 拆开联动组、本地模板引用未声明参数 → 退出 2 且不写文件（Task 2、Task 3 测试）。
- 条件块去掉指令行后留下多余空行，导致同一输入不同输出或格式漂移 → 连续空行压成一行，两次生成逐字节一致（Task 1、Task 3 测试）。
- hskill 安装时的变量替换改写包文件 → 安装后 `assets/packs/**` 与仓库逐字节一致（Task 5 测试）。

---

## 文件总览

| 文件 | 职责 | 任务 |
|---|---|---|
| `skills/devflow/compose-agentsmd/scripts/lib/template.mjs` | 模板渲染（参数代入、单层条件、报错带文件行号） | 1 |
| `skills/devflow/compose-agentsmd/scripts/lib/config.mjs` | 读骨架、加载发布包与本地包、校验配置、解析每槽来源与生效参数 | 2 |
| `skills/devflow/compose-agentsmd/assets/skeleton.json` | 骨架定义 | 2 |
| `skills/devflow/compose-agentsmd/scripts/lib/compose.mjs` | 拼装文本、首行与槽标记、`init`/`generate`/`check` 逻辑 | 3 |
| `skills/devflow/compose-agentsmd/scripts/compose-agentsmd.mjs` | CLI 入口（参数解析、输出、退出码） | 3 |
| `skills/devflow/compose-agentsmd/assets/config.template.json` | `init` 写入的配置模板 | 3 |
| `skills/devflow/compose-agentsmd/assets/packs/devflow/*` | `devflow` 发布包：`pack.json`、`VERSION`、5 个槽模板 | 4 |
| `skills/devflow/compose-agentsmd/SKILL.md` | skill 说明（初始化、生成/升级、本地包、检查、边界） | 5 |
| `skills-index.json`、`package.json` | 注册与打包清单 | 5 |
| `tests/compose-agentsmd-template.test.mjs` | Task 1 测试 | 1 |
| `tests/compose-agentsmd-config.test.mjs` | Task 2 测试 | 2 |
| `tests/compose-agentsmd-cli.test.mjs` | Task 3 测试 | 3 |
| `tests/compose-agentsmd-devflow-pack.test.mjs` | Task 4 测试 | 4 |
| `tests/compose-agentsmd-skill.test.mjs` | Task 5 测试 | 5 |
| `tests/fixtures/compose-agentsmd/` | 合成发布包、合成本地包、最小配置 | 2、3 |

测试放仓库 `tests/`：`npm test` 以 `node --test tests/*.test.mjs` 运行 Node 测试，skill 目录下的 `tests/` 只发现 bats/pytest（`scripts/run-skill-tests.sh`）。

---

### Task 1: 模板渲染器

**Prerequisites:** 无

**Files:**
- Create: `skills/devflow/compose-agentsmd/scripts/lib/template.mjs`
- Test: `tests/compose-agentsmd-template.test.mjs`

**Interfaces:**
- Produces:
  - `class TemplateError extends Error { file: string; line: number }`（`message` 含 `<file>:<line>`）
  - `renderTemplate(text: string, params: Record<string, string|boolean>, file: string): string`
  - `templateParams(text: string, file: string): string[]`——模板中引用的全部参数名（`@{}` 与 `@if`），去重、按出现顺序；语法错误抛 `TemplateError`

- [ ] **Step 1: 编写失败测试**

```js
test('substitutes @{name} with string params', () => {
  assert.equal(renderTemplate('branch @{b}.\n', { b: 'staging' }, 'm.md'), 'branch staging.\n')
})
test('leaves {{name}} untouched', () => {
  assert.equal(renderTemplate('{{x}} @{b}\n', { b: 'y' }, 'm.md'), '{{x}} y\n')
})
test('@if on true boolean keeps the if-branch and drops directives', () => {
  const t = 'a\n<!-- @if c -->\nyes\n<!-- @else -->\nno\n<!-- @endif -->\nb\n'
  assert.equal(renderTemplate(t, { c: true }, 'm.md'), 'a\nyes\nb\n')
  assert.equal(renderTemplate(t, { c: false }, 'm.md'), 'a\nno\nb\n')
})
test('@if on string tests non-empty', () => {
  const t = '<!-- @if e -->\nE2E: @{e}\n<!-- @endif -->\n'
  assert.equal(renderTemplate(t, { e: 'playwright' }, 'm.md'), 'E2E: playwright\n')
  assert.equal(renderTemplate(t, { e: '' }, 'm.md'), '')
})
test('collapses consecutive blank lines left by removed blocks', () => {
  const t = 'a\n\n<!-- @if c -->\nx\n<!-- @endif -->\n\nb\n'
  assert.equal(renderTemplate(t, { c: false }, 'm.md'), 'a\n\nb\n')
})
test('unknown parameter throws TemplateError with file and line', () => {
  assert.throws(() => renderTemplate('ok\n@{nope}\n', {}, 'm.md'),
    e => e instanceof TemplateError && e.file === 'm.md' && e.line === 2)
})
test('unclosed @if throws', () => {
  assert.throws(() => renderTemplate('<!-- @if c -->\nx\n', { c: true }, 'm.md'), TemplateError)
})
test('nested @if throws', () => {
  const t = '<!-- @if c -->\n<!-- @if c -->\nx\n<!-- @endif -->\n<!-- @endif -->\n'
  assert.throws(() => renderTemplate(t, { c: true }, 'm.md'), e => e instanceof TemplateError && e.line === 2)
})
test('stray @else / @endif throws', () => {
  assert.throws(() => renderTemplate('<!-- @else -->\n', {}, 'm.md'), TemplateError)
  assert.throws(() => renderTemplate('<!-- @endif -->\n', {}, 'm.md'), TemplateError)
})
test('@if on unknown parameter throws', () => {
  assert.throws(() => renderTemplate('<!-- @if zz -->\nx\n<!-- @endif -->\n', {}, 'm.md'), TemplateError)
})
test('templateParams lists referenced names in order', () => {
  assert.deepEqual(templateParams('<!-- @if c -->\n@{b} @{a} @{b}\n<!-- @endif -->\n', 'm.md'), ['c', 'b', 'a'])
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/compose-agentsmd-template.test.mjs`
Expected: FAIL，提示无法导入 `skills/devflow/compose-agentsmd/scripts/lib/template.mjs`

- [ ] **Step 3: 在 `scripts/lib/template.mjs` 中实现 `renderTemplate`、`templateParams`、`TemplateError`**

Approach: 按行扫描，状态机只有“块外 / if 分支 / else 分支”；指令行正则 `^<!-- @(if \w+|else|endif) -->$`；参数正则 `/@\{(\w+)\}/g`；输出后用 `/\n{3,}/g → '\n\n'` 压空行。

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/compose-agentsmd-template.test.mjs`
Expected: PASS（11 项）

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/compose-agentsmd/scripts/lib/template.mjs tests/compose-agentsmd-template.test.mjs
git commit -m "feat(compose-agentsmd): add template renderer"
```

---

### Task 2: 骨架、模块包加载与配置校验

**Prerequisites:** Task 1

**Files:**
- Create: `skills/devflow/compose-agentsmd/assets/skeleton.json`
- Create: `skills/devflow/compose-agentsmd/scripts/lib/config.mjs`
- Create: `tests/fixtures/compose-agentsmd/packs/alpha/{pack.json,VERSION,flow-summary.md,instruction-sources.md,flow-steps.md}`（合成发布包；见下）
- Create: `tests/fixtures/compose-agentsmd/packs/beta/{pack.json,VERSION,flow-steps.md}`
- Test: `tests/compose-agentsmd-config.test.mjs`

**Interfaces:**
- Consumes: Task 1 的 `templateParams`、`TemplateError`
- Produces:
  - `class ConfigError extends Error {}`
  - `loadSkeleton(skeletonPath?: string): Array<{ id: string, kind: 'standard'|'description', heading: string|null }>`——默认读 skill 的 `assets/skeleton.json`；`overview` 的 `heading` 为 `null`（标题来自 `title`）
  - `loadPacks({ packsDir: string, localPacksDir: string }): Map<string, { name, source: 'shipped'|'local', version: string|null, slots: string[], linked: string[][], params: Record<string,{type,required?,default?}>, dir: string }>`
  - `resolveConfig({ config: object, skeleton, packs }): { params: Record<string,string|boolean>, slots: Array<{ id, kind, heading, pack: string|null }> }`——`pack` 为填该标准槽的包名；无来源或被关闭的标准槽 `pack: null`；任何校验失败抛 `ConfigError`（消息指出字段、包或槽）

骨架文件按 Spec 5.2：`overview`(description, null) · `flow-summary`(standard, null) · `principles`(description, `## 项目原则`) · `instruction-sources`(standard, null) · `platform-fallbacks`(standard, null) · `platform-adaptation`(description, `## 平台适配`) · `repo-env`(description, `## 仓库环境`) · `flow-steps`(standard, null) · `release-acceptance`(standard, null) · `other`(description, `## 其他约定`)。标准槽 `heading` 为 `null`（标题由模块自带）。

合成包：`alpha` 声明 `slots: ["flow-summary","instruction-sources","flow-steps"]`、`linked: [["flow-summary","flow-steps"]]`、`params: { branch: {type:"string", required:true}, extra: {type:"string", default:""} }`；`beta` 声明 `slots: ["flow-steps"]`、`params: { branch: {type:"string", required:true} }`。模板正文各含一个标题行（如 `## Flow @{branch}`），`alpha/flow-steps.md` 另含 `<!-- @if extra -->…<!-- @endif -->` 块。`VERSION` 均为 `1.0.0`。

- [ ] **Step 1: 编写失败测试**

```js
const base = { title: 'T', pack: 'alpha', branch: 'main' }
test('skeleton has the 10 slots in spec order', () => {
  assert.deepEqual(loadSkeleton().map(s => s.id), ['overview','flow-summary','principles','instruction-sources','platform-fallbacks','platform-adaptation','repo-env','flow-steps','release-acceptance','other'])
})
test('resolves slots from the main pack and applies param defaults', () => {
  const r = resolveConfig({ config: base, skeleton, packs: loadPacks(dirs) })
  assert.equal(r.slots.find(s => s.id === 'flow-steps').pack, 'alpha')
  assert.equal(r.slots.find(s => s.id === 'instruction-sources').pack, 'alpha')
  assert.equal(r.slots.find(s => s.id === 'platform-fallbacks').pack, null)
  assert.equal(r.params.extra, '')
  assert.equal(r.params.agent_canvas, false)
})
test('missing required param is rejected', () => {
  assert.throws(() => resolveConfig({ config: { title: 'T', pack: 'alpha' }, skeleton, packs }), /branch/)
})
test('unknown field is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, bogus: 1 }, skeleton, packs }), /bogus/)
})
test('wrong type is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, agent_canvas: 'yes' }, skeleton, packs }), /agent_canvas/)
})
test('slot_packs splitting a linked group is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, slot_packs: { 'flow-steps': 'beta' } }, skeleton, packs }), /linked|联动/)
})
test('slot_packs to a pack that does not declare the slot is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, slot_packs: { 'flow-summary': 'beta' } }, skeleton, packs }), /beta/)
})
test('disabling only part of a linked group is rejected; whole group is allowed', () => {
  assert.throws(() => resolveConfig({ config: { ...base, disabled_slots: ['flow-summary'] }, skeleton, packs }), ConfigError)
  const r = resolveConfig({ config: { ...base, disabled_slots: ['flow-summary', 'flow-steps'] }, skeleton, packs })
  assert.equal(r.slots.find(s => s.id === 'flow-steps').pack, null)
})
test('disabled_slots naming a description slot is rejected', () => {
  assert.throws(() => resolveConfig({ config: { ...base, disabled_slots: ['other'] }, skeleton, packs }), /other/)
})
test('same pack name in shipped and local dirs is rejected', () => {
  // localPacksDir 里放一个名为 alpha 的包
  assert.throws(() => loadPacks({ packsDir, localPacksDir: dupDir }), /alpha/)
})
test('template referencing an undeclared param is rejected', () => {
  // 本地包 gamma 的模板引用 @{undeclared}
  assert.throws(() => loadPacks({ packsDir, localPacksDir: badParamDir }), /undeclared/)
})
test('conflicting declarations of the same param across used packs are rejected', () => {
  // 本地包 delta 声明 branch 为 boolean，并通过 slot_packs 被使用
  assert.throws(() => resolveConfig({ config: { ...base, ...useDelta }, skeleton, packs: withDelta }), /branch/)
})
test('agent_canvas true with spec_dir outside docs/superpowers/specs is rejected', () => {
  // 包 epsilon 声明 spec_dir
  assert.throws(() => resolveConfig({ config: { title: 'T', pack: 'epsilon', agent_canvas: true, spec_dir: 'docs/specs' }, skeleton, packs: withEpsilon }), /spec_dir/)
})
```

（`dupDir`、`badParamDir`、`withDelta`、`withEpsilon` 在测试里用 `mkdtempSync` 临时建目录写入；`dirs = { packsDir: 'tests/fixtures/compose-agentsmd/packs', localPacksDir: <空临时目录> }`。）

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/compose-agentsmd-config.test.mjs`
Expected: FAIL，提示无法导入 `scripts/lib/config.mjs`

- [ ] **Step 3: 创建 `assets/skeleton.json`，在 `scripts/lib/config.mjs` 实现 `loadSkeleton`、`loadPacks`、`resolveConfig`、`ConfigError`**

Approach: `loadPacks` 读两个目录（不存在视为空），对每个包校验 `pack.json`（`name` 与目录名一致、`slots` 均为骨架标准槽且有同名 `.md`、`linked` 每组成员都在 `slots` 内、`params` 类型仅 `string`/`boolean`），并用 `templateParams` 核对模板只引用本包 `params` 与骨架级 `agent_canvas`；`resolveConfig` 依次：骨架级字段类型 → 解析每槽来源 → 联动组完整性 → 生效参数并集与冲突 → 未知字段 → 必填与默认值 → `spec_dir` 前缀规则。

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/compose-agentsmd-template.test.mjs tests/compose-agentsmd-config.test.mjs`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/compose-agentsmd/assets/skeleton.json skills/devflow/compose-agentsmd/scripts/lib/config.mjs tests/fixtures/compose-agentsmd tests/compose-agentsmd-config.test.mjs
git commit -m "feat(compose-agentsmd): load skeleton and packs, validate config"
```

---

### Task 3: 拼装、`init` / `generate` / `check` 与 CLI

**Prerequisites:** Task 2

**Files:**
- Create: `skills/devflow/compose-agentsmd/scripts/lib/compose.mjs`
- Create: `skills/devflow/compose-agentsmd/scripts/compose-agentsmd.mjs`
- Create: `skills/devflow/compose-agentsmd/assets/config.template.json`
- Test: `tests/compose-agentsmd-cli.test.mjs`

**Interfaces:**
- Consumes: Task 1 `renderTemplate`、`TemplateError`；Task 2 `loadSkeleton`、`loadPacks`、`resolveConfig`、`ConfigError`
- Produces:
  - `composeText({ root: string, packsDir: string }): { text: string, packs: Array<{ name, source, version }> }`——完整 AGENTS.md 文本（含首行）
  - `parseHeader(text: string): { packs: Array<{ name, source: 'shipped'|'local', version: string|null }>, sha256: string } | null`
  - `runInit({ root, packsDir? }): { code: 0|1, lines: string[] }`
  - `runGenerate({ root, packsDir?, force?: boolean }): { code: 0|1|2, lines: string[], errors: string[] }`
  - `runCheck({ root, packsDir? }): { code: 0|1|2, lines: string[], errors: string[] }`——`lines` 含一行 `status=<逗号分隔状态>`、一行 `path=<AGENTS.md 绝对路径>`、每个发布包一行 `pack=<名> installed=<版本> generated=<版本或空>`
  - CLI：`node scripts/compose-agentsmd.mjs <init|generate|check> [--root <dir>] [--force]`，把 `lines` 打到 stdout、`errors` 打到 stderr，以 `code` 退出；`packsDir` 固定为 skill 的 `assets/packs`

`config.template.json`：`{ "title": "", "pack": "devflow", "agent_canvas": false, "integration_branch": "", "merge_command": "" }`（字段顺序如此，2 空格缩进，结尾换行）。`init` 写入它，并为每个描述槽建空文件 `slots/<id>.md`（`overview`、`principles`、`platform-adaptation`、`repo-env`、`other`）。

拼装规则（Spec 5.2、5.6）：按骨架顺序逐槽产出块；描述槽文件不存在或去空白后为空则跳过（`overview` 例外：总产出 `# <title>`，后接正文如有）；描述槽块 = 槽标记 + 标题（若有）+ 空行 + 正文；标准槽块 = 槽标记 + 渲染结果；`pack: null` 的标准槽跳过，若因“无来源”跳过（非 `disabled_slots`）在 `errors` 记一行提示但不影响退出码；`release-acceptance` 在 `agent_canvas: false` 时跳过。描述槽内容含 `<!-- slot:` 或 `<!-- compose-agentsmd:` → `ConfigError`。

- [ ] **Step 1: 编写失败测试**

测试用 `mkdtempSync` 建项目根，写入使用 fixture 包 `alpha` 的最小配置与描述槽，所有调用传 `packsDir: 'tests/fixtures/compose-agentsmd/packs'`。

```js
test('V1 generate twice is byte-identical and check reports ok', () => {
  assert.equal(runGenerate({ root, packsDir }).code, 0)
  const a = readFileSync(agents)
  assert.equal(runGenerate({ root, packsDir }).code, 0)
  assert.ok(a.equals(readFileSync(agents)))
  const c = runCheck({ root, packsDir })
  assert.equal(c.code, 0); assert.ok(c.lines.includes('status=ok'))
})
test('header and slot markers follow the spec format', () => {
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  const [first, ...rest] = text.split('\n')
  const h = parseHeader(text)
  assert.match(first, /^<!-- compose-agentsmd: packs=alpha@1\.0\.0 sha256=[0-9a-f]{64}; generated from \.hskill\/compose-agentsmd\/, do not edit -->$/)
  assert.equal(h.sha256, createHash('sha256').update(rest.join('\n')).digest('hex'))
  assert.ok(text.includes('<!-- slot:flow-steps pack=alpha@1.0.0 -->'))
  assert.ok(text.includes('<!-- slot:overview -->\n# T\n'))
  assert.ok(text.endsWith('\n') && !text.endsWith('\n\n'))
})
test('empty description slot is omitted, overview title always present', () => {
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  assert.ok(!text.includes('slot:principles')); assert.ok(text.includes('# T'))
})
test('V5 hand edit is detected and generate refuses without --force', () => {
  runGenerate({ root, packsDir })
  writeFileSync(agents, readFileSync(agents, 'utf8').replace('# T', '# T!'))
  const before = readFileSync(agents)
  const c = runCheck({ root, packsDir }); assert.equal(c.code, 1); assert.match(c.lines.join('\n'), /status=.*hand-edited/)
  assert.equal(runGenerate({ root, packsDir }).code, 1); assert.ok(before.equals(readFileSync(agents)))
  assert.equal(runGenerate({ root, packsDir, force: true }).code, 0)
})
test('AGENTS.md without header counts as hand-edited', () => {
  writeFileSync(agents, '# handwritten\n')
  assert.equal(runGenerate({ root, packsDir }).code, 1)
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /hand-edited/)
})
test('missing AGENTS.md reports missing', () => {
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /status=missing/)
})
test('V6 older generated pack version reports outdated', () => {
  runGenerate({ root, packsDir })
  rewriteHeaderVersion(agents, 'alpha', '0.9.0')   // 改首行版本并重算 sha256
  const c = runCheck({ root, packsDir })
  assert.equal(c.code, 1); assert.match(c.lines.join('\n'), /outdated/)
  assert.ok(c.lines.includes('pack=alpha installed=1.0.0 generated=0.9.0'))
})
test('newer generated version than installed reports stale, not outdated', () => {
  runGenerate({ root, packsDir }); rewriteHeaderVersion(agents, 'alpha', '9.0.0')
  const s = runCheck({ root, packsDir }).lines.join('\n')
  assert.match(s, /stale/); assert.doesNotMatch(s, /outdated/)
})
test('config change without regenerate reports stale', () => {
  runGenerate({ root, packsDir }); writeSlot(root, 'other', 'new text\n')
  assert.match(runCheck({ root, packsDir }).lines.join('\n'), /status=stale/)
})
test('V10 slot_packs moves a non-linked slot to a local pack and both packs are recorded', () => {
  // 本地包 local-a 只声明非联动槽 instruction-sources，模板正文含 'LOCAL-A BODY'；
  // 配置 slot_packs: { 'instruction-sources': 'local-a' }，主包仍为 alpha
  runGenerate({ root, packsDir })
  const text = readFileSync(agents, 'utf8')
  assert.ok(text.includes('<!-- slot:instruction-sources pack=local:local-a -->\n'))
  assert.ok(text.includes('LOCAL-A BODY'))
  assert.ok(text.includes('<!-- slot:flow-steps pack=alpha@1.0.0 -->'))
  assert.match(text.split('\n')[0], /^<!-- compose-agentsmd: packs=alpha@1\.0\.0,local:local-a sha256=/)
})
test('V11 editing a local pack template reports stale, not outdated', () => {
  runGenerate({ root, packsDir }); appendToLocalTemplate(root, 'local-a', 'instruction-sources', 'x\n')
  const s = runCheck({ root, packsDir }).lines.join('\n')
  assert.match(s, /stale/); assert.doesNotMatch(s, /outdated/)
})
test('V7 config or template errors exit 2 and write nothing', () => {
  for (const breakIt of [setUnknownParamInLocalTemplate, setUnclosedIfInLocalTemplate, setNestedIfInLocalTemplate, disableOnlyFlowSummary, splitLinkedGroup]) {
    const r = freshRoot(); breakIt(r)
    assert.equal(runGenerate({ root: r, packsDir }).code, 2); assert.equal(existsSync(join(r, 'AGENTS.md')), false)
  }
})
test('description slot containing a slot marker is rejected', () => {
  writeSlot(root, 'other', '<!-- slot:x -->\n')
  assert.equal(runGenerate({ root, packsDir }).code, 2)
})
test('generate and check without config dir exit 2', () => {
  const r = mkdtempSync(join(tmpdir(), 'ca-'))
  assert.equal(runGenerate({ root: r, packsDir }).code, 2); assert.equal(runCheck({ root: r, packsDir }).code, 2)
})
test('init creates config and empty description slots; second init exits 1 and changes nothing', () => {
  const r = mkdtempSync(join(tmpdir(), 'ci-'))
  assert.equal(runInit({ root: r }).code, 0)
  assert.deepEqual(JSON.parse(readFileSync(join(r, '.hskill/compose-agentsmd/config.json'), 'utf8')).pack, 'devflow')
  for (const id of ['overview','principles','platform-adaptation','repo-env','other'])
    assert.equal(readFileSync(join(r, `.hskill/compose-agentsmd/slots/${id}.md`), 'utf8'), '')
  writeFileSync(join(r, '.hskill/compose-agentsmd/slots/other.md'), 'keep\n')
  assert.equal(runInit({ root: r }).code, 1)
  assert.equal(readFileSync(join(r, '.hskill/compose-agentsmd/slots/other.md'), 'utf8'), 'keep\n')
})
test('CLI maps results to stdout and exit codes', () => {
  const r = spawnSync(process.execPath, [CLI, 'check', '--root', emptyDir], { encoding: 'utf8' })
  assert.equal(r.status, 2)
  const u = spawnSync(process.execPath, [CLI, 'bogus'], { encoding: 'utf8' })
  assert.equal(u.status, 2)
})
```

（`rewriteHeaderVersion`、`writeSlot`、`appendToLocalTemplate`、`freshRoot` 及五个 `breakIt` 为测试文件内辅助函数。V10、V11 的根在 `slots` 外另建本地包 `.hskill/compose-agentsmd/packs/local-a/`（`pack.json` 声明 `slots: ["instruction-sources"]`、`params: {}`），配置加 `slot_packs`。）

首行 `packs` 的排序键为包名本身（`alpha`、`local-a`），不含 `local:` 前缀与版本；按 JavaScript 默认字符串比较升序。

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/compose-agentsmd-cli.test.mjs`
Expected: FAIL，提示无法导入 `scripts/lib/compose.mjs`

- [ ] **Step 3: 实现 `scripts/lib/compose.mjs` 的五个导出、`scripts/compose-agentsmd.mjs` CLI，创建 `assets/config.template.json`**

Approach: `runCheck` 先 `composeText`（错误→2）；磁盘无文件 → `missing`；有文件则：首行缺失或哈希不符 → `hand-edited`；逐个发布包比较首行版本与已装版本，首行版本低于已装 → `outdated`；磁盘字节与新拼装不一致且未命中前述原因 → `stale`（首行版本高于已装也归 `stale`）。版本比较按 `x.y.z` 数字逐段比较。`runGenerate` 先拼装（错误→2，不写），再判断目标文件是否手改（无首行或哈希不符）→ 无 `--force` 返回 1。

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/compose-agentsmd-template.test.mjs tests/compose-agentsmd-config.test.mjs tests/compose-agentsmd-cli.test.mjs`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/compose-agentsmd/scripts skills/devflow/compose-agentsmd/assets/config.template.json tests/compose-agentsmd-cli.test.mjs tests/fixtures/compose-agentsmd
git commit -m "feat(compose-agentsmd): compose AGENTS.md with init, generate and check"
```

---

### Task 4: `devflow` 发布包

**Prerequisites:** Task 3

**Files:**
- Create: `skills/devflow/compose-agentsmd/assets/packs/devflow/pack.json`（内容按 Spec 5.2a 示例，逐字段一致）
- Create: `skills/devflow/compose-agentsmd/assets/packs/devflow/VERSION`（`1.0.0\n`）
- Create: `skills/devflow/compose-agentsmd/assets/packs/devflow/{flow-summary,instruction-sources,platform-fallbacks,flow-steps,release-acceptance}.md`
- Test: `tests/compose-agentsmd-devflow-pack.test.mjs`

**Interfaces:**
- Consumes: Task 3 `runGenerate`、`composeText`（`packsDir` 用 skill 的 `assets/packs`）
- Produces: 发布包 `devflow@1.0.0`

模板内容来源：`~/Projects/agent-canvas/AGENTS.md` 在提交 `14dbe3e0b` 的版本（`git -C ~/Projects/agent-canvas show 14dbe3e0b:AGENTS.md`）；按 Spec 5.4 表、兜底规则与 5.4a 逐节改写；`## 验收标准` V 格式要点取自 `git -C ~/Projects/agent-canvas show 14dbe3e0b:docs/superpowers/specs/2026-10-13-requirement-acceptance-design.md` 的 §3.1。每处按“兜底规则”做的改动，记入本任务提交说明正文（逐条一行），供 Task 6 对照。

- [ ] **Step 1: 编写失败测试**

```js
const CANVAS_WORDS = ['describe-node','capture-requirement','relate-node','observe-node-quality','judge-release','Agent Canvas','Step 8','画布','节点','第二道关','版本验收','V<n>｜']
const PROJECT_WORDS = ['Electron','simulate-user','sync-design','.design-scratch','staging','merge-to-staging','main↔renderer','.claude/worktrees','AGENTS.pre-init-spec','2026-10-13-requirement-acceptance']
const cfg = { title: 'P', pack: 'devflow', integration_branch: 'develop', merge_command: 'make merge' }

test('V2 agent_canvas false leaves no canvas wording but keeps acceptance criteria', () => {
  const text = generateWith({ ...cfg, agent_canvas: false })
  for (const w of CANVAS_WORDS) assert.ok(!text.includes(w), w)
  assert.ok(text.includes('## 验收标准'))
  assert.ok(!text.includes('slot:release-acceptance'))
})
test('V2 agent_canvas true includes Step 8, release acceptance and V format', () => {
  const text = generateWith({ ...cfg, agent_canvas: true })
  assert.ok(text.includes('## Step 8')); assert.ok(text.includes('## 版本验收')); assert.ok(text.includes('V1｜'))
})
test('V4 devflow pack files contain no Agent Canvas project specifics', () => {
  for (const f of readdirSync(PACK)) for (const w of PROJECT_WORDS)
    assert.ok(!readFileSync(join(PACK, f), 'utf8').includes(w), `${f}: ${w}`)
})
test('params are substituted into the flow', () => {
  const text = generateWith({ ...cfg, e2e: 'Playwright E2E', complexity_signals: '改动公共 API' })
  for (const v of ['develop', 'make merge', 'Playwright E2E', '改动公共 API', 'docs/superpowers/specs']) assert.ok(text.includes(v), v)
  assert.ok(!text.includes('@{'))
})
test('pack.json matches the spec declaration', () => {
  const p = JSON.parse(readFileSync(join(PACK, 'pack.json'), 'utf8'))
  assert.deepEqual(p.slots, ['flow-summary','instruction-sources','platform-fallbacks','flow-steps','release-acceptance'])
  assert.deepEqual(p.linked, [['flow-summary','flow-steps']])
  assert.equal(p.params.integration_branch.required, true)
  assert.equal(readFileSync(join(PACK, 'VERSION'), 'utf8'), '1.0.0\n')
})
```

（`generateWith(config)` 在临时根写配置、调用 `runGenerate`，返回生成文本；`PACK` 为 `skills/devflow/compose-agentsmd/assets/packs/devflow`。）

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/compose-agentsmd-devflow-pack.test.mjs`
Expected: FAIL，提示包 `devflow` 不存在

- [ ] **Step 3: 按 Spec 5.4、5.4a 与兜底规则编写五个槽模板，创建 `pack.json`、`VERSION`**

- [ ] **Step 4: 运行本任务的全部测试，验证通过**

Run: `node --test tests/compose-agentsmd-*.test.mjs`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/compose-agentsmd/assets/packs tests/compose-agentsmd-devflow-pack.test.mjs
git commit -m "feat(compose-agentsmd): add devflow pack 1.0.0 distilled from Agent Canvas"
```

---

### Task 5: SKILL.md、注册与安装验证

**Prerequisites:** Task 4

**Files:**
- Create: `skills/devflow/compose-agentsmd/SKILL.md`
- Modify: `skills-index.json`（新增条目；`bundleMeta.devflow` 追加说明）
- Modify: `package.json`（由 `node scripts/generate-npmignore.js` 重新生成 `files`）
- Test: `tests/compose-agentsmd-skill.test.mjs`

**Interfaces:**
- Consumes: Task 3 CLI 路径与子命令；Task 4 包
- Produces: 可安装、已注册的 skill

SKILL.md 要求：frontmatter `name: compose-agentsmd`、英文 `description`（含触发语：compose / generate / check AGENTS.md、adopt the standard AGENTS.md skeleton）、`user_invocable: true`、`version: "0.1.0"`；正文中文，按 Spec 5.8 写「初始化」「生成 / 升级」「本地包」「检查」「边界」五节；脚本以 `<skill 目录>/scripts/compose-agentsmd.mjs` 引用（不写 `~/.claude/skills` 绝对路径）。`skills-index.json` 条目：`{ "path": "devflow/compose-agentsmd", "bundle": "devflow", "installScope": "global", "contentHash": <按 publish-skill F8 计算>, "contentVersion": "0.1.0" }`；`bundleMeta.devflow` 末尾在右括号前追加“；compose-agentsmd — 从标准骨架生成 AGENTS.md”。

- [ ] **Step 1: 编写失败测试**

```js
test('compose-agentsmd is registered in devflow with matching version and hash', async () => {
  const entry = index.skills.find(s => s.path === 'devflow/compose-agentsmd')
  assert.equal(entry.bundle, 'devflow'); assert.equal(entry.installScope, 'global')
  assert.equal(entry.contentVersion, '0.1.0'); assert.equal(entry.contentHash, hash(body))
  assert.match(index.bundleMeta.devflow, /compose-agentsmd/)
  assert.ok(pkg.files.includes('skills/devflow/compose-agentsmd/'))
})
test('SKILL.md states the actions, boundaries and portable script path', () => {
  for (const p of ['## 初始化', '## 生成 / 升级', '## 本地包', '## 检查', '## 边界',
                   'scripts/compose-agentsmd.mjs', '--force', 'slot_packs', '不提交 git'])
    assert.ok(body.includes(p), p)
  assert.ok(!body.includes('~/.claude/skills'))
})
test('V8 hskill install copies pack files byte-for-byte', () => {
  const home = mkdtempSync(join(tmpdir(), 'hs-'))
  mkdirSync(join(home, '.claude/skills'), { recursive: true })
  const r = spawnSync(process.execPath, ['bin/cli.js', 'install', '--skill', 'compose-agentsmd', '--target', 'claude', '--scope', 'user', '--force'], { cwd: root, env: { ...process.env, HOME: home }, encoding: 'utf8' })
  assert.equal(r.status, 0, r.stderr)
  for (const f of walk(join(root, 'skills/devflow/compose-agentsmd/assets/packs')))
    assert.ok(readFileSync(f).equals(readFileSync(f.replace(join(root, 'skills/devflow'), join(home, '.claude/skills')))), f)
})
```

- [ ] **Step 2: 运行测试，验证它失败**

Run: `node --test tests/compose-agentsmd-skill.test.mjs`
Expected: FAIL（未注册、SKILL.md 不存在）

- [ ] **Step 3: 编写 SKILL.md，更新 `skills-index.json`，运行 `node scripts/generate-npmignore.js`**

- [ ] **Step 4: 运行全量测试，验证通过**

Run: `npm test`
Expected: 全部通过（含 `tests/skills.bats` 的 SKILL.md 格式校验）

- [ ] **Step 5: 提交**

```bash
git add skills/devflow/compose-agentsmd/SKILL.md skills-index.json package.json tests/compose-agentsmd-skill.test.mjs
git commit -m "feat(compose-agentsmd): add SKILL.md and register in devflow bundle"
```

---

### Task 6: Agent Canvas 对照验证（V3，不提交配置）

**Prerequisites:** Task 5

**Files:**
- 无仓库文件改动（只在临时目录操作）

**Interfaces:**
- Consumes: Task 3 CLI；Task 4 包；Task 4 提交说明中的兜底改动清单

- [ ] **Step 1: 在临时目录准备项目根**

Run: `T=$(mktemp -d) && git -C ~/Projects/agent-canvas show 14dbe3e0b:AGENTS.md > "$T/AGENTS.md" && cp "$T/AGENTS.md" "$T/AGENTS.orig.md"`
Expected: `$T/AGENTS.orig.md` 为 394 行

- [ ] **Step 2: 按 SKILL.md「初始化」把原文拆进配置**

Run: `node skills/devflow/compose-agentsmd/scripts/compose-agentsmd.mjs init --root "$T"`，然后按 Spec 5.4 表把项目内容写入 `$T/.hskill/compose-agentsmd/slots/*.md`，参数写入 `config.json`（`agent_canvas: true`、`integration_branch: "staging"`、`merge_command: "scripts/merge-to-staging.sh"`、`e2e` 为 `simulate-user` Electron E2E 的原文表述、`complexity_signals` 为 main↔renderer↔utilityProcess / IPC 的原文表述）
Expected: `init` 退出 0

- [ ] **Step 3: 生成并对照**

Run: `node skills/devflow/compose-agentsmd/scripts/compose-agentsmd.mjs generate --root "$T" --force && diff "$T/AGENTS.orig.md" "$T/AGENTS.md"`
Expected: 生成退出 0；diff 中每一处差异都能归入 Spec 5.4 表的某一行、5.4a 或兜底规则清单中的某一条

- [ ] **Step 4: 写对照结果**

在实施汇报中给出逐节对照表（原文小节 → 生成位置 → 差异 → 归入的 5.4 行或兜底条目）；出现无法归类的差异时，回到 Task 4 修正模板并重跑本任务。不提交 `$T` 下任何文件。
