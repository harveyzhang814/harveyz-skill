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

  # Silence git global config warnings
  export GIT_CONFIG_NOSYSTEM=1
  git config --global user.email "test@test.com" 2>/dev/null || true
  git config --global user.name "Test" 2>/dev/null || true
  git config --global init.defaultBranch "main" 2>/dev/null || true
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# Shorthand: run the installed script with MOCK_HOME and mock fzf first in PATH.
_run_p() {
  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch" "$@"
}

# Helper: create a local bare repo and a clone pointing to it
_make_git_repo_with_remote() {
  local name="$1"
  local base="${2:-${PROJECTS_DIR}}"
  local bare_dir="${TEST_DIR}/remotes/${name}.git"
  local repo_dir="${base}/${name}"

  mkdir -p "$bare_dir" "$repo_dir"
  git init --bare "$bare_dir" -q
  git clone "$bare_dir" "$repo_dir" -q 2>/dev/null

  git -C "$repo_dir" commit --allow-empty -m "init" -q
  git -C "$repo_dir" push origin main -q 2>/dev/null

  echo "$repo_dir"
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  [ ! -d "${MOCK_HOME}/.config/p-launch" ]
}

@test "--uninstall: full cleanup removes all three targets at once" {
  printf '%s\n' "${ZSHRC_BLOCK}" > "${MOCK_HOME}/.zshrc"

  run bash -c "
    printf 'y\n' | \
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
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
    env HOME='${MOCK_HOME}' PATH='${MOCK_BIN}:${PATH}' GIT_CONFIG_NOSYSTEM=1 \
      zsh '${MOCK_BIN}/p-launch' --uninstall
  "
  [ "$status" -eq 0 ]
  # Output should not mention config dir since it was absent.
  [[ "$output" != *".config/p-launch"* ]]
}

# ── Internal: --_pull ─────────────────────────────────────────────────────────

@test "--_pull: reports nothing to pull for synced repo" {
  local repo
  repo=$(_make_git_repo_with_remote "pull-synced-e2e")

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch" --_pull "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"nothing to pull"* ]]
}

@test "--_pull: pulls behind branch" {
  local repo bare_dir
  repo=$(_make_git_repo_with_remote "pull-behind-e2e")
  bare_dir="${TEST_DIR}/remotes/pull-behind-e2e.git"

  local tmp_clone="${TEST_DIR}/tc1"
  git clone "$bare_dir" "$tmp_clone" -q 2>/dev/null
  git -C "$tmp_clone" commit --allow-empty -m "remote ahead" -q
  git -C "$tmp_clone" push origin main -q 2>/dev/null

  git -C "$repo" fetch origin -q 2>/dev/null

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch" --_pull "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"main"* ]]
  # Confirm local repo has been updated
  local local_sha remote_sha
  local_sha=$(git -C "$repo" rev-parse main)
  remote_sha=$(git -C "$repo" rev-parse origin/main)
  [ "$local_sha" = "$remote_sha" ]
}

# ── Internal: --_push ─────────────────────────────────────────────────────────

@test "--_push: reports nothing to push for synced repo" {
  local repo
  repo=$(_make_git_repo_with_remote "push-synced-e2e")

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch" --_push "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"nothing to push"* ]]
}

@test "--_push: pushes ahead branch to remote" {
  local repo bare_dir
  repo=$(_make_git_repo_with_remote "push-ahead-e2e")
  bare_dir="${TEST_DIR}/remotes/push-ahead-e2e.git"

  git -C "$repo" commit --allow-empty -m "local ahead" -q

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch" --_push "$repo"

  [ "$status" -eq 0 ]
  [[ "$output" == *"pushed"*"main"* ]]
  # Confirm remote was updated
  local repo_sha bare_sha
  repo_sha=$(git -C "$repo" rev-parse main)
  bare_sha=$(git -C "$bare_dir" rev-parse main)
  [ "$repo_sha" = "$bare_sha" ]
}

# ── Internal: --_format-no-fetch ──────────────────────────────────────────────

@test "--_format-no-fetch: outputs four-column tab-delimited format" {
  local tmpdir repo
  tmpdir=$(mktemp -d)
  mkdir -p "${PROJECTS_DIR}/myproject"

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    _STATUS_TMPDIR="$tmpdir" \
    zsh "${MOCK_BIN}/p-launch" --_format-no-fetch

  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -ge 1 ]
  local tabs
  tabs=$(printf '%s' "${lines[0]}" | tr -cd '\t' | wc -c | tr -d ' ')
  [ "$tabs" -eq 3 ]
  rm -rf "$tmpdir"
}

@test "--_format-no-fetch: skips fetch (non-git dirs show · status)" {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "${PROJECTS_DIR}/plain-dir"

  run env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    _STATUS_TMPDIR="$tmpdir" \
    zsh "${MOCK_BIN}/p-launch" --_format-no-fetch

  [ "$status" -eq 0 ]
  [[ "${lines[0]}" == *"·"* ]]
  rm -rf "$tmpdir"
}

# ── Parallel fetch: non-git dirs do not hang ──────────────────────────────────

@test "parallel fetch completes when project dirs have no remote" {
  mkdir -p "${PROJECTS_DIR}/plain1" "${PROJECTS_DIR}/plain2"
  local repo_no_remote="${PROJECTS_DIR}/no-remote"
  mkdir -p "$repo_no_remote"
  git -C "$repo_no_remote" init -q

  # Mock fzf to exit immediately (prevents interactive wait)
  printf '#!/bin/sh\nexit 0\n' > "${MOCK_BIN}/fzf"
  chmod +x "${MOCK_BIN}/fzf"

  run timeout 10 env HOME="${MOCK_HOME}" PATH="${MOCK_BIN}:${PATH}" \
    GIT_CONFIG_NOSYSTEM=1 \
    zsh "${MOCK_BIN}/p-launch"

  # Should not timeout (exit code 124 = timeout)
  [ "$status" -ne 124 ]
}
