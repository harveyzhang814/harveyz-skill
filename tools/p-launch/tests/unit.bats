#!/usr/bin/env bats
# Unit tests for p-launch internal functions.
# Requires: bats-core (brew install bats-core)

setup() {
  SCRIPT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/p-launch.sh"
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  mkdir -p "${MOCK_HOME}"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# Helper: run a zsh snippet that sources the script in test mode.
# PROJECT_DIRS is overridden AFTER sourcing so the script's default
# doesn't interfere.
_src() {
  local dirs="$1" code="$2"
  zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    PROJECT_DIRS=(${dirs})
    ${code}
  "
}

# ── _collect ──────────────────────────────────────────────────────────────────

@test "_collect: fails when project dir does not exist" {
  run _src "'${TEST_DIR}/nonexistent'" "_collect"
  [ "$status" -eq 1 ]
  [ -z "$output" ]
}

@test "_collect: fails when project dir is empty" {
  mkdir -p "${TEST_DIR}/projects"
  run _src "'${TEST_DIR}/projects'" "_collect"
  [ "$status" -eq 1 ]
}

@test "_collect: lists subdirectories" {
  mkdir -p "${TEST_DIR}/projects/alpha" "${TEST_DIR}/projects/beta"
  run _src "'${TEST_DIR}/projects'" "_collect"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 2 ]
}

@test "_collect: sorts by mtime descending (newest first)" {
  mkdir -p "${TEST_DIR}/projects/old" \
            "${TEST_DIR}/projects/mid" \
            "${TEST_DIR}/projects/new"
  touch -t 202001010000 "${TEST_DIR}/projects/old"
  touch -t 202006010000 "${TEST_DIR}/projects/mid"
  touch -t 202101010000 "${TEST_DIR}/projects/new"

  run _src "'${TEST_DIR}/projects'" "_collect"
  [ "$status" -eq 0 ]
  [[ "${lines[0]}" == *"/new" ]]
  [[ "${lines[1]}" == *"/mid" ]]
  [[ "${lines[2]}" == *"/old" ]]
}

@test "_collect: merges multiple base dirs" {
  mkdir -p "${TEST_DIR}/dir1/proj-a" "${TEST_DIR}/dir2/proj-b"
  run _src "'${TEST_DIR}/dir1' '${TEST_DIR}/dir2'" "_collect"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 2 ]
}

@test "_collect: skips files, only returns directories" {
  mkdir -p "${TEST_DIR}/projects/valid-dir"
  touch    "${TEST_DIR}/projects/afile.txt"
  run _src "'${TEST_DIR}/projects'" "_collect"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"valid-dir" ]]
}

@test "_collect: skips non-existent base dirs silently" {
  mkdir -p "${TEST_DIR}/real/proj-a"
  run _src "'${TEST_DIR}/real' '${TEST_DIR}/ghost'" "_collect"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
}

# ── _format ───────────────────────────────────────────────────────────────────

@test "_format: outputs exactly three tab-delimited fields" {
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    printf '%s\n' '${MOCK_HOME}/projects/myapp' | _format
  "
  [ "$status" -eq 0 ]
  local tabs
  tabs=$(printf '%s' "${lines[0]}" | tr -cd '\t' | wc -c | tr -d ' ')
  [ "$tabs" -eq 2 ]
}

@test "_format: first field is the project name (basename)" {
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    printf '%s\n' '${TEST_DIR}/some/deep/path/myproject' | _format
  "
  local name
  name=$(printf '%s' "${lines[0]}" | cut -f1)
  [ "$name" = "myproject" ]
}

@test "_format: second field is the full path unchanged" {
  local proj="${TEST_DIR}/myproject"
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    printf '%s\n' '${proj}' | _format
  "
  local full_path
  full_path=$(printf '%s' "${lines[0]}" | cut -f2)
  [ "$full_path" = "${proj}" ]
}

@test "_format: third field replaces HOME with ~" {
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    printf '%s\n' '${MOCK_HOME}/projects/myapp' | _format
  "
  local parent
  parent=$(printf '%s' "${lines[0]}" | cut -f3)
  [[ "$parent" == "~"* ]]
  [[ "$parent" != *"${MOCK_HOME}"* ]]
}

@test "_format: handles multiple projects" {
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    source '${SCRIPT}'
    printf '%s\n%s\n' '${TEST_DIR}/proj-a' '${TEST_DIR}/proj-b' | _format
  "
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 2 ]
}
