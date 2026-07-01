#!/usr/bin/env bats
# End-to-end tests for `hskill install` (flag-based, non-interactive).
#
# These tests run the real CLI with --skill / --bundle / --tool / --scope /
# --target flags and verify actual file-system state after installation.
# They complement agent-cli.bats (which tests JSON output shape) by asserting
# that the right files end up in the right directories.
#
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
NODE="$(which node)"

SKILL1_NAME="survey-skillrepo"
SKILL1_SRC="${REPO_ROOT}/skills/research/survey-skillrepo"
SKILL1_VER="2.0.1"

SKILL2_NAME="manage-docs"
SKILL2_SRC="${REPO_ROOT}/skills/writing/manage-docs"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}/.claude/skills"
  mkdir -p "${MOCK_HOME}/.cursor/skills"
  mkdir -p "${MOCK_HOME}/.config/opencode/skills"
  mkdir -p "${MOCK_HOME}/.local/bin"
  mkdir -p "${MOCK_HOME}/.hskill/tools"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── helpers ───────────────────────────────────────────────────────────────────

# Run CLI non-interactively (pipe forces non-TTY); captures stdout.
_install() {
  HOME="${MOCK_HOME}" node "${CLI}" install "$@" 2>/tmp/bats-install-stderr | cat
}

_stderr() { cat /tmp/bats-install-stderr; }

# Extract the installed version from a SKILL.md (strips surrounding quotes).
_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

# ── single skill installation ─────────────────────────────────────────────────

@test "install --skill: SKILL.md written to target dir" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill: installed version matches available version" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "${SKILL1_VER}" ]
}

@test "install --skill --target cursor: installs to cursor dir" {
  _install --skill "${SKILL1_NAME}" --target cursor --scope user --force
  [ -f "${MOCK_HOME}/.cursor/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill --target opencode: installs to ~/.config/opencode/skills" {
  _install --skill "${SKILL1_NAME}" --target opencode --scope user --force
  [ -f "${MOCK_HOME}/.config/opencode/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill --target opencode --scope project: installs to .opencode/skills" {
  local project_dir="${TEST_DIR}/opencode-proj"
  mkdir -p "${project_dir}"
  (cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target opencode --scope project --force 2>/dev/null | cat)
  [ -f "${project_dir}/.opencode/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.config/opencode/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --skill --target all: installs to every target including opencode" {
  _install --skill "${SKILL1_NAME}" --target all --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.cursor/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.config/opencode/skills/${SKILL1_NAME}/SKILL.md" ]
}

# ── project scope ─────────────────────────────────────────────────────────────

@test "install --scope project: installs to cwd/.claude/skills" {
  local project_dir="${TEST_DIR}/my-project"
  mkdir -p "${project_dir}"
  (cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope project --force 2>/dev/null | cat)
  [ -f "${project_dir}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

@test "install --scope project: does not install to user-scope dir" {
  local project_dir="${TEST_DIR}/proj2"
  mkdir -p "${project_dir}"
  (cd "${project_dir}" && HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope project --force 2>/dev/null | cat)
  [ ! -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
}

# ── force flag ────────────────────────────────────────────────────────────────

@test "install --force: overwrites an outdated skill" {
  # Pre-install old version.
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "${SKILL1_VER}" ]
}

@test "install (no --force): up-to-date skill is skipped" {
  # Pre-install at current version.
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  # Second install without --force; stderr should mention skipped.
  local err
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user \
    2>/tmp/bats-install-stderr >/dev/null | cat
  err="$(_stderr)"
  [[ "$err" == *"skipped"* ]] || [[ "$err" == *"up-to-date"* ]]
}

@test "install (no --force): outdated skill skipped, old version preserved" {
  mkdir -p "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL1_NAME}" \
    > "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md"

  _install --skill "${SKILL1_NAME}" --target claude --scope user

  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md")" = "0.0.1" ]
}

# ── bundle installation ───────────────────────────────────────────────────────

@test "install --bundle devops: installs all skills in the bundle" {
  _install --bundle devops --target claude --scope user --force
  # devops bundle contains clean-git.
  [ -f "${MOCK_HOME}/.claude/skills/clean-git/SKILL.md" ]
}

@test "install --bundle writing: installs all skills in the bundle" {
  _install --bundle writing --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL2_NAME}/SKILL.md" ]
}

@test "install --bundle: --json reports installed list" {
  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --bundle research --target claude --scope user --force --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"installed"'* ]]
  [[ "$out" == *"${SKILL1_NAME}"* ]]
}

# ── multiple skills ───────────────────────────────────────────────────────────

@test "install --skill (comma-separated): installs all listed skills" {
  _install --skill "${SKILL1_NAME},${SKILL2_NAME}" --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}/SKILL.md" ]
  [ -f "${MOCK_HOME}/.claude/skills/${SKILL2_NAME}/SKILL.md" ]
}

# ── JSON output ───────────────────────────────────────────────────────────────

@test "install --skill --json: reports installed skill under target key" {
  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user --force --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"skills"'* ]]
  [[ "$out" == *'"claude"'* ]]
  [[ "$out" == *"${SKILL1_NAME}"* ]]
}

@test "install --skill --json: skipped entry has reason field" {
  # Pre-install so next run skips.
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force

  local out
  out=$(HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL1_NAME}" --target claude --scope user --json 2>/dev/null | cat)
  echo "$out" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$out" == *'"skipped"'* ]]
  [[ "$out" == *'"reason"'* ]]
}

# ── uninstall skill ───────────────────────────────────────────────────────────

_uninstall() {
  HOME="${MOCK_HOME}" node "${CLI}" uninstall "$@" 2>/tmp/bats-uninstall-stderr | cat
}


@test "uninstall skill: removes skill dir from user claude" {
  _install --skill "${SKILL1_NAME}" --target claude --scope user --force
  [ -d "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}" ]
  HOME="${MOCK_HOME}" node "${CLI}" uninstall "${SKILL1_NAME}" --scope user --target claude
  [ ! -d "${MOCK_HOME}/.claude/skills/${SKILL1_NAME}" ]
}

@test "uninstall skill: exits 0 when skill not installed" {
  run _uninstall "${SKILL1_NAME}" --scope user --target claude
  [ "$status" -eq 0 ]
}

@test "install --skill: sync-hotfix installs SKILL.md to claude skills dir" {
  _install --skill sync-hotfix --target claude --scope user --force
  [ -f "${MOCK_HOME}/.claude/skills/sync-hotfix/SKILL.md" ]
  [ "$(_skill_version "${MOCK_HOME}/.claude/skills/sync-hotfix/SKILL.md")" = "1.1.1" ]
}
