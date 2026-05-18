# hskill Testing Guide

Reference for AI agents writing or modifying tests in this repository.

---

## Overview

Tests use [bats-core](https://bats-core.readthedocs.io/) and live under `tests/`.
Run them all with:

```bash
npm test
```

There are three test files and one shared helper:

| File | What it tests |
|---|---|
| `tests/agent-cli.bats` | CLI output shape: `--json` validity, error codes, mutual-exclusion flags |
| `tests/install.bats` | Flag-based install (`--skill`, `--bundle`, `--tool`, `--scope`, `--target`) — verifies file-system state |
| `tests/interactive.bats` | Interactive fzf loop — verifies loop-back behavior, multi-select, cancellation |
| `tests/helpers/mock-fzf.sh` | Stateful fzf mock used by `interactive.bats` |

**Rule:** when in doubt about which file to add a test to, use this decision tree:

```
Does the test exercise the interactive fzf flow?
  yes → interactive.bats
  no  → Does it verify files on disk after install?
          yes → install.bats
          no  → Does it check CLI output shape / exit codes?
                  yes → agent-cli.bats
```

---

## install.bats — flag-based install tests

### Helpers

```bash
_install <flags...>         # runs `hskill install <flags>` non-interactively, stdout only
_stderr                     # reads stderr from the last _install call
_skill_version <SKILL.md>   # extracts version string, strips surrounding quotes
```

### Environment

Each test gets a fresh `MOCK_HOME` (`$TEST_DIR/home`) with these dirs pre-created:

```
~/.claude/skills/
~/.cursor/skills/
~/.local/bin/
~/.local/share/hskill/tools/
```

`HOME` is set to `MOCK_HOME` for every `_install` call; the real home is never touched.

### Writing a new install test

```bash
@test "install --skill: <description>" {
  _install --skill skill-analyzer --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/skill-analyzer/SKILL.md" ]
}
```

Key points:
- Always pass `--target` and `--scope` to avoid fzf pickers that block in non-TTY.
- Pass `--force` when you want a clean install regardless of existing state.
- Version comparison: use `_skill_version`, not raw `grep`. SKILL.md stores versions
  as `version: "1.0.0"` (quoted); `_skill_version` strips the quotes.

```bash
[ "$(_skill_version "${MOCK_HOME}/.claude/skills/skill-analyzer/SKILL.md")" = "1.0.0" ]
```

- Skip messages go to **stderr** (installer.js uses `console.error`). Capture with:

```bash
HOME="${MOCK_HOME}" node "${CLI}" install --skill foo --target claude --scope user \
  2>/tmp/bats-install-stderr >/dev/null | cat
err="$(_stderr)"
[[ "$err" == *"skipped"* ]]
```

- Project-scope installs use `process.cwd()` as the base. Run from a temp dir:

```bash
local project_dir="${TEST_DIR}/proj"
mkdir -p "${project_dir}"
(cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
  --skill skill-analyzer --target claude --scope project --force 2>/dev/null | cat)
[ -f "${project_dir}/.claude/skills/skill-analyzer/SKILL.md" ]
```

---

## interactive.bats — fzf loop tests

### How the mock works

`hskill` calls `spawnSync('fzf', ...)` for every prompt. In tests:

1. `HSKILL_TEST_INTERACTIVE=1` bypasses the `process.stdout.isTTY` guard in `cli.js`.
2. A mock `fzf` binary (`tests/helpers/mock-fzf.sh`) is prepended to `PATH`.
3. The mock reads responses from `HSKILL_FZF_RESPONSES_FILE` — one response per line,
   consumed in order by call count tracked in `HSKILL_FZF_COUNTER_FILE`.
4. `--version` probes (`requireFzf`) are intercepted and **do not consume a slot**.

### fzf call ordering

**Skill-only selection (one install round):**

| Slot | Prompt | Response format |
|---|---|---|
| 1 | skill selector | `_skill_line NAME VER BUNDLE SRC` |
| 2 | scope selector | `"user"` or `"project"` |
| 3 | target selector | `"claude"` (first word = target) |
| N | loop-back skill selector | `""` (empty = Esc → exit) |

**Tool-only selection:**

| Slot | Prompt | Response format |
|---|---|---|
| 1 | skill selector | `_tool_line NAME VER SRC` |
| 2 | loop-back skill selector | `""` |

Tools have **no scope or target prompts**. Always 2 calls per round.

**Multi-select (tab-select multiple items in one round):**
Encode multiple lines in a single response using `<NL>`:

```bash
"$(_skill_line A …)<NL>$(_skill_line B …)"
```

The mock expands `<NL>` to real newlines, matching real fzf multi-select output.

### Helpers

```bash
_skill_line NAME VER BUNDLE SRC   # build a skill fzf response line
_tool_line  NAME VER SRC           # build a tool fzf response line
_write_responses LINE [LINE ...]   # write response file; "" = empty line (Esc)
_run_interactive [FLAGS...]        # run CLI in interactive mode; captures stdout+stderr
_fzf_call_count                    # how many times mock fzf was called (--version excluded)
_skill_version PATH/TO/SKILL.md    # extract version string, strips quotes
```

### Writing a new interactive test

**Template:**

```bash
@test "interactive: <description>" {
  _write_responses \
    "$(_skill_line skill-analyzer 1.0.0 analysis "${SKILL1_SRC}")" \
    "user" \
    "claude" \
    ""   # Esc on loop-back

  run _run_interactive --force

  [ "$status" -eq 0 ]
  [ -f "${MOCK_HOME}/.claude/skills/skill-analyzer/SKILL.md" ]
  [ "$(_fzf_call_count)" -eq 4 ]
}
```

**Response count = expected `_fzf_call_count`:**

```
skill + scope + target + loop-back(Esc) = 4    (one skill round)
(skill + scope + target) × 2 + Esc     = 7    (two skill rounds)
tool + loop-back(Esc)                   = 2    (one tool round)
skill + scope(Esc)                      = 2    (cancel on scope)
skill + scope + target(Esc)             = 3    (cancel on target)
Esc immediately                         = 1
```

**`--force` is not implicit.** Pass it explicitly when the test needs a clean install:

```bash
run _run_interactive --force      # with force
run _run_interactive               # without force (tests skip/outdated behavior)
```

**Project-scope interactive test:**

```bash
local project_dir="${TEST_DIR}/my-project"
mkdir -p "${project_dir}"

_write_responses "$(_skill_line …)" "project" "claude" ""

local out
out=$(cd "${project_dir}" && \
  HSKILL_TEST_INTERACTIVE=1 \
  HSKILL_FZF_COUNTER_FILE="${COUNTER_FILE}" \
  HSKILL_FZF_RESPONSES_FILE="${RESPONSES_FILE}" \
  HOME="${MOCK_HOME}" \
  PATH="${MOCK_BIN}:${PATH}" \
  NO_COLOR=1 \
  node "${CLI}" --force 2>&1)

[ -f "${project_dir}/.claude/skills/skill-analyzer/SKILL.md" ]
```

---

## Available test fixtures

These constants are defined in both `interactive.bats` and `install.bats`:

| Constant | Value |
|---|---|
| `SKILL1_NAME` | `skill-analyzer` |
| `SKILL1_SRC` | `skills/analysis/skill-analyzer` |
| `SKILL1_VER` | `1.0.0` |
| `SKILL1_BUNDLE` | `analysis` |
| `SKILL2_NAME` | `diataxis-docs` |
| `SKILL2_SRC` | `skills/harness/diataxis-docs` |
| `TOOL_NAME` | `p-launch` |
| `TOOL_SRC` | `tools/p-launch` |

---

## Common mistakes

| Mistake | Fix |
|---|---|
| Using `_run_interactive` without `--force` and expecting a fresh install | Pass `--force` explicitly |
| Forgetting the loop-back `""` response | Every interactive session needs a final `""` to exit the loop |
| Wrong `_fzf_call_count` assertion | Count: skill+scope+target per round, +1 for loop-back; tools skip scope+target |
| `grep version:` gives `"1.0.0"` with quotes | Use `_skill_version` instead of raw grep |
| Asserting skip message in `$output` of `_install` | Skips go to stderr — use `$(_stderr)` |
| Project scope test installing to `MOCK_HOME` | Must `cd` to the project dir before running the CLI |
| Adding a new skill fixture | Pull name, src, ver, bundle from `skills-index.json` — do not hardcode paths |
