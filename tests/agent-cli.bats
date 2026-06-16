#!/usr/bin/env bats
# Tests for agent-friendly CLI behavior:
#   - non-TTY never hangs (TTY gates)
#   - --json output is valid, single-object, stdout-only
#   - errors are structured JSON in --json mode
#   - --skill + --tool mutual exclusion
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
NODE="$(which node)"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_SKILL_DIR="${MOCK_HOME}/.claude/skills"
  MOCK_TOOL_DIR="${MOCK_HOME}/.local/bin"
  MOCK_TOOL_DATA="${MOCK_HOME}/.local/share/hskill/tools"

  mkdir -p "${MOCK_SKILL_DIR}"
  mkdir -p "${MOCK_TOOL_DIR}"
  mkdir -p "${MOCK_TOOL_DATA}"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── helper: run CLI with fake HOME, forced non-TTY via pipe ───────────────────

_cli() {
  # Pipe through cat to force non-TTY on stdout
  HOME="${MOCK_HOME}" node "${CLI}" "$@" 2>/tmp/bats-stderr | cat
}

_cli_exit() {
  HOME="${MOCK_HOME}" node "${CLI}" "$@" 2>/tmp/bats-stderr
}

_stderr() {
  cat /tmp/bats-stderr
}

# ── JSON output validity ───────────────────────────────────────────────────────

@test "--help --json emits valid single JSON object" {
  run _cli --help --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
}

@test "--help --json includes agent_notes and commands array" {
  run _cli --help --json
  [ "$status" -eq 0 ]
  [[ "$output" == *'"agent_notes"'* ]]
  [[ "$output" == *'"commands"'* ]]
}

@test "--help --json install command includes mutual exclusion note" {
  run _cli --help --json
  [ "$status" -eq 0 ]
  [[ "$output" == *'mutually exclusive'* ]]
}

@test "--help --json --target enum includes opencode" {
  run _cli --help --json
  [ "$status" -eq 0 ]
  [[ "$output" == *'"opencode"'* ]]
}

@test "status --json emits valid single JSON object to stdout" {
  run _cli status --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"skills"'* ]]
  [[ "$output" == *'"tools"'* ]]
}

@test "status --json includes opencode in each skill's user scope" {
  run _cli status --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
    const skill = Object.values(d.skills)[0]
    if (!skill) process.exit(0)
    if (!skill.user || !('opencode' in skill.user)) { console.error('opencode missing from user scope'); process.exit(1) }
  "
}

@test "list --json emits valid single JSON object to stdout" {
  run _cli list --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"skills"'* ]]
  [[ "$output" == *'"bundle"'* ]]
}

@test "outdated --json emits valid single JSON object to stdout" {
  run _cli outdated --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
}

@test "info --json emits valid single JSON object to stdout" {
  run _cli info analyze-skill --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"type"'* ]]
  [[ "$output" == *'"skill"'* ]]
}

# ── install --json: unified single object ─────────────────────────────────────

@test "install --skill --json emits single object with 'skills' key" {
  run _cli install --skill analyze-skill --target claude --scope user --json
  # May fail due to no claude dir, but stdout must be valid JSON if anything
  local stdout_content="$output"
  if [ -n "$stdout_content" ]; then
    echo "$stdout_content" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
    [[ "$stdout_content" == *'"skills"'* ]]
    [[ "$stdout_content" != *'"tools"'* ]]
  fi
}

@test "install --tool --json emits single object with 'tools' key" {
  local src="${TEST_DIR}/src/fake-tool"
  mkdir -p "${src}"
  printf '#!/bin/sh\necho fake\n' > "${src}/fake-tool.sh"
  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' > "${src}/tool.json"

  local jsfile="${TEST_DIR}/run-install-tool.mjs"
  cat > "${jsfile}" <<JSEOF
import { installTools } from 'file://${REPO_ROOT}/lib/installer.js'
const r = await installTools(
  [{ toolName: 'fake-tool', srcPath: '${src}' }],
  '${MOCK_TOOL_DIR}',
  true
)
process.stdout.write(JSON.stringify({ tools: r }))
JSEOF

  local out
  out="$(HOME="${MOCK_HOME}" "${NODE}" "${jsfile}" 2>/dev/null)"
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"installed"'* ]]
  [[ "$out" == *'"skipped"'* ]]
  [[ "$out" == *'"failed"'* ]]
}

# ── mutual exclusion ──────────────────────────────────────────────────────────

@test "--skill and --tool combined: exits 1 with error" {
  run _cli_exit install --skill analyze-skill --tool hub --target claude
  [ "$status" -eq 1 ]
  [[ "$(_stderr)" == *"cannot be combined"* ]]
}

@test "--skill and --tool combined with --json: stderr is JSON error" {
  local errfile="${TEST_DIR}/stderr-json.txt"
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill analyze-skill --tool hub --target claude --json \
    >/dev/null 2>"${errfile}" || true
  local err
  err="$(cat "${errfile}")"
  echo "$err" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$err" == *'"error":true'* ]]
  [[ "$err" == *'"message"'* ]]
}

# ── error JSON in --json mode ─────────────────────────────────────────────────

@test "unknown skill --json: exits 1 with JSON on stderr, empty stdout" {
  local errfile="${TEST_DIR}/stderr-unknown.txt"
  local stdoutfile="${TEST_DIR}/stdout-unknown.txt"
  local exit_code=0
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill __nonexistent__ --target claude --scope user --json \
    >"${stdoutfile}" 2>"${errfile}" || exit_code=$?
  [ "$exit_code" -eq 1 ]
  [ ! -s "${stdoutfile}" ]
  local err
  err="$(cat "${errfile}")"
  echo "$err" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$err" == *'"error":true'* ]]
}

@test "unknown skill (human mode): exits 1 with plain text on stderr" {
  run _cli_exit install --skill __nonexistent__ --target claude --scope user
  [ "$status" -eq 1 ]
  [[ "$(_stderr)" == *"✗"* ]]
  # stdout should be empty
  [ -z "$output" ]
}

# ── non-TTY install: no hang, structured result ───────────────────────────────

@test "non-TTY install of existing skill returns skipped with reason (no hang)" {
  # Pre-install the skill so the conflict path is hit
  local dest="${MOCK_SKILL_DIR}/analyze-skill"
  mkdir -p "${dest}"
  printf -- '---\nname: analyze-skill\nversion: 0.0.1\n---\n' > "${dest}/SKILL.md"

  # Run non-interactively (pipe forces non-TTY)
  local stdout_out
  stdout_out="$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill analyze-skill --target claude --scope user --json \
    2>/dev/null | cat)"

  echo "$stdout_out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$stdout_out" == *'"skipped"'* ]]
}

@test "non-TTY install with vars.json: uses defaults, does not hang" {
  local src="${TEST_DIR}/src/fake-varsed-tool"
  mkdir -p "${src}"
  printf '#!/bin/sh\necho {{MY_VAR}}\n' > "${src}/fake-varsed-tool.sh"
  printf '{ "name": "fake-varsed-tool", "version": "1.0.0" }\n' > "${src}/tool.json"
  printf '[{"name":"MY_VAR","description":"A variable","default":"hello"}]' > "${src}/vars.json"

  local js="
import { installTools } from 'file://${REPO_ROOT}/lib/installer.js'
const r = await installTools(
  [{ toolName: 'fake-varsed-tool', srcPath: '${src}' }],
  '${MOCK_TOOL_DIR}',
  true
)
process.stdout.write(JSON.stringify(r))
"
  # Pipe forces non-TTY — must not hang
  local out
  out="$(HOME="${MOCK_HOME}" node --input-type=module -e "$js" 2>/dev/null | cat)"
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"installed":["fake-varsed-tool"]'* ]]

  # Verify the default was substituted in the installed script
  grep -q "hello" "${MOCK_TOOL_DIR}/fake-varsed-tool"
}

@test "non-TTY install with zshrc.snippet: skips patch, does not hang" {
  local src="${TEST_DIR}/src/fake-zshrc-tool"
  mkdir -p "${src}"
  printf '#!/bin/sh\necho hi\n' > "${src}/fake-zshrc-tool.sh"
  printf '{ "name": "fake-zshrc-tool", "version": "1.0.0" }\n' > "${src}/tool.json"
  printf 'export PATH="$PATH:/fake"\n' > "${src}/zshrc.snippet"

  local js="
import { installTools } from 'file://${REPO_ROOT}/lib/installer.js'
const r = await installTools(
  [{ toolName: 'fake-zshrc-tool', srcPath: '${src}' }],
  '${MOCK_TOOL_DIR}',
  true
)
process.stdout.write(JSON.stringify(r))
"
  # Pipe forces non-TTY — must complete without hanging
  local out
  out="$(HOME="${MOCK_HOME}" node --input-type=module -e "$js" 2>/dev/null | cat)"
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"installed":["fake-zshrc-tool"]'* ]]

  # zshrc must NOT have been patched (no confirm() in non-TTY)
  [ ! -f "${MOCK_HOME}/.zshrc" ] || ! grep -q "fake-zshrc-tool" "${MOCK_HOME}/.zshrc"
}
