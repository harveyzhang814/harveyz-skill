# High-priority cross-platform skill remediation implementation plan

**目标：** 修复七个已发布 skill 的 Claude 专属路径、工具和调度假设，并以自动化守卫防止回归。

**架构：** 共享 `SKILL.md` 描述可移植能力和相对 `SKILL_DIR` 资源解析；平台差异仅放入受控适配说明。以一个 Node 静态测试保护共享入口，现有 Python/Bats 测试验证运行资产和元数据。

**技术栈：** Markdown/YAML、Node `node:test`、Bats、pytest、hskill CLI。

**规格：** `docs/superpowers/specs/2026-09-24-cross-platform-high-priority-design.md`

---

### Task 1: Add the portability regression guard

**文件：**
- 创建: `tests/skill-portability.test.mjs`
- 修改: `package.json:10-12`

- [ ] **Step 1: Write focused failing portability tests**

Create `tests/skill-portability.test.mjs` with one fixture table per shared entrypoint and a separate Codex adapter case. Each entry supplies required capability wording and forbidden host-specific tokens. Use `readFile`, `resolve`, and `node:test` assertions; do not scan archived files or legitimate non-Codex platform adapters.

```js
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import test from 'node:test'

const root = resolve(import.meta.dirname, '..')
const cases = [
  ['skills/coding/capture-vocab/SKILL.md', ['~/.claude/skills'], ['SKILL_DIR/scripts/vocab.py']],
  ['skills/writing/forge-doc/SKILL.md', ['~/.claude/skills', 'AskUserQuestion'], ['SKILL_DIR']],
  ['skills/mint/contribute-skill/SKILL.md', ['~/.claude/skills', '.claude/skills'], ['source_skill_dir', '~/.hskill/contribute-skill']],
  ['skills/coding/init-project/SKILL.md', ['user.claude.status', '--target claude', '~/.claude/skills'], ['TARGET', 'AGENTS.md']],
  ['skills/research/fetch-paper/SKILL.md', ['WebFetch', 'WebSearch'], ['下载能力', '临时文件']],
  ['skills/coding/init-goal/SKILL.md', ['/loop'], ['持续执行']],
]

test('shared portability entrypoints state portable behavior', async () => {
  for (const [file, forbidden, required] of cases) {
    const body = await readFile(resolve(root, file), 'utf8')
    for (const token of forbidden) assert.ok(!body.includes(token), `${file}: forbids ${token}`)
    for (const token of required) assert.ok(body.includes(token), `${file}: requires ${token}`)
  }
})
```

- [ ] **Step 2: Run the test and confirm the expected initial failure**

Run: `node --test tests/skill-portability.test.mjs`

Expected: FAIL because the current entrypoints contain at least one forbidden Claude-only assumption.

- [ ] **Step 3: Register the test with the deterministic Node suite**

Extend the Node invocation in `package.json` to include `tests/skill-portability.test.mjs` immediately after `tests/templates.test.mjs`.

- [ ] **Step 4: Run the registered test command**

Run: `node --test tests/mcp.test.mjs tests/templates.test.mjs tests/skill-portability.test.mjs tests/harness/*.test.mjs`

Expected: FAIL only in the new portability test before the remediation tasks complete.

### Task 2: Make local assets and contributor sync portable

**文件：**
- 修改: `skills/coding/capture-vocab/SKILL.md`
- 修改: `skills/coding/capture-vocab/references/manage.md`
- 修改: `skills/writing/forge-doc/SKILL.md`
- 修改: `skills/mint/contribute-skill/SKILL.md`
- 测试: `tests/skill-portability.test.mjs`

- [ ] **Step 1: Replace capture-vocab's installed-host path assumption**

Add a concise `SKILL_DIR` definition to `capture-vocab/SKILL.md`, change its lookup command to `python3 SKILL_DIR/scripts/vocab.py`, and make the write-operation reference use the same notation. Bump the entrypoint version from `1.2.1` to `1.2.2`.

- [ ] **Step 2: Run the capture-vocab runtime tests**

Run: `python3 -m pytest skills/coding/capture-vocab/tests/ -q`

Expected: PASS; the script continues to resolve the project vocabulary from its working directory.

- [ ] **Step 3: Replace forge-doc's path and prompt API assumptions**

Define `SKILL_DIR` once in `forge-doc/SKILL.md`. Rewrite every script, asset, and preview command to use that variable. Replace both mandatory `AskUserQuestion` references with “use the current host's question mechanism; otherwise ask in the conversation,” and make opening the preview optional. Bump `2.5.0` to `2.5.1`.

- [ ] **Step 4: Run the forge-doc unit tests**

Run: `python3 -m pytest skills/writing/forge-doc/tests/ -q`

Expected: PASS.

- [ ] **Step 5: Make contribute-skill preserve an explicit source directory**

Introduce `source_skill_dir` as the verified directory containing `SKILL.md`; search known host directories only as optional candidates, never as an assumed `.claude/skills` location. Move its cache to `~/.hskill/contribute-skill/.config` and replace every sync/status/copy/commit path with `source_skill_dir`. Bump `1.0.0` to `1.0.1`.

- [ ] **Step 6: Run the portability case after local-asset changes**

Run: `node --test --test-name-pattern='shared portability entrypoints' tests/skill-portability.test.mjs`

Expected: the three completed entries pass; remaining entries may still make the aggregate test fail until later tasks.

### Task 3: Make project initialization target-aware and generate neutral guidance

**文件：**
- 修改: `skills/coding/init-project/SKILL.md`
- 修改: `skills/coding/init-project/assets/templates/code.yml`
- 重命名并修改: `skills/coding/init-project/assets/skeleton/CLAUDE.md` to `skills/coding/init-project/assets/skeleton/AGENTS.md`
- 测试: `tests/skill-portability.test.mjs`

- [ ] **Step 1: Describe an explicit active installation target**

In `init-project/SKILL.md`, bind `TARGET` to the current host when known; otherwise ask the user to choose a supported hskill target. Change status inspection to `user.TARGET.status` then `project.TARGET.status`, and change installation to `hskill install ... --target TARGET`. Keep the project working directory rule unchanged. Bump `0.1.0` to `0.1.1`.

- [ ] **Step 2: Replace the generated Claude-only skeleton**

Change the template entry from `CLAUDE.md` to `AGENTS.md`. Rename the asset and rewrite its heading and prose for any agent host while preserving the project overview, commands, workflow, vocabulary, and task references.

- [ ] **Step 3: Run the portability guard for initialization**

Run: `node --test tests/skill-portability.test.mjs`

Expected: initialization no longer fails its target/path/skeleton assertions; research and goal cases may remain until Task 4.

- [ ] **Step 4: Verify the template registry remains valid**

Run: `node --test tests/templates.test.mjs`

Expected: PASS; every template-referenced skill remains registered.

### Task 4: Replace native research and continuous-run assumptions

**文件：**
- 修改: `skills/research/fetch-paper/SKILL.md`
- 修改: `skills/coding/init-goal/SKILL.md`
- 创建: `skills/coding/init-goal/platforms/SKILL.claude.md`
- 创建: `skills/coding/init-goal/platforms/SKILL.codex.md`
- 修改: `skills/research/clip-url/SKILL.md`
- 修改: `skills/research/clip-url/platforms/SKILL.codex.md`
- 测试: `tests/skill-portability.test.mjs`

- [ ] **Step 1: Make fetch-paper transport capability-based**

Replace named `WebSearch` and `WebFetch` calls with host-neutral search, structured-request, and binary-download capabilities. Require the downloader to return or create a temporary file; use `curl -L --fail --output` only when the host cannot save binary data. Preserve source priority, OA restrictions, manual/paid classifications, and `%PDF-`/MIME validation. Bump `0.2.0` to `0.2.1`.

- [ ] **Step 2: Make init-goal's shared flow independent of `/loop`**

Rename shared wording from “loop” to “持续执行”, keep `prompt.md`, `log.md`, and `summary.md` lifecycle rules for the executing agent, and give a host-neutral start instruction with manual continuation fallback. Move the `/loop` invocation to `platforms/SKILL.claude.md`; add a Codex adapter that does not claim an unavailable slash command. Bump `1.3.0` to `1.3.1`.

- [ ] **Step 3: Validate Codex delegation before documenting it**

Run one delegation request whose prompt explicitly forbids filesystem writes, network access, process execution, and user-visible actions, and requires the literal response `CODEX_DELEGATION_READY`. Record only the observed supported invocation behavior. If delegation cannot be used, do not invent syntax.

- [ ] **Step 4: Replace clip-url's unverified stop gate**

Update the shared `clip-url` entrypoint to require a host adapter with a sequential fallback. In `SKILL.codex.md`, replace “未验证/先询问是否继续/待补” with the verified delegation behavior from Step 3, or the explicit sequential fallback. Bump the root `clip-url` entrypoint from `0.9.2` to `0.9.3` so its content hash records the adapter contract change.

- [ ] **Step 5: Run the complete portability guard**

Run: `node --test tests/skill-portability.test.mjs`

Expected: PASS.

### Task 5: Synchronize packaging metadata and run scoped verification

**文件：**
- 修改: `skills-index.json`
- 测试: `tests/skill-portability.test.mjs`, `skills/coding/init-goal/tests/init-goal.bats`, `skills/research/clip-url/tests/`, repository test suites

- [ ] **Step 1: Update seven index records**

For `coding/capture-vocab`, `coding/init-project`, `mint/contribute-skill`, `writing/forge-doc`, `research/fetch-paper`, `coding/init-goal`, and `research/clip-url`, set `contentVersion` to the bumped frontmatter version. Compute each `contentHash` with:

```bash
sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' SKILL.md | shasum -a 256 | cut -c1-16
```

Add the missing `contentHash` and `contentVersion` fields for `coding/init-project`.

- [ ] **Step 2: Run skill-specific suites**

Run: `bats skills/coding/init-goal/tests/init-goal.bats && python3 -m pytest skills/research/clip-url/tests/ -q`

Expected: PASS.

- [ ] **Step 3: Exercise target-aware installation in a temporary HOME**

Run the hskill install and status commands with a temporary HOME for `capture-vocab` once with `--target claude` and once with `--target codex`, then parse `hskill status --json` to confirm both target records report installed. Remove only the freshly-created temporary directory after the assertions.

Expected: PASS without reading or altering the user's actual host configuration.

- [ ] **Step 4: Run deterministic repository verification**

Run: `bats tests/skills.bats && bash scripts/run-skill-tests.sh && node --test tests/mcp.test.mjs tests/templates.test.mjs tests/skill-portability.test.mjs tests/harness/*.test.mjs`

Expected: PASS.

- [ ] **Step 5: Run the full test command with real-Claude E2E isolated**

Run `npm test` with a PATH that deliberately does not expose the real `claude` executable, while preserving Node, Bats, Python, and required project tools.

Expected: PASS with the two opt-in real-Claude hook E2E cases explicitly skipped; report that isolation separately from deterministic test success.

- [ ] **Step 6: Inspect final scope and commit the completed unit**

Run: `git status --short && git diff --check && git diff --stat`

Expected: only the planned skill, test, manifest, design, and plan files differ with no whitespace errors. Commit with `fix(skills): remove high-priority host assumptions` after all verification succeeds.

## Review focus

- Shared files must express fallback behavior, not merely rename Claude-only tokens.
- Host-specific adapters must not make untested API claims.
- `init-project` must not rewrite existing projects' instructions.
- F8 metadata must match each changed entrypoint version and normalized content hash.
