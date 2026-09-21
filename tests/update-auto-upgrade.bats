#!/usr/bin/env bats
# Tests for the `autoUpdate` skills-index.json field: `hskill update` should
# auto-upgrade any already-installed skill flagged `autoUpdate: true`, and
# leave everything else alone.
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
CLI="${REPO_ROOT}/bin/cli.js"
INDEX="${REPO_ROOT}/skills-index.json"
INDEX_BACKUP="${REPO_ROOT}/skills-index.json.bats-backup"

AUTO_SKILL="survey-skillrepo"
AUTO_SKILL_SRC="${REPO_ROOT}/skills/research/survey-skillrepo"
PLAIN_SKILL="learn-skill"
PLAIN_SKILL_SRC="${REPO_ROOT}/skills/mint/learn-skill"

setup() {
  cp "${INDEX}" "${INDEX_BACKUP}"
  node -e "
    const fs = require('fs');
    const idx = JSON.parse(fs.readFileSync('${INDEX}', 'utf8'));
    const s = idx.skills.find(s => s.path === 'research/survey-skillrepo');
    if (!s) throw new Error('survey-skillrepo entry not found');
    s.autoUpdate = true;
    fs.writeFileSync('${INDEX}', JSON.stringify(idx, null, 2) + '\n');
  "

  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}/.claude/skills"

  GLOBAL_ROOT="${TEST_DIR}/global"
  mkdir -p "${GLOBAL_ROOT}/harveyz-skill"
  printf '{"name":"harveyz-skill","version":"1.0.0"}\n' > "${GLOBAL_ROOT}/harveyz-skill/package.json"

  NPM_LOG="${TEST_DIR}/npm.log"
  MOCK_BIN="${TEST_DIR}/bin"
  mkdir -p "${MOCK_BIN}"
  cp "${BATS_TEST_DIRNAME}/helpers/mock-npm.sh" "${MOCK_BIN}/npm"
  chmod +x "${MOCK_BIN}/npm"
}

teardown() {
  mv "${INDEX_BACKUP}" "${INDEX}"
  rm -rf "${TEST_DIR}"
}

_update() {
  HOME="${MOCK_HOME}" HSKILL_GLOBAL_ROOT="${GLOBAL_ROOT}" HSKILL_TEST_NPM_LOG="${NPM_LOG}" \
    PATH="${MOCK_BIN}:${PATH}" node "${CLI}" update "$@"
}

_skill_version() {
  grep -o 'version: [^[:space:]]*' "$1" | head -1 | awk '{print $2}' | tr -d '"'
}

_install_old_version() {
  local name="$1" dest="${MOCK_HOME}/.claude/skills/$1"
  mkdir -p "${dest}"
  printf -- '---\nname: %s\nversion: 0.0.1\n---\n' "${name}" > "${dest}/SKILL.md"
}

@test "update: auto-upgrades an installed skill flagged autoUpdate:true" {
  _install_old_version "${AUTO_SKILL}"
  run _update
  [ "$status" -eq 0 ]

  local installed_ver available_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${AUTO_SKILL}/SKILL.md")"
  available_ver="$(_skill_version "${AUTO_SKILL_SRC}/SKILL.md")"
  [ "${installed_ver}" = "${available_ver}" ]
  [[ "$output" == *"Auto-updated"* ]]
  [[ "$output" == *"${AUTO_SKILL}"* ]]
}

@test "update: leaves an outdated skill without autoUpdate untouched" {
  _install_old_version "${PLAIN_SKILL}"
  run _update
  [ "$status" -eq 0 ]

  local installed_ver
  installed_ver="$(_skill_version "${MOCK_HOME}/.claude/skills/${PLAIN_SKILL}/SKILL.md")"
  [ "${installed_ver}" = "0.0.1" ]
}

@test "update: skips auto-upgrade entirely when the flagged skill isn't installed" {
  run _update
  [ "$status" -eq 0 ]
  [[ "$output" != *"Auto-updated"* ]]
  [ ! -d "${MOCK_HOME}/.claude/skills/${AUTO_SKILL}" ]
}
