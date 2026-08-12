# hskill MCP wrapper — design

## Problem

`hskill` is a skill/tool manager: install, list, status, outdated, info, uninstall,
hooks (list/install/uninstall), update. Today it's only usable as a human-run CLI
(`hskill ...`), even though `bin/cli.js` already has an agent-friendly `--json` mode
(non-TTY safe, structured `{error:true,message}` errors — tested in
`tests/agent-cli.bats`).

We want an AI agent to call hskill's operations natively during a session (list
available skills, check what's installed/outdated, install/uninstall a skill, manage
hooks, self-update) instead of the human running `hskill` by hand.

## Decision: CLI stays the source of truth, MCP wraps it

hskill's install target list — Claude Code, Cursor, Codex, OpenClaw, Hermes,
OpenCode, Pi — includes hosts that don't (or may not) speak MCP. The CLI must keep
working standalone for all of them. MCP is an additional, optional interface layered
on top for hosts that do speak it (Claude Code and other MCP-capable hosts) — it is
not a replacement for the CLI.

The MCP server does not reimplement or directly import hskill's business logic
(`lib/bundles.js`, `lib/installer.js`, `lib/targets.js`). Each MCP tool handler shells
out to `node bin/cli.js <args> --json` and parses the result. This means the MCP layer
is a pure protocol translator sitting on top of the exact same `--json` contract
that's already tested in `tests/agent-cli.bats`, and any future CLI-internal
refactor can't silently break the MCP layer as long as the `--json` contract holds.

Alternative considered and rejected: importing `lib/*` functions directly in-process
(avoids subprocess overhead, returns JS objects instead of round-tripping through
JSON). Rejected because it would create a second, untested code path for the same
operations and couples the MCP layer to internal function signatures instead of the
stable CLI contract. Subprocess spawn overhead (tens of ms) is not a real constraint
for this use case.

## Architecture

```
MCP client (agent host)
   │  tool call (JSON-RPC over stdio)
   ▼
hskill mcp                          (new subcommand, bin/cli.js)
   │  starts stdio server via lib/mcp-server.js
   ▼
lib/mcp-server.js
   │  tool handler: build argv → spawn('node', [cliPath, ...argv, '--json'])
   ▼
node bin/cli.js <existing subcommand> --json
   │  stdout: JSON result (exit 0)  |  stderr: {error:true,message} (exit != 0)
   ▼
lib/mcp-server.js
   │  exit 0  → JSON.parse(stdout) as tool result
   │  exit !=0 → parse stderr error JSON → MCP isError:true result
   ▼
MCP client
```

## Components

- **`lib/mcp-server.js`** (new) — tool definitions + one handler function per tool.
  Each handler: build argv from validated params → spawn CLI subprocess → parse
  result → return MCP content.
- **`bin/cli.js`** — add `if (subcommand === 'mcp') { ... }` dispatch that loads
  `lib/mcp-server.js` and starts the stdio server. A few lines of glue; no existing
  dispatch branch changes.
- **`bin/cli.js`** — two small additive patches:
  - `uninstall` command gains a `--json` branch (currently only prints chalk text).
  - `hooks uninstall` subcommand gains a `--json` branch (same gap).
  Both reuse the exact `{error:true,message}` / result-object shape already used
  elsewhere in the file (e.g. lines currently around 664, 1055, 1409, and the
  existing `hooks install --json` branch as the template for a success shape).
- **`package.json`** — add `@modelcontextprotocol/sdk` as a dependency.

## Tool surface

One MCP tool per CLI operation, parameters mirroring existing CLI flags 1:1. Hooks'
three sub-operations are consolidated into a single tool with an `action` enum to
keep the tool count an agent has to choose from smaller.

| MCP tool | Params | CLI equivalent |
|---|---|---|
| `hskill_list` | — | `hskill list --json` |
| `hskill_status` | — | `hskill status --json` |
| `hskill_outdated` | — | `hskill outdated --json` |
| `hskill_info` | `{name}` | `hskill info <name> --json` |
| `hskill_install` | `{bundle?, skill?, tool?, target?, scope?, force?}` | `hskill install ... --json` |
| `hskill_uninstall` | `{name, scope?, target?, yes?}` | `hskill uninstall <name> ... --json` |
| `hskill_hooks` | `{action: list\|install\|uninstall, name?, scope?, project?, force?}` | `hskill hooks <action> ... --json` |
| `hskill_update` | — | `hskill update` |

`hskill_update` has no `--json` output today (`update` shells out to
`npm install -g harveyz-skill@latest` with `stdio: 'inherit'`) and is out of scope to
change — the handler just runs it and reports exit code/success, no structured
result parsing.

## Data flow

1. MCP client calls a tool with validated JSON args.
2. Handler maps args → CLI argv (e.g. `['install', '--skill', 'x', '--target', 'y', '--json']`).
3. Handler spawns `node bin/cli.js <argv>`, captures stdout, stderr, exit code.
4. Exit 0 → `JSON.parse(stdout)` → returned as the MCP tool result content.
5. Exit != 0 → stderr parsed as `{error:true,message}` → returned as an MCP
   `isError:true` result with that message.
6. If stderr isn't valid JSON (unexpected crash) → the raw stderr text is wrapped
   into the MCP error result rather than letting the handler throw.

## Error handling

No new error format. The seven `--json`-backed handlers (all tools except
`hskill_update`) reuse the `{error:true,message}` stderr contract that already
exists in `bin/cli.js`. The two commands missing `--json` today (`uninstall`,
`hooks uninstall`) get patched to emit the same shape on both success and failure,
so those seven tools behave uniformly from the MCP layer's point of view.
`hskill_update` has no structured output (see Tool surface) — its handler reports
plain success/failure from the subprocess exit code, not a parsed JSON error.

## Testing

The four existing bats files test the CLI's own behavior (`agent-cli.bats`,
`install.bats`, `interactive.bats`, `hooks.bats`) — `hskill mcp` speaks JSON-RPC over
stdio, not a plain CLI invocation, so it doesn't fit their decision tree and isn't
added to any of them. A new test file (proposed: `tests/mcp.test.mjs`) spawns the MCP
server via `@modelcontextprotocol/sdk`'s client, calls each of the 8 tools, and
asserts the returned content shape and the error-translation path. Exact assertions
are left to the implementation plan.

## Safety model

No custom confirmation/approval layer is built for mutating tools (`hskill_install`,
`hskill_uninstall`, `hskill_hooks` with install/uninstall actions, `hskill_update`).
MCP-capable hosts already gate tool invocation through their own permission UI, the
same way they gate a Bash call — that's the existing safety net and this design
doesn't duplicate it. Each tool's `description` field must state its side effects
plainly (writes to `~/.claude/skills` or a project's skill dir, uninstalls files,
`hskill_update` replaces the globally-installed `hskill` binary and is irreversible
without manually reinstalling a specific version) so the host's permission prompt is
informative. `hskill_update` is called out as the highest-risk tool in this set.

## Out of scope

- Changing hskill's interactive (fzf) install flow.
- Any host-specific behavior (e.g. assuming Claude Code's worktree/permission
  features) — the server must work the same for any MCP-capable host.
- Publishing the MCP server as a separate npm package/binary — it ships as the
  `hskill mcp` subcommand of the existing `harveyz-skill` package.
