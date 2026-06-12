#!/usr/bin/env bats
# Tests for tool version detection: lib/bundles.js, lib/installer.js, bin/preview.mjs
# Requires: bats-core (brew install bats-core)

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"

setup() {
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_SRC="${TEST_DIR}/src/fake-tool"

  mkdir -p "${MOCK_HOME}/.local/bin"
  mkdir -p "${MOCK_HOME}/.hskill/tools"
  mkdir -p "${MOCK_SRC}"

  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' > "${MOCK_SRC}/tool.json"
  printf '#!/bin/sh\necho fake\n' > "${MOCK_SRC}/fake-tool.sh"
  chmod +x "${MOCK_SRC}/fake-tool.sh"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# Helper: call checkToolInstalled('fake-tool', MOCK_SRC) and print JSON
_preview() {
  HOME="${MOCK_HOME}" node "${REPO_ROOT}/bin/preview.mjs" "$@"
}

_check() {
  local js="
import { checkToolInstalled } from 'file://${REPO_ROOT}/lib/bundles.js'
const r = checkToolInstalled('fake-tool', '${MOCK_SRC}')
process.stdout.write(JSON.stringify(r))
"
  HOME="${MOCK_HOME}" node --input-type=module -e "$js"
}

# ── checkToolInstalled ─────────────────────────────────────────────────────────

@test "checkToolInstalled: binary absent → none" {
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"none"'* ]]
  [[ "$output" == *'"version":"—"'* ]]
}

@test "checkToolInstalled: binary present, no data JSON → up-to-date (cannot compare)" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
  [[ "$output" == *'"version":"—"'* ]]
}

@test "checkToolInstalled: binary present, versions match → up-to-date" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
  [[ "$output" == *'"version":"1.0.0"'* ]]
}

@test "checkToolInstalled: binary present, versions differ → update" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool", "version": "0.9.0" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"update"'* ]]
  [[ "$output" == *'"version":"0.9.0"'* ]]
}

@test "checkToolInstalled: malformed data JSON → up-to-date (safe fallback)" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf 'not valid json\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
}

@test "checkToolInstalled: data JSON missing version field → up-to-date" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
}

@test "checkToolInstalled: source tool.json missing → up-to-date (safe fallback)" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  rm "${MOCK_SRC}/tool.json"
  run _check
  [ "$status" -eq 0 ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
}

# ── legacy path migration ──────────────────────────────────────────────────────

@test "migration: old tools dir moved to new location on first checkToolInstalled" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  rm -rf "${MOCK_HOME}/.hskill/tools"   # simulate fresh install without new dir
  mkdir -p "${MOCK_HOME}/.local/share/hskill/tools"
  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' \
    > "${MOCK_HOME}/.local/share/hskill/tools/fake-tool.json"
  run _check
  [ "$status" -eq 0 ]
  [ -f "${MOCK_HOME}/.hskill/tools/fake-tool.json" ]
  [ ! -d "${MOCK_HOME}/.local/share/hskill/tools" ]
  [[ "$output" == *'"status":"up-to-date"'* ]]
}

# ── installer: tool.json copied to data dir ────────────────────────────────────

@test "installer: copies tool.json to data dir on install" {
  local data_json="${MOCK_HOME}/.hskill/tools/fake-tool.json"
  local js="
import { installTools } from 'file://${REPO_ROOT}/lib/installer.js'
await installTools(
  [{ toolName: 'fake-tool', srcPath: '${MOCK_SRC}' }],
  '${MOCK_HOME}/.local/bin',
  true
)
"
  HOME="${MOCK_HOME}" node --input-type=module -e "$js"
  [ -f "${data_json}" ]
  grep -q '"version"' "${data_json}"
}

@test "installer: skips data JSON write when source tool.json absent" {
  rm "${MOCK_SRC}/tool.json"
  local data_json="${MOCK_HOME}/.hskill/tools/fake-tool.json"
  local js="
import { installTools } from 'file://${REPO_ROOT}/lib/installer.js'
await installTools(
  [{ toolName: 'fake-tool', srcPath: '${MOCK_SRC}' }],
  '${MOCK_HOME}/.local/bin',
  true
)
"
  HOME="${MOCK_HOME}" node --input-type=module -e "$js"
  [ ! -f "${data_json}" ]
}

# ── preview.mjs ────────────────────────────────────────────────────────────────

@test "preview: tool not installed shows 'not installed'" {
  run _preview \
    fake-tool 1.0.0 tool "${MOCK_SRC}"
  [ "$status" -eq 0 ]
  [[ "$output" == *"not installed"* ]]
}

@test "preview: tool installed and up-to-date shows 'ok'" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool", "version": "1.0.0" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _preview \
    fake-tool 1.0.0 tool "${MOCK_SRC}"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok"* ]]
}

@test "preview: tool installed with older version shows 'update'" {
  touch "${MOCK_HOME}/.local/bin/fake-tool"
  printf '{ "name": "fake-tool", "version": "0.9.0" }\n' \
    > "${MOCK_HOME}/.hskill/tools/fake-tool.json"
  run _preview \
    fake-tool 1.0.0 tool "${MOCK_SRC}"
  [ "$status" -eq 0 ]
  [[ "$output" == *"update"* ]]
}
