# hskill MCP Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let any MCP-capable agent host call hskill's skill-manager operations (list/status/outdated/info/install/uninstall/hooks/update) as native tools, via a new `hskill mcp` subcommand.

**Architecture:** `hskill mcp` starts a stdio MCP server (`lib/mcp-server.js`). Each of its 8 tools shells out to `node bin/cli.js <same-subcommand> --json` and translates the CLI's existing `{...}` / `{error:true,message}` JSON contract into an MCP tool result — no hskill business logic is duplicated or imported directly.

**Tech Stack:** `@modelcontextprotocol/sdk` (McpServer, StdioServerTransport, InMemoryTransport, Client), `zod` for tool input schemas, Node's built-in `node:test` runner for the new JS-level tests (project has no existing JS test framework — bats covers the CLI, `node:test` is stdlib and needs no new devDependency).

Design doc: `docs/superpowers/specs/2026-08-12-hskill-mcp-wrapper-design.md`

## Global Constraints

- Node >= 18 (per `package.json` `engines`) — `node:test` and top-level `await` are both safe to use.
- New runtime dependencies: `@modelcontextprotocol/sdk@^1.30.0`, `zod@^4.0.0` — added to `package.json` `dependencies` (zod is a required, non-optional peer dependency of the SDK).
- ESM only — `package.json` has `"type": "module"`; every new file uses `import`/`export`.
- No behavior change to any existing CLI command's non-`--json` output or exit codes. Only additive `--json` branches are added to `uninstall` and `hooks uninstall`, which currently lack them.
- MCP tool names are exact: `hskill_list`, `hskill_status`, `hskill_outdated`, `hskill_info`, `hskill_install`, `hskill_uninstall`, `hskill_hooks`, `hskill_update`.
- `lib/mcp-server.js` never imports `lib/bundles.js`, `lib/installer.js`, or `lib/targets.js` directly — every tool handler goes through a subprocess call to `bin/cli.js`.
- The `mcp` subcommand branch in `bin/cli.js` must block forever after starting the server (via `await new Promise(() => {})`) so this flat, non-function-wrapped script never falls through into the generic install-arg-parsing code that runs unconditionally near the end of the file. This is a correctness requirement, not a style choice — without it, the process calls `process.exit(0)` moments after starting the MCP server and kills it.

---

## File Structure

- `bin/cli.js` — modify: patch `uninstall` (currently lines 476-521) and `hooks uninstall` (currently lines 634-644) to support `--json`; add a new `mcp` subcommand dispatch block.
- `lib/mcp-server.js` — new file. Exports `runCli(argv)` (spawn helper), `createServer()` (builds and returns a configured, unconnected `McpServer`), `startServer()` (connects `createServer()`'s result to a `StdioServerTransport`).
- `tests/mcp.test.mjs` — new file, uses `node:test` + `node:assert/strict` + the SDK's `InMemoryTransport`/`Client` to test `createServer()`'s tools in-process, plus one end-to-end test that spawns the real `hskill mcp` subcommand via `StdioClientTransport`.
- `package.json` — add the two new dependencies; extend the `test` script to also run `node --test tests/mcp.test.mjs`.
- `tests/agent-cli.bats` — add cases for `uninstall --json`.
- `tests/hooks.bats` — add cases for `hooks uninstall --json`.

---

### Task 1: `uninstall` command gains `--json` support

**Files:**
- Modify: `bin/cli.js:476-521` (the `if (subcommand === 'uninstall')` block)
- Test: `tests/agent-cli.bats`

**Interfaces:**
- Produces: `hskill uninstall <name> --json` now prints `{"removed":true|false,"failed":true|false}` to stdout on stdout and exits 0/1 exactly as the non-JSON path does today; on usage/unknown-name errors it prints `{"error":true,"message":"..."}` to stderr (same shape already used elsewhere in this file, e.g. the existing `--json` error branch inside the `upgrade` block).

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/agent-cli.bats`:

```bash
# ── uninstall --json ────────────────────────────────────────────────────────

@test "uninstall --json: unknown name emits JSON error on stderr" {
  local errfile="${TEST_DIR}/uninstall-unknown.txt"
  HOME="${MOCK_HOME}" node "${CLI}" uninstall does-not-exist --json \
    >/dev/null 2>"${errfile}" || true
  local err
  err="$(cat "${errfile}")"
  echo "$err" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$err" == *'"error":true'* ]]
  [[ "$err" == *'"message"'* ]]
}

@test "uninstall --json: missing name emits JSON error on stderr" {
  local errfile="${TEST_DIR}/uninstall-missing.txt"
  HOME="${MOCK_HOME}" node "${CLI}" uninstall --json \
    >/dev/null 2>"${errfile}" || true
  local err
  err="$(cat "${errfile}")"
  echo "$err" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$err" == *'"error":true'* ]]
}

@test "uninstall --json: removes installed skill and reports removed:true" {
  HOME="${MOCK_HOME}" node "${CLI}" install --skill survey-skillrepo --target claude --scope user --force >/dev/null 2>&1
  [ -d "${MOCK_HOME}/.claude/skills/survey-skillrepo" ]
  run bash -c "HOME='${MOCK_HOME}' node '${CLI}' uninstall survey-skillrepo --scope user --target claude --json"
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"removed":true'* ]]
  [ ! -d "${MOCK_HOME}/.claude/skills/survey-skillrepo" ]
}

@test "uninstall --json: skill not installed reports removed:false, exits 0" {
  run bash -c "HOME='${MOCK_HOME}' node '${CLI}' uninstall survey-skillrepo --scope user --target claude --json"
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"removed":false'* ]]
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/agent-cli.bats -f "uninstall --json"`
Expected: the two "unknown name" / "missing name" cases still pass (existing plain-text error path happens to satisfy neither assertion — confirm they FAIL because stderr isn't JSON), and the two skill-removal cases FAIL because stdout is currently empty (only `console.error` chalk text is printed, no JSON).

- [ ] **Step 3: Patch `bin/cli.js`**

Replace the block currently at `bin/cli.js:476-521`:

```javascript
if (subcommand === 'uninstall') {
  const nameToRemove = args[1]
  if (!nameToRemove || nameToRemove.startsWith('--')) {
    console.error(chalk.red('  ✗ Usage: hskill uninstall <tool-or-skill-name> [--yes] [--scope user|project] [--target claude|...]'))
    process.exit(1)
  }

  const yesFlag    = args.includes('--yes')
  const scopeIdx2  = args.indexOf('--scope')
  const targetIdx2 = args.indexOf('--target')
  const scopeArg2  = scopeIdx2  !== -1 ? args[scopeIdx2  + 1] : 'user'
  const targetArg2 = targetIdx2 !== -1 ? args[targetIdx2 + 1] : undefined

  const toolItems2  = getAllToolItems()
  const skillItems2 = getAllSkillItems()
  const isTool  = toolItems2.some(t => t.toolName  === nameToRemove)
  const isSkill = skillItems2.some(s => s.skillName === nameToRemove)

  if (!isTool && !isSkill) {
    console.error(chalk.red(`  ✗ Unknown tool or skill: "${nameToRemove}"`))
    process.exit(1)
  }

  if (isTool) {
    const { removed, failed } = await uninstallTool(nameToRemove, { yes: yesFlag })
    if (removed.length > 0) console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
    process.exit(failed.length ? 1 : 0)
  }

  // Skill uninstall
  const scope = scopeArg2
  const selectedTargets = targetArg2
    ? [targetArg2]
    : SKILL_TARGETS
  const targets = resolveTargets(selectedTargets, scope)

  let anyRemoved = false
  let anyFailed  = false
  for (const { dir } of targets) {
    const { removed, failed } = await uninstallSkill(nameToRemove, dir)
    if (removed.length) anyRemoved = true
    if (failed.length)  anyFailed  = true
  }
  if (anyRemoved) console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
  process.exit(anyFailed ? 1 : 0)
}
```

with:

```javascript
if (subcommand === 'uninstall') {
  const nameToRemove = args[1]
  if (!nameToRemove || nameToRemove.startsWith('--')) {
    const msg = 'Usage: hskill uninstall <tool-or-skill-name> [--yes] [--scope user|project] [--target claude|...]'
    if (jsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
    else console.error(chalk.red('  ✗ ' + msg))
    process.exit(1)
  }

  const yesFlag    = args.includes('--yes')
  const scopeIdx2  = args.indexOf('--scope')
  const targetIdx2 = args.indexOf('--target')
  const scopeArg2  = scopeIdx2  !== -1 ? args[scopeIdx2  + 1] : 'user'
  const targetArg2 = targetIdx2 !== -1 ? args[targetIdx2 + 1] : undefined

  const toolItems2  = getAllToolItems()
  const skillItems2 = getAllSkillItems()
  const isTool  = toolItems2.some(t => t.toolName  === nameToRemove)
  const isSkill = skillItems2.some(s => s.skillName === nameToRemove)

  if (!isTool && !isSkill) {
    const msg = `Unknown tool or skill: "${nameToRemove}"`
    if (jsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
    else console.error(chalk.red('  ✗ ' + msg))
    process.exit(1)
  }

  if (isTool) {
    const { removed, failed } = await uninstallTool(nameToRemove, { yes: yesFlag })
    if (jsonFlag) {
      console.log(JSON.stringify({ removed: removed.length > 0, failed: failed.length > 0 }, null, 2))
    } else if (removed.length > 0) {
      console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
    }
    process.exit(failed.length ? 1 : 0)
  }

  // Skill uninstall
  const scope = scopeArg2
  const selectedTargets = targetArg2
    ? [targetArg2]
    : SKILL_TARGETS
  const targets = resolveTargets(selectedTargets, scope)

  let anyRemoved = false
  let anyFailed  = false
  for (const { dir } of targets) {
    const { removed, failed } = await uninstallSkill(nameToRemove, dir)
    if (removed.length) anyRemoved = true
    if (failed.length)  anyFailed  = true
  }
  if (jsonFlag) {
    console.log(JSON.stringify({ removed: anyRemoved, failed: anyFailed }, null, 2))
  } else if (anyRemoved) {
    console.error(chalk.green.bold(`✔ ${nameToRemove} uninstalled`))
  }
  process.exit(anyFailed ? 1 : 0)
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/agent-cli.bats -f "uninstall --json"`
Expected: all 4 new tests PASS.

- [ ] **Step 5: Run the full existing suite to check for regressions**

Run: `bats tests/agent-cli.bats tests/install.bats`
Expected: PASS (the two pre-existing plain-text `uninstall` tests in `install.bats:206-216` don't pass `--json` and must still pass unchanged).

- [ ] **Step 6: Commit**

```bash
git add bin/cli.js tests/agent-cli.bats
git commit -m "feat(cli): add --json support to uninstall command"
```

---

### Task 2: `hooks uninstall` subcommand gains `--json` support

**Files:**
- Modify: `bin/cli.js:634-644` (the `if (hooksSubcmd === 'uninstall')` block, inside the `hooks` dispatch)
- Test: `tests/hooks.bats`

**Interfaces:**
- Produces: `hskill hooks uninstall <name> --json` prints `{"removed":true|false}` to stdout, exit 0; usage error prints `{"error":true,"message":"..."}` to stderr, exit 1. Uses the `hookJsonFlag` variable already computed earlier in the same `hooks` block (`bin/cli.js:527`).

- [ ] **Step 1: Write the failing tests**

Add to `tests/hooks.bats` near the existing `hooks uninstall` tests (after line 116, right after the two existing `hooks uninstall` tests):

```bash
@test "hooks uninstall --json: removed:true when hook was installed" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user >/dev/null 2>&1
  run bash -c "HOME='${MOCK_HOME}' node '${CLI}' hooks uninstall '${HOOK_NAME}' --scope user --json"
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"removed":true'* ]]
}

@test "hooks uninstall --json: removed:false when hook was not installed" {
  run bash -c "HOME='${MOCK_HOME}' node '${CLI}' hooks uninstall '${HOOK_NAME}' --scope user --json"
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"removed":false'* ]]
}

@test "hooks uninstall --json: missing name emits JSON error on stderr" {
  local errfile="${TEST_DIR}/hooks-uninstall-missing.txt"
  HOME="${MOCK_HOME}" node "${CLI}" hooks uninstall --json \
    >/dev/null 2>"${errfile}" || true
  local err
  err="$(cat "${errfile}")"
  echo "$err" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$err" == *'"error":true'* ]]
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bats tests/hooks.bats -f "hooks uninstall --json"`
Expected: all 3 FAIL (stdout is currently empty or plain text, not JSON).

- [ ] **Step 3: Patch `bin/cli.js`**

Replace the block currently at `bin/cli.js:634-644`:

```javascript
  // ── hooks uninstall ──────────────────────────────────────────────────────────
  if (hooksSubcmd === 'uninstall') {
    const nameToRemove = args[2]
    if (!nameToRemove || nameToRemove.startsWith('--')) {
      console.error(chalk.red('  ✗ Usage: hskill hooks uninstall <name> [--scope user|project]'))
      process.exit(1)
    }
    const { removed } = await uninstallHook(nameToRemove, hookScopeArg, hookProjectArg)
    if (!removed) console.log(chalk.dim(`  · ${nameToRemove} was not installed in ${hookScopeArg} scope`))
    process.exit(0)
  }
```

with:

```javascript
  // ── hooks uninstall ──────────────────────────────────────────────────────────
  if (hooksSubcmd === 'uninstall') {
    const nameToRemove = args[2]
    if (!nameToRemove || nameToRemove.startsWith('--')) {
      const msg = 'Usage: hskill hooks uninstall <name> [--scope user|project]'
      if (hookJsonFlag) process.stderr.write(JSON.stringify({ error: true, message: msg }) + '\n')
      else console.error(chalk.red('  ✗ ' + msg))
      process.exit(1)
    }
    const { removed } = await uninstallHook(nameToRemove, hookScopeArg, hookProjectArg)
    if (hookJsonFlag) {
      console.log(JSON.stringify({ removed }, null, 2))
    } else if (!removed) {
      console.log(chalk.dim(`  · ${nameToRemove} was not installed in ${hookScopeArg} scope`))
    }
    process.exit(0)
  }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bats tests/hooks.bats -f "hooks uninstall"`
Expected: all pass, including the 2 pre-existing non-JSON `hooks uninstall` tests (`hooks.bats:99-116`).

- [ ] **Step 5: Run the full hooks suite to check for regressions**

Run: `bats tests/hooks.bats`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/cli.js tests/hooks.bats
git commit -m "feat(cli): add --json support to hooks uninstall subcommand"
```

---

### Task 3: Add MCP SDK dependencies

**Files:**
- Modify: `package.json`

**Interfaces:**
- Produces: `@modelcontextprotocol/sdk` and `zod` importable from any file in the repo.

- [ ] **Step 1: Install the dependencies**

Run: `npm install @modelcontextprotocol/sdk@^1.30.0 zod@^4.0.0`

This updates `package.json` `dependencies` and `package-lock.json`.

- [ ] **Step 2: Verify the install**

Run: `node -e "import('@modelcontextprotocol/sdk/server/mcp.js').then(m => console.log(typeof m.McpServer))"`
Expected: prints `function`

Run: `node -e "import('zod').then(m => console.log(typeof m.z.string))"`
Expected: prints `function`

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "chore: add @modelcontextprotocol/sdk and zod dependencies"
```

---

### Task 4: `lib/mcp-server.js` skeleton — `runCli`, `createServer`, `startServer`, first tool (`hskill_list`)

**Files:**
- Create: `lib/mcp-server.js`
- Create: `tests/mcp.test.mjs`

**Interfaces:**
- Produces:
  - `runCli(argv: string[]): Promise<{code: number, stdout: string, stderr: string}>` — spawns `node bin/cli.js <argv>`.
  - `createServer(): McpServer` — builds and returns an `McpServer` with tools registered, NOT yet connected to any transport.
  - `startServer(): Promise<void>` — calls `createServer()`, connects it to a `StdioServerTransport`, resolves once connected (the process is then kept alive by open stdio, not by this promise).
- Consumes: nothing from other tasks (this task is self-contained; later tasks add more tools to the same `createServer()`).

- [ ] **Step 1: Write the failing test**

Create `tests/mcp.test.mjs`:

```javascript
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js'
import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { createServer } from '../lib/mcp-server.js'

async function connectedClient() {
  const server = createServer()
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair()
  const client = new Client({ name: 'test-client', version: '1.0.0' })
  await Promise.all([
    client.connect(clientTransport),
    server.connect(serverTransport),
  ])
  return { client, server }
}

test('hskill_list is registered and returns the real skill list as JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const { tools } = await client.listTools()
    const names = tools.map(t => t.name)
    assert.ok(names.includes('hskill_list'), `expected hskill_list in ${names.join(', ')}`)

    const result = await client.callTool({ name: 'hskill_list', arguments: {} })
    assert.equal(result.isError, undefined)
    const text = result.content[0].text
    const parsed = JSON.parse(text)
    assert.ok(parsed.skills, 'expected a "skills" key in hskill_list output')
  } finally {
    await client.close()
    await server.close()
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/mcp.test.mjs`
Expected: FAIL — `lib/mcp-server.js` does not exist (`Cannot find module`).

- [ ] **Step 3: Write `lib/mcp-server.js`**

```javascript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const CLI_PATH = path.join(__dirname, '..', 'bin', 'cli.js')

// Spawns `node bin/cli.js <argv>` and collects its full stdout/stderr/exit code.
// Never rejects — callers branch on `code`.
export function runCli(argv) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [CLI_PATH, ...argv], { stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d) => { stdout += d })
    child.stderr.on('data', (d) => { stderr += d })
    child.on('close', (code) => resolve({ code, stdout, stderr }))
  })
}

// Turns a runCli() result into an MCP CallToolResult. On success, the CLI's
// stdout JSON is forwarded as-is. On failure, stderr is parsed as the CLI's
// existing {error:true,message} shape; if that parse fails, the raw stderr
// text is used so a handler never throws on an unexpected crash.
export function toToolResult({ code, stdout, stderr }) {
  if (code === 0) {
    return { content: [{ type: 'text', text: stdout.trim() || '{}' }] }
  }
  let message = stderr.trim() || `hskill exited with code ${code}`
  const lastLine = stderr.trim().split('\n').pop()
  try {
    const parsed = JSON.parse(lastLine)
    if (parsed && parsed.error) message = parsed.message
  } catch {
    // stderr wasn't JSON — fall back to the raw text already assigned above
  }
  return { content: [{ type: 'text', text: message }], isError: true }
}

export function createServer() {
  const server = new McpServer({ name: 'hskill', version: '1.0.0' })

  server.registerTool('hskill_list', {
    description: 'List all available hskill skills and bundles, with per-target install status.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['list', '--json'])))

  return server
}

export async function startServer() {
  const server = createServer()
  const transport = new StdioServerTransport()
  await server.connect(transport)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add MCP server skeleton with hskill_list tool"
```

---

### Task 5: Add `hskill_status`, `hskill_outdated`, `hskill_info` tools

**Files:**
- Modify: `lib/mcp-server.js` (inside `createServer()`, after the `hskill_list` registration)
- Modify: `tests/mcp.test.mjs`

**Interfaces:**
- Consumes: `runCli`, `toToolResult` from Task 4 (same file, already defined above `createServer()`).
- Produces: 3 more registered tools, no new exports.

- [ ] **Step 1: Write the failing tests**

Add to `tests/mcp.test.mjs`, after the `hskill_list` test:

```javascript
test('hskill_status returns valid JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_status', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_outdated returns valid JSON', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_outdated', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_info returns detail for a known skill', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_info', arguments: { name: 'survey-skillrepo' } })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.equal(parsed.skill, 'survey-skillrepo')
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_info reports an MCP error for an unknown name', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_info', arguments: { name: 'does-not-exist' } })
    assert.equal(result.isError, true)
  } finally {
    await client.close()
    await server.close()
  }
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/mcp.test.mjs`
Expected: the 4 new tests FAIL with "Unknown tool" (`hskill_status`/`hskill_outdated`/`hskill_info` aren't registered yet).

- [ ] **Step 3: Add the tools to `lib/mcp-server.js`**

In `createServer()`, immediately after the `hskill_list` registration, add:

```javascript
  server.registerTool('hskill_status', {
    description: 'Show install status for all skills, tools, and hooks across every target.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['status', '--json'])))

  server.registerTool('hskill_outdated', {
    description: 'List only the skills and tools that have an available update.',
    inputSchema: {},
  }, async () => toToolResult(await runCli(['outdated', '--json'])))

  server.registerTool('hskill_info', {
    description: 'Show install detail for one named skill or tool, as returned by hskill_list.',
    inputSchema: {
      name: z.string().describe('Skill or tool name, exactly as shown by hskill_list'),
    },
  }, async ({ name }) => toToolResult(await runCli(['info', name, '--json'])))
```

Add the zod import at the top of `lib/mcp-server.js`, alongside the existing imports:

```javascript
import { z } from 'zod'
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add hskill_status, hskill_outdated, hskill_info tools"
```

---

### Task 6: Add `hskill_install` tool

**Files:**
- Modify: `lib/mcp-server.js`
- Modify: `tests/mcp.test.mjs`

**Interfaces:**
- Consumes: `runCli`, `toToolResult`, `z` from earlier tasks (same file).
- Produces: `hskill_install` tool, argv-building logic contained entirely inside its handler (not exported — no other task needs it).

- [ ] **Step 1: Write the failing test**

Add to `tests/mcp.test.mjs`. This test needs an isolated `HOME` so it doesn't write into the real `~/.claude/skills` — set `process.env.HOME` to a temp dir for the duration of the test, matching the isolation pattern the bats tests use with `MOCK_HOME`:

```javascript
import { mkdtempSync, rmSync, existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

test('hskill_install writes the skill to a mocked HOME', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({
      name: 'hskill_install',
      arguments: { skill: 'survey-skillrepo', target: 'claude', scope: 'user', force: true },
    })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.ok(parsed.skills, 'expected a "skills" key in hskill_install output')
    assert.ok(existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo', 'SKILL.md')))
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/mcp.test.mjs`
Expected: FAILS with "Unknown tool".

Note: `runCli()` spawns a child process, and Node child processes inherit the parent's `process.env` at spawn time by default — setting `process.env.HOME` before calling `client.callTool` is enough for the spawned `node bin/cli.js` subprocess to see the mocked `HOME`.

- [ ] **Step 3: Add the tool to `lib/mcp-server.js`**

```javascript
  server.registerTool('hskill_install', {
    description: 'Install a skill bundle, a specific skill, or a shell tool. Writes files under ~/.claude/skills (or the equivalent dir for --target) or a project directory. Provide exactly one of bundle, skill, or tool.',
    inputSchema: {
      bundle: z.string().optional().describe('Bundle name(s) to install, comma-separated'),
      skill: z.string().optional().describe('Specific skill name(s) to install, comma-separated'),
      tool: z.string().optional().describe('Specific shell tool name(s) to install, comma-separated'),
      target: z.string().optional().describe('Target host: claude, cursor, codex, opencode, etc., or "all"'),
      scope: z.enum(['user', 'project']).optional().describe('Install scope, defaults to user'),
      force: z.boolean().optional().describe('Overwrite an existing install'),
    },
  }, async ({ bundle, skill, tool, target, scope, force }) => {
    const argv = ['install']
    if (bundle) argv.push('--bundle', bundle)
    if (skill) argv.push('--skill', skill)
    if (tool) argv.push('--tool', tool)
    if (target) argv.push('--target', target)
    if (scope) argv.push('--scope', scope)
    if (force) argv.push('--force')
    argv.push('--json')
    return toToolResult(await runCli(argv))
  })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add hskill_install tool"
```

---

### Task 7: Add `hskill_uninstall` tool

**Files:**
- Modify: `lib/mcp-server.js`
- Modify: `tests/mcp.test.mjs`

**Interfaces:**
- Consumes: `runCli`, `toToolResult`, `z`; relies on Task 1's `uninstall --json` support in `bin/cli.js`.
- Produces: `hskill_uninstall` tool.

- [ ] **Step 1: Write the failing test**

Add to `tests/mcp.test.mjs`:

```javascript
test('hskill_uninstall removes a previously installed skill', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    await client.callTool({
      name: 'hskill_install',
      arguments: { skill: 'survey-skillrepo', target: 'claude', scope: 'user', force: true },
    })
    assert.ok(existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo')))

    const result = await client.callTool({
      name: 'hskill_uninstall',
      arguments: { name: 'survey-skillrepo', scope: 'user', target: 'claude' },
    })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.equal(parsed.removed, true)
    assert.ok(!existsSync(path.join(mockHome, '.claude', 'skills', 'survey-skillrepo')))
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/mcp.test.mjs`
Expected: FAILS with "Unknown tool".

- [ ] **Step 3: Add the tool to `lib/mcp-server.js`**

```javascript
  server.registerTool('hskill_uninstall', {
    description: 'Uninstall a named skill or shell tool, removing its files from disk.',
    inputSchema: {
      name: z.string().describe('Skill or tool name to uninstall, as shown by hskill_list'),
      scope: z.enum(['user', 'project']).optional().describe('Scope to uninstall from, defaults to user'),
      target: z.string().optional().describe('Target host to uninstall from'),
      yes: z.boolean().optional().describe('Skip confirmation prompts'),
    },
  }, async ({ name, scope, target, yes }) => {
    const argv = ['uninstall', name]
    if (scope) argv.push('--scope', scope)
    if (target) argv.push('--target', target)
    if (yes) argv.push('--yes')
    argv.push('--json')
    return toToolResult(await runCli(argv))
  })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add hskill_uninstall tool"
```

---

### Task 8: Add `hskill_hooks` tool (list / install / uninstall)

**Files:**
- Modify: `lib/mcp-server.js`
- Modify: `tests/mcp.test.mjs`

**Interfaces:**
- Consumes: `runCli`, `toToolResult`, `z`; relies on Task 2's `hooks uninstall --json` support.
- Produces: `hskill_hooks` tool with an `action` enum.

- [ ] **Step 1: Write the failing tests**

Add to `tests/mcp.test.mjs`:

```javascript
test('hskill_hooks list returns valid JSON with a hooks array', async () => {
  const { client, server } = await connectedClient()
  try {
    const result = await client.callTool({ name: 'hskill_hooks', arguments: { action: 'list' } })
    assert.equal(result.isError, undefined)
    const parsed = JSON.parse(result.content[0].text)
    assert.ok(Array.isArray(parsed.hooks))
  } finally {
    await client.close()
    await server.close()
  }
})

test('hskill_hooks install then uninstall round-trips in a mocked HOME', async () => {
  const mockHome = mkdtempSync(path.join(tmpdir(), 'hskill-mcp-test-'))
  const originalHome = process.env.HOME
  process.env.HOME = mockHome
  const { client, server } = await connectedClient()
  try {
    const installResult = await client.callTool({
      name: 'hskill_hooks',
      arguments: { action: 'install', name: 'check-similar-branch', scope: 'user' },
    })
    assert.equal(installResult.isError, undefined)
    const installed = JSON.parse(installResult.content[0].text)
    assert.ok(installed.installed.includes('check-similar-branch'))

    const uninstallResult = await client.callTool({
      name: 'hskill_hooks',
      arguments: { action: 'uninstall', name: 'check-similar-branch', scope: 'user' },
    })
    assert.equal(uninstallResult.isError, undefined)
    const uninstalled = JSON.parse(uninstallResult.content[0].text)
    assert.equal(uninstalled.removed, true)
  } finally {
    await client.close()
    await server.close()
    process.env.HOME = originalHome
    rmSync(mockHome, { recursive: true, force: true })
  }
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/mcp.test.mjs`
Expected: both FAIL with "Unknown tool".

- [ ] **Step 3: Add the tool to `lib/mcp-server.js`**

```javascript
  server.registerTool('hskill_hooks', {
    description: 'List, install, or uninstall hskill git hooks. Install/uninstall write files under ~/.claude/hooks (or the project dir for --scope project) and register them in settings.json.',
    inputSchema: {
      action: z.enum(['list', 'install', 'uninstall']),
      name: z.string().optional().describe('Hook name — required for install/uninstall'),
      scope: z.enum(['user', 'project']).optional().describe('Scope, defaults to user'),
      project: z.string().optional().describe('Project directory, used when scope is project'),
      force: z.boolean().optional().describe('Overwrite an existing hook install'),
    },
  }, async ({ action, name, scope, project, force }) => {
    const argv = ['hooks', action]
    if (name) argv.push('--name', name)
    if (scope) argv.push('--scope', scope)
    if (project) argv.push('--project', project)
    if (force) argv.push('--force')
    argv.push('--json')
    return toToolResult(await runCli(argv))
  })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add hskill_hooks tool"
```

---

### Task 9: Add `hskill_update` tool

**Files:**
- Modify: `lib/mcp-server.js`
- Modify: `tests/mcp.test.mjs`

**Interfaces:**
- Consumes: `runCli`; does NOT use `toToolResult` (the underlying `hskill update` command has no `--json` output — see design doc's Tool surface section).
- Produces: `hskill_update` tool.

This is the one tool whose test must NOT call it — `hskill update` runs a real `npm install -g harveyz-skill@latest` against the environment's actual global npm prefix. The test only verifies the tool is registered with the right name/description; it does not call it.

- [ ] **Step 1: Write the failing test**

Add to `tests/mcp.test.mjs`:

```javascript
test('hskill_update is registered with a description warning about irreversibility', async () => {
  const { client, server } = await connectedClient()
  try {
    const { tools } = await client.listTools()
    const updateTool = tools.find(t => t.name === 'hskill_update')
    assert.ok(updateTool, 'expected hskill_update to be registered')
    assert.match(updateTool.description, /irreversible/i)
    // Deliberately not calling this tool: it runs a real `npm install -g`
    // against the environment's actual global npm prefix.
  } finally {
    await client.close()
    await server.close()
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/mcp.test.mjs`
Expected: FAILS — `hskill_update` not found in `tools`.

- [ ] **Step 3: Add the tool to `lib/mcp-server.js`**

```javascript
  server.registerTool('hskill_update', {
    description: 'Update hskill itself to the latest version via `npm install -g harveyz-skill@latest`. This replaces the globally installed hskill binary and is irreversible except by manually reinstalling a specific version.',
    inputSchema: {},
  }, async () => {
    const { code, stdout, stderr } = await runCli(['update'])
    if (code === 0) {
      return { content: [{ type: 'text', text: 'hskill updated to the latest version.' }] }
    }
    const message = stderr.trim() || stdout.trim() || `update failed with exit code ${code}`
    return { content: [{ type: 'text', text: message }], isError: true }
  })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/mcp-server.js tests/mcp.test.mjs
git commit -m "feat(mcp): add hskill_update tool"
```

---

### Task 10: Wire the `hskill mcp` subcommand into `bin/cli.js`

**Files:**
- Modify: `bin/cli.js` (insert a new dispatch block between the existing `update` block, which ends at line 190, and the `list` block, which starts at line 193)
- Modify: `tests/mcp.test.mjs`
- Modify: `package.json` (`test` script)

**Interfaces:**
- Consumes: `startServer` from `lib/mcp-server.js` (Task 4).
- Produces: `hskill mcp` as a real, spawnable CLI subcommand.

This is the task that proves the "block forever, never fall through" requirement from Global Constraints actually holds — the test spawns the real subcommand as a subprocess and must be able to complete an MCP handshake and a tool call before explicitly killing it (the server never exits on its own).

- [ ] **Step 1: Write the failing test**

Add to `tests/mcp.test.mjs`:

```javascript
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'

test('hskill mcp subcommand: spawns a real MCP server over stdio and serves hskill_list', async () => {
  const cliPath = new URL('../bin/cli.js', import.meta.url).pathname
  const transport = new StdioClientTransport({ command: process.execPath, args: [cliPath, 'mcp'] })
  const client = new Client({ name: 'test-client', version: '1.0.0' })
  await client.connect(transport)
  try {
    const { tools } = await client.listTools()
    assert.ok(tools.some(t => t.name === 'hskill_list'))
    const result = await client.callTool({ name: 'hskill_list', arguments: {} })
    assert.equal(result.isError, undefined)
    JSON.parse(result.content[0].text)
  } finally {
    await client.close()
  }
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/mcp.test.mjs`
Expected: FAILS or hangs/times out — `mcp` isn't a recognized subcommand yet, so `node bin/cli.js mcp` falls through to the generic install-arg parser, which (with no `--skill`/`--bundle`/`--tool` flags and no TTY) prints "Nothing selected, exiting" and calls `process.exit(0)` — the client's `connect()` never completes its handshake. If `node --test` hangs instead of failing cleanly, interrupt it and confirm by running `node bin/cli.js mcp` directly in a terminal — it should print "Nothing selected, exiting" and exit immediately, proving the fallthrough.

- [ ] **Step 3: Add the `mcp` dispatch block to `bin/cli.js`**

Insert between the end of the `update` block (`bin/cli.js:190`) and the `// ── List` comment (`bin/cli.js:192`):

```javascript
// ── MCP server ───────────────────────────────────────────────────────────────
if (subcommand === 'mcp') {
  const { startServer } = await import('../lib/mcp-server.js')
  await startServer()
  // StdioServerTransport keeps stdin/stdout open for JSON-RPC. bin/cli.js is a
  // flat top-level script with no early-return mechanism (this is a real ES
  // module, so a bare top-level `return` is a syntax error) — every other
  // subcommand block ends itself with process.exit(), which we can't do here
  // without killing the server we just started. Blocking on a promise that
  // never resolves is what stops execution from falling through into the
  // generic install-arg parsing near the end of this file.
  await new Promise(() => {})
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/mcp.test.mjs`
Expected: PASS.

- [ ] **Step 5: Run the full test suite**

Run: `npm test` (bats suites) and `node --test tests/mcp.test.mjs`
Expected: all PASS, no regressions in the existing 4 bats files.

- [ ] **Step 6: Wire `node --test` into the `test` script**

In `package.json`, change:

```json
    "test": "bats tests/ && bash scripts/run-skill-tests.sh"
```

to:

```json
    "test": "bats tests/ && bash scripts/run-skill-tests.sh && node --test tests/mcp.test.mjs"
```

- [ ] **Step 7: Run `npm test` end to end**

Run: `npm test`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add bin/cli.js tests/mcp.test.mjs package.json
git commit -m "feat(cli): add hskill mcp subcommand, wire mcp tests into npm test"
```

---

## Manual Verification (after Task 10)

Not automated — run once by hand to confirm the subcommand is usable as a real MCP server config entry, not just under the SDK's test client:

```bash
node bin/cli.js mcp
```

Expected: the process starts and hangs (no output, no exit) — this is correct; it's waiting for a JSON-RPC client on stdin. Press Ctrl-C to stop it. This confirms the binary is ready to be pointed at from an MCP host's config as `{"command": "hskill", "args": ["mcp"]}` (once published) or `{"command": "node", "args": ["<repo>/bin/cli.js", "mcp"]}` (local dev).
