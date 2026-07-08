#!/usr/bin/env bats
# End-to-end tests for `hskill upgrade`.
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
SKILL_NAME="survey-skillrepo"
SKILL_SRC="${REPO_ROOT}/skills/research/survey-skillrepo"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}/.claude/skills"
  mkdir -p "${MOCK_HOME}/.cursor/skills"
  mkdir -p "${MOCK_HOME}/.config/opencode/skills"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

_upgrade() {
  HOME="${MOCK_HOME}" node "${CLI}" upgrade "$@" 2>/tmp/bats-upgrade-stderr | cat
}

_upgrade_exit() {
  HOME="${MOCK_HOME}" node "${CLI}" upgrade "$@" 2>/tmp/bats-upgrade-stderr
}

_stderr() { cat /tmp/bats-upgrade-stderr; }

_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

_install_old_version() {
  local target="${1:-claude}"
  local dest="${MOCK_HOME}/.${target}/skills/${SKILL_NAME}"
  mkdir -p "${dest}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${SKILL_NAME}" > "${dest}/SKILL.md"
}

# ── basic upgrade ─────────────────────────────────────────────────────────────

@test "upgrade --skill --target: upgrades outdated skill" {
  _install_old_version claude
  _upgrade --skill "${SKILL_NAME}" --target claude --scope user
  local installed_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL_NAME}/SKILL.md")"
  local available_ver
  available_ver="$(_skill_version "${SKILL_SRC}/SKILL.md")"
  [ "${installed_ver}" = "${available_ver}" ]
}

@test "upgrade --skill --target: skips skill not installed on that target" {
  # skill installed on claude but NOT cursor
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target cursor --scope user
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_HOME}/.cursor/skills/${SKILL_NAME}/SKILL.md" ]
  [[ "$output" == *"up to date"* ]]
}

@test "upgrade --skill --target: skips already up-to-date skill silently" {
  # Install at current version
  HOME="${MOCK_HOME}" node "${CLI}" install \
    --skill "${SKILL_NAME}" --target claude --scope user --force 2>/dev/null | cat
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user
  [ "$status" -eq 0 ]
  [[ "$output" == *"up to date"* ]]
}

@test "upgrade --target: upgrades all outdated skills on that target" {
  _install_old_version claude
  _upgrade --target claude --scope user
  local installed_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${SKILL_NAME}/SKILL.md")"
  local available_ver
  available_ver="$(_skill_version "${SKILL_SRC}/SKILL.md")"
  [ "${installed_ver}" = "${available_ver}" ]
}

@test "upgrade (global): nothing installed prints up-to-date message" {
  run _upgrade
  [ "$status" -eq 0 ]
  [[ "$output" == *"up to date"* ]]
}

# ── --json output ─────────────────────────────────────────────────────────────

@test "upgrade --json: valid JSON to stdout when skill upgraded" {
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))"
  [[ "$output" == *'"skills"'* ]]
}

@test "upgrade --json: installed array contains skill name after upgrade" {
  _install_old_version claude
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
    const installed = d.skills?.claude?.installed ?? []
    if (!installed.includes('${SKILL_NAME}')) {
      console.error('skill not in installed:', JSON.stringify(installed))
      process.exit(1)
    }
  "
}

@test "upgrade --json: upToDate:true when nothing to upgrade" {
  run _upgrade --skill "${SKILL_NAME}" --target claude --scope user --json
  [ "$status" -eq 0 ]
  echo "$output" | node -e "
    const d = JSON.parse(require('fs').readFileSync('/dev/stdin','utf8'))
    if (!d.upToDate) { console.error('upToDate missing'); process.exit(1) }
  "
}

@test "upgrade --skill unknown: exits 1 with error" {
  run _upgrade_exit --skill __nonexistent__ --target claude --scope user
  [ "$status" -eq 1 ]
  [[ "$(_stderr)" == *"Unknown skill"* ]]
}
