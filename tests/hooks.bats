#!/usr/bin/env bats
# E2E tests for `hskill hooks` subcommand.

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
HOOK_NAME="check-similar-branch"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_PROJECT="${TEST_DIR}/project"
  mkdir -p "${MOCK_HOME}/.claude"
  mkdir -p "${MOCK_PROJECT}/.claude"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── list ──────────────────────────────────────────────────────────────────────

@test "hooks list: shows available hook name" {
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list 2>&1)"
  echo "$output" | grep -q "${HOOK_NAME}"
}

@test "hooks list --json: returns valid JSON with hooks array" {
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list --json 2>&1)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    if (!Array.isArray(d.hooks)) throw new Error('hooks must be array');
    const h = d.hooks.find(h => h.name === '${HOOK_NAME}');
    if (!h) throw new Error('hook not found in JSON output');
  "
}

# ── install user scope ────────────────────────────────────────────────────────

@test "hooks install --scope user: copies script to ~/.claude/hooks/" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  [ -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --scope user: script is executable" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  [ -x "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --scope user: registers in ~/.claude/settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered in settings.json');
  "
}

# ── install project scope ─────────────────────────────────────────────────────

@test "hooks install --scope project: copies script to project .claude/hooks/" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"
  [ -f "${MOCK_PROJECT}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --scope project: registers in project .claude/settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_PROJECT}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered in project settings.json');
  "
}

# ── dedup / force ─────────────────────────────────────────────────────────────

@test "hooks install: skips if already installed without --force" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user 2>&1)"
  echo "$output" | grep -qiE "skip|already"
}

@test "hooks install --force: no duplicate registration in settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --force
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const count = entries.filter(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh'))).length;
    if (count !== 1) throw new Error('expected exactly 1 registration, got ' + count);
  "
}

# ── uninstall ─────────────────────────────────────────────────────────────────

@test "hooks uninstall: removes script file" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks uninstall "${HOOK_NAME}" --scope user
  [ ! -f "${MOCK_HOME}/.claude/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks uninstall: removes registration from settings.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user
  HOME="${MOCK_HOME}" node "${CLI}" hooks uninstall "${HOOK_NAME}" --scope user
  node -e "
    const s = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.claude/settings.json','utf8'));
    const entries = s.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (found) throw new Error('hook still registered after uninstall');
  "
}
