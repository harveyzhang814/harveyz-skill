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
  echo "$output" | grep -qiE "skip|up-to-date|outdated"
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

# ── version tracking ──────────────────────────────────────────────────────────

@test "hooks install: JSON output reason is 'up-to-date' when reinstalling same version" {
  # Install first time
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"

  # Install again — should be up-to-date
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --json --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}" 2>/dev/null)"
  [ "$(echo "$output" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')); process.stdout.write(d.skipped[0].reason)")" = "up-to-date" ]
  echo "$output" | node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf8')); if (!d.skipped[0].version) throw new Error('version field missing')"
}

@test "hooks install: --force reinstalls hook (version field present after force)" {
  # Install first time
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"

  # Force reinstall
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --json --force --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}" 2>/dev/null)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    if (!Array.isArray(d.installed) || d.installed.length !== 1) throw new Error('expected 1 installed, got: ' + JSON.stringify(d.installed));
    if (d.installed[0] !== '${HOOK_NAME}') throw new Error('wrong hook name: ' + d.installed[0]);
  "
}

@test "hooks install: outdated skip when installed version differs from available" {
  # Install first (gets version 1.0.0)
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}"

  # Patch the installed script to have a fake old version
  HOOKS_DIR="${MOCK_PROJECT}/.claude/hooks"
  sed -i.bak 's/# version: 1.0.0/# version: 0.9.0/' "${HOOKS_DIR}/${HOOK_NAME}.sh"

  # Reinstall without --force in non-TTY (should be outdated)
  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks install --json --name "${HOOK_NAME}" --scope project --project "${MOCK_PROJECT}" 2>/dev/null)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    if (d.skipped[0].reason !== 'outdated') throw new Error('expected outdated, got: ' + d.skipped[0].reason);
    if (d.skipped[0].installed !== '0.9.0') throw new Error('expected installed=0.9.0, got: ' + d.skipped[0].installed);
    if (d.skipped[0].available !== '1.0.0') throw new Error('expected available=1.0.0, got: ' + d.skipped[0].available);
  "

  # Cleanup backup
  rm -f "${HOOKS_DIR}/${HOOK_NAME}.sh.bak"
}

# ── codex target ──────────────────────────────────────────────────────────────

@test "hooks install --target codex --scope user: copies script to ~/.codex/hooks/" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  [ -f "${MOCK_HOME}/.codex/hooks/${HOOK_NAME}.sh" ]
}

@test "hooks install --target codex --scope user: registers in ~/.codex/hooks.json" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const found = entries.some(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh')));
    if (!found) throw new Error('hook not registered in ~/.codex/hooks.json');
  "
}

@test "hooks install --target codex: command uses absolute path" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const cmd = entries.flatMap(e => e.hooks ?? []).find(h => h.command?.includes('${HOOK_NAME}.sh'))?.command;
    if (!cmd) throw new Error('command not found');
    if (!require('path').isAbsolute(cmd)) throw new Error('command is not absolute: ' + cmd);
  "
}

@test "hooks install --target codex: no type field in hooks.json entry" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const entry = entries.flatMap(e => e.hooks ?? []).find(h => h.command?.includes('${HOOK_NAME}.sh'));
    if (!entry) throw new Error('entry not found');
    if ('type' in entry) throw new Error('type field must not be present in codex hooks.json');
  "
}

@test "hooks install --force --target codex: no duplicate registration" {
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --target codex
  HOME="${MOCK_HOME}" node "${CLI}" hooks install --name "${HOOK_NAME}" --scope user --target codex --force
  node -e "
    const d = JSON.parse(require('fs').readFileSync('${MOCK_HOME}/.codex/hooks.json','utf8'));
    const entries = d.hooks?.PreToolUse ?? [];
    const count = entries.filter(e => e.hooks?.some(h => h.command?.includes('${HOOK_NAME}.sh'))).length;
    if (count !== 1) throw new Error('expected 1 registration, got ' + count);
  "
}

# ── codex status in list ──────────────────────────────────────────────────────

@test "hooks list --json: includes codex install status" {
  # Install into codex user scope
  HOME="${MOCK_HOME}" node "${CLI}" hooks install \
    --name "${HOOK_NAME}" --scope user --target codex

  output="$(HOME="${MOCK_HOME}" node "${CLI}" hooks list --json 2>&1)"
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'));
    const h = d.hooks.find(h => h.name === '${HOOK_NAME}');
    if (!h) throw new Error('hook not found');
    if (!h.codex) throw new Error('codex field missing from hook status');
    if (h.codex.user.status !== 'installed') throw new Error('expected codex.user=installed, got: ' + h.codex.user.status);
  "
}
