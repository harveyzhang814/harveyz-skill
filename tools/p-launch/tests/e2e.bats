#!/usr/bin/env bats
# E2E tests for p-launch — exercises the script as a real executable.
# Requires: bats-core (brew install bats-core)

ZSHRC_BLOCK=$'
# >>> p-launch (added by harveyz-skill) >>>\nexport PATH="$HOME/.local/bin:$PATH"\nalias p=p-launch\n# <<< p-launch <<<\n'

setup() {
  SCRIPT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/p-launch.sh"
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_BIN="${TEST_DIR}/bin"
  PROJECTS_DIR="${TEST_DIR}/projects"

  mkdir -p "${MOCK_HOME}" "${MOCK_BIN}" "${PROJECTS_DIR}"

  # Install a copy of the script (as the real installer would do).
  # Config file provides PROJECT_DIRS so the {{PROJECT_DIR}} placeholder
  # never has to be substituted.
  cp "${SCRIPT}" "${MOCK_BIN}/p-launch"
  chmod +x "${MOCK_BIN}/p-launch"
  mkdir -p "${MOCK_HOME}/.config/p-launch"
  printf 'PROJECT_DIRS=("%s")\n' "${PROJECTS_DIR}" \
    > "${MOCK_HOME}/.config/p-launch/config.zsh"

  # Minimal mock for fzf — enough to satisfy _check_deps.
  printf '#!/bin/sh\nexit 0\n' > "${MOCK_BIN}/fzf"
  chmod +x "${MOCK_BIN}/fzf"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# Shorthand: run the installed script with MOCK_HOME and mock fzf first in PATH.
_run_p() {
  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    zsh "${MOCK_BIN}/p-launch" "$@"
}

# ── Syntax ────────────────────────────────────────────────────────────────────

@test "script passes zsh -n syntax check" {
  run zsh -n "${SCRIPT}"
  [ "$status" -eq 0 ]
}

# ── Dependency guard ──────────────────────────────────────────────────────────

@test "exits 1 with fzf error when fzf is absent from PATH" {
  # Use an empty PATH so fzf cannot be found, but invoke zsh by full path.
  local ZSH_BIN
  ZSH_BIN="$(command -v zsh)"
  mkdir -p "${TEST_DIR}/empty"
  run bash -c "printf '' | env HOME='${MOCK_HOME}' PATH='${TEST_DIR}/empty' \
    '$ZSH_BIN' '${MOCK_BIN}/p-launch' 2>&1"
  [ "$status" -eq 1 ]
  [[ "$output" == *"fzf"* ]]
}

# ── No projects ───────────────────────────────────────────────────────────────

@test "exits 0 and prints message when project dir is empty" {
  # PROJECTS_DIR exists but has no subdirectories.
  _run_p
  [ "$status" -eq 0 ]
  [[ "$output" == *"no projects found"* ]]
}

# ── --uninstall: abort ────────────────────────────────────────────────────────

@test "--uninstall: N answer removes nothing" {
  printf '%s\n' "${ZSHRC_BLOCK}" > "${MOCK_HOME}/.zshrc"

  run bash -c "
    printf 'n\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  [[ "$output" == *"aborted"* ]]

  # Nothing should have been removed.
  [ -f "${MOCK_BIN}/p-launch" ]
  grep -q "# >>> p-launch" "${MOCK_HOME}/.zshrc"
  [ -d "${MOCK_HOME}/.config/p-launch" ]
}

# ── --uninstall: confirm ──────────────────────────────────────────────────────

@test "--uninstall: Y removes the script itself" {
  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_BIN}/p-launch" ]
}

@test "--uninstall: Y strips the marker block from .zshrc" {
  printf 'export BEFORE=1\n%s\nexport AFTER=2\n' "${ZSHRC_BLOCK}" \
    > "${MOCK_HOME}/.zshrc"

  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  ! grep -q "# >>> p-launch" "${MOCK_HOME}/.zshrc"
  grep -q "BEFORE=1"         "${MOCK_HOME}/.zshrc"
  grep -q "AFTER=2"          "${MOCK_HOME}/.zshrc"
}

@test "--uninstall: Y removes the config directory" {
  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  [ ! -d "${MOCK_HOME}/.config/p-launch" ]
}

@test "--uninstall: full cleanup removes all three targets at once" {
  printf '%s\n' "${ZSHRC_BLOCK}" > "${MOCK_HOME}/.zshrc"

  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  [ ! -f "${MOCK_BIN}/p-launch" ]
  ! grep -q "p-launch"        "${MOCK_HOME}/.zshrc"
  [ ! -d "${MOCK_HOME}/.config/p-launch" ]
}

@test "--uninstall: skips .zshrc when marker is absent" {
  printf 'export FOO=bar\n' > "${MOCK_HOME}/.zshrc"

  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  # Existing .zshrc content must be intact.
  [ "$(cat "${MOCK_HOME}/.zshrc")" = "export FOO=bar" ]
}

@test "--uninstall: skips config dir when it does not exist" {
  rm -rf "${MOCK_HOME}/.config/p-launch"

  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  # Output should not mention config dir since it was absent.
  [[ "$output" != *".config/p-launch"* ]]
}
