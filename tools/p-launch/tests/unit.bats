#!/usr/bin/env bats
# Unit tests for p-launch internal functions.
# Requires: bats-core (brew install bats-core)

setup() {
  SCRIPT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/p-launch.sh"
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_BIN="${TEST_DIR}/bin"
  mkdir -p "${MOCK_HOME}" "${MOCK_BIN}"

  # Silence git global config warnings
  export GIT_CONFIG_NOSYSTEM=1
  export HOME="${MOCK_HOME}"
  git config --global user.email "test@test.com" 2>/dev/null || true
  git config --global user.name "Test" 2>/dev/null || true
  git config --global init.defaultBranch "main" 2>/dev/null || true
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
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    PROJECT_DIRS=(${dirs})
    ${code}
  "
}

# Helper: create a local bare repo and a clone pointing to it (simulates remote)
_make_git_repo_with_remote() {
  local name="$1"
  local bare_dir="${TEST_DIR}/remotes/${name}.git"
  local repo_dir="${TEST_DIR}/repos/${name}"

  mkdir -p "$bare_dir" "$repo_dir"
  git init --bare "$bare_dir" -q
  git clone "$bare_dir" "$repo_dir" -q 2>/dev/null

  # Make an initial commit so main exists on remote
  git -C "$repo_dir" commit --allow-empty -m "init" -q

  git -C "$repo_dir" push origin main -q 2>/dev/null

  echo "$repo_dir"
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

# ── _format_with_status ───────────────────────────────────────────────────────

@test "_format_with_status: outputs exactly four tab-delimited fields" {
  local tmpdir
  tmpdir=$(mktemp -d)
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n' '${MOCK_HOME}/projects/myapp' | _format_with_status
  "
  [ "$status" -eq 0 ]
  local tabs
  tabs=$(printf '%s' "${lines[0]}" | tr -cd '\t' | wc -c | tr -d ' ')
  [ "$tabs" -eq 3 ]
  rm -rf "$tmpdir"
}

@test "_format_with_status: second field is the project name" {
  local tmpdir
  tmpdir=$(mktemp -d)
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n' '${TEST_DIR}/some/path/myproject' | _format_with_status
  "
  local name
  name=$(printf '%s' "${lines[0]}" | cut -f2 | tr -d ' ')
  [ "$name" = "myproject" ]
  rm -rf "$tmpdir"
}

@test "_format_with_status: third field is full path unchanged" {
  local proj="${TEST_DIR}/myproject"
  local tmpdir
  tmpdir=$(mktemp -d)
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n' '${proj}' | _format_with_status
  "
  local full_path
  full_path=$(printf '%s' "${lines[0]}" | cut -f3)
  [ "$full_path" = "${proj}" ]
  rm -rf "$tmpdir"
}

@test "_format_with_status: status is · when no status file exists" {
  local tmpdir
  tmpdir=$(mktemp -d)
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n' '${TEST_DIR}/someproject' | _format_with_status
  "
  local status_col
  status_col=$(printf '%s' "${lines[0]}" | cut -f1)
  [[ "$status_col" == *"·"* ]]
  rm -rf "$tmpdir"
}

@test "_format_with_status: status shows content from status file" {
  local tmpdir proj key
  tmpdir=$(mktemp -d)
  proj="${TEST_DIR}/myrepo"
  # Compute the key the same way the script does
  key=$(printf '%s' "$proj" | shasum -a 256 | cut -c1-16)
  printf '↓3      ' > "${tmpdir}/${key}"

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n' '${proj}' | _format_with_status
  "
  local status_col
  status_col=$(printf '%s' "${lines[0]}" | cut -f1)
  [[ "$status_col" == *"↓3"* ]]
  rm -rf "$tmpdir"
}

@test "_format_with_status: handles multiple projects" {
  local tmpdir
  tmpdir=$(mktemp -d)
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export _STATUS_TMPDIR='${tmpdir}'
    source '${SCRIPT}'
    printf '%s\n%s\n' '${TEST_DIR}/proj-a' '${TEST_DIR}/proj-b' | _format_with_status
  "
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 2 ]
  rm -rf "$tmpdir"
}

# ── _is_git_with_remote ───────────────────────────────────────────────────────

@test "_is_git_with_remote: returns 1 for non-git directory" {
  local plain_dir="${TEST_DIR}/plain"
  mkdir -p "$plain_dir"
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _is_git_with_remote '${plain_dir}'
  "
  [ "$status" -eq 1 ]
}

@test "_is_git_with_remote: returns 1 for git repo without remote" {
  local repo="${TEST_DIR}/no-remote"
  mkdir -p "$repo"
  git -C "$repo" init -q
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _is_git_with_remote '${repo}'
  "
  [ "$status" -eq 1 ]
}

@test "_is_git_with_remote: returns 0 for git repo with remote" {
  local repo
  repo=$(_make_git_repo_with_remote "with-remote")
  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _is_git_with_remote '${repo}'
  "
  [ "$status" -eq 0 ]
}

# ── _write_status_file ────────────────────────────────────────────────────────

@test "_write_status_file: writes · for non-git directory" {
  local plain_dir="${TEST_DIR}/plain"
  local tmpdir
  mkdir -p "$plain_dir"
  tmpdir=$(mktemp -d)

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _write_status_file '${plain_dir}' '${tmpdir}'
    key=\$(_path_key '${plain_dir}')
    cat '${tmpdir}/'\$key
  "
  [[ "$output" == *"·"* ]]
  rm -rf "$tmpdir"
}

@test "_write_status_file: writes ✓ when repo is in sync" {
  local repo tmpdir
  repo=$(_make_git_repo_with_remote "synced-repo")
  tmpdir=$(mktemp -d)

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _write_status_file '${repo}' '${tmpdir}'
    key=\$(_path_key '${repo}')
    cat '${tmpdir}/'\$key
  "
  [[ "$output" == *"✓"* ]]
  rm -rf "$tmpdir"
}

@test "_write_status_file: writes ↑N when repo is ahead" {
  local repo tmpdir
  repo=$(_make_git_repo_with_remote "ahead-repo")
  tmpdir=$(mktemp -d)

  # Make 2 local commits not pushed
  git -C "$repo" commit --allow-empty -m "ahead 1" -q
  git -C "$repo" commit --allow-empty -m "ahead 2" -q

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _write_status_file '${repo}' '${tmpdir}'
    key=\$(_path_key '${repo}')
    cat '${tmpdir}/'\$key
  "
  [[ "$output" == *"↑2"* ]]
  rm -rf "$tmpdir"
}

@test "_write_status_file: writes ↓N when repo is behind" {
  local repo tmpdir bare_dir
  repo=$(_make_git_repo_with_remote "behind-repo")
  bare_dir="${TEST_DIR}/remotes/behind-repo.git"
  tmpdir=$(mktemp -d)

  # Push 2 commits directly to bare (simulates remote advancing)
  local tmp_clone="${TEST_DIR}/tmp-clone"
  git clone "$bare_dir" "$tmp_clone" -q 2>/dev/null
  git -C "$tmp_clone" commit --allow-empty -m "remote 1" -q
  git -C "$tmp_clone" commit --allow-empty -m "remote 2" -q
  git -C "$tmp_clone" push origin main -q 2>/dev/null

  # Fetch so the local repo knows about remote commits
  git -C "$repo" fetch origin -q 2>/dev/null

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _write_status_file '${repo}' '${tmpdir}'
    key=\$(_path_key '${repo}')
    cat '${tmpdir}/'\$key
  "
  [[ "$output" == *"↓2"* ]]
  rm -rf "$tmpdir"
}

@test "_write_status_file: writes ↑N↓M when diverged" {
  local repo tmpdir bare_dir
  repo=$(_make_git_repo_with_remote "diverged-repo")
  bare_dir="${TEST_DIR}/remotes/diverged-repo.git"
  tmpdir=$(mktemp -d)

  # Remote advances
  local tmp_clone="${TEST_DIR}/tmp-clone2"
  git clone "$bare_dir" "$tmp_clone" -q 2>/dev/null
  git -C "$tmp_clone" commit --allow-empty -m "remote advance" -q
  git -C "$tmp_clone" push origin main -q 2>/dev/null

  # Local advances (diverge)
  git -C "$repo" commit --allow-empty -m "local advance" -q

  # Fetch so local knows about remote diverge
  git -C "$repo" fetch origin -q 2>/dev/null

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _write_status_file '${repo}' '${tmpdir}'
    key=\$(_path_key '${repo}')
    cat '${tmpdir}/'\$key
  "
  [[ "$output" == *"↑1"* ]]
  [[ "$output" == *"↓1"* ]]
  rm -rf "$tmpdir"
}

# ── _do_pull ──────────────────────────────────────────────────────────────────

@test "_do_pull: reports 'nothing to pull' when up to date" {
  local repo
  repo=$(_make_git_repo_with_remote "pull-synced")

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _do_pull '${repo}'
  "
  [[ "$output" == *"nothing to pull"* ]]
}

@test "_do_pull: pulls current branch when behind" {
  local repo bare_dir
  repo=$(_make_git_repo_with_remote "pull-behind")
  bare_dir="${TEST_DIR}/remotes/pull-behind.git"

  local tmp_clone="${TEST_DIR}/tmp-clone3"
  git clone "$bare_dir" "$tmp_clone" -q 2>/dev/null
  git -C "$tmp_clone" commit --allow-empty -m "remote commit" -q
  git -C "$tmp_clone" push origin main -q 2>/dev/null

  git -C "$repo" fetch origin -q 2>/dev/null

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _do_pull '${repo}'
  "
  [[ "$output" == *"pulled"*"main"* ]] || [[ "$output" == *"fast-fwd"*"main"* ]]
}

# ── _do_push ──────────────────────────────────────────────────────────────────

@test "_do_push: reports 'nothing to push' when up to date" {
  local repo
  repo=$(_make_git_repo_with_remote "push-synced")

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _do_push '${repo}'
  "
  [[ "$output" == *"nothing to push"* ]]
}

@test "_do_push: pushes branch when ahead" {
  local repo
  repo=$(_make_git_repo_with_remote "push-ahead")

  git -C "$repo" commit --allow-empty -m "local commit" -q

  run zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export GIT_CONFIG_NOSYSTEM=1
    source '${SCRIPT}'
    _do_push '${repo}'
  "
  [[ "$output" == *"pushed"*"main"* ]]
}

# ── _launch: Cursor ────────────────────────────────────────────────────────────

_launch_src() {
  local code="$1"
  # _OSASCRIPT lets tests inject a mock without relying on PATH,
  # since p-launch.sh calls /usr/bin/osascript via full path.
  local mock_osascript="${MOCK_BIN}/osascript"
  local osascript_override=""
  [[ -x "$mock_osascript" ]] && osascript_override="export _OSASCRIPT='${mock_osascript}'"
  zsh -c "
    export _P_LAUNCH_TEST=1
    export HOME='${MOCK_HOME}'
    export PATH='${MOCK_BIN}:${PATH}'
    ${osascript_override}
    source '${SCRIPT}'
    ${code}
  "
}

@test "_launch: reports ✓ Cursor when cursor CLI is in PATH" {
  printf '#!/bin/sh\nexit 0\n' > "${MOCK_BIN}/cursor"
  chmod +x "${MOCK_BIN}/cursor"

  run _launch_src "_launch '${TEST_DIR}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"✓"*"Cursor"* ]]
}

@test "_launch: reports ⚠ Cursor when CLI absent and Cursor.app not found" {
  [[ ! -d "/Applications/Cursor.app" ]] || skip "Cursor.app installed — cannot test absence"

  run _launch_src "_launch '${TEST_DIR}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"⚠"*"Cursor"* ]]
}

# ── _launch: Ghostty ───────────────────────────────────────────────────────────

@test "_launch: reports ✓ Ghostty when osascript succeeds" {
  [[ -d "/Applications/Ghostty.app" ]] || skip "Ghostty.app not installed"
  printf '#!/bin/sh\nexit 0\n' > "${MOCK_BIN}/osascript"
  chmod +x "${MOCK_BIN}/osascript"

  run _launch_src "_launch '${TEST_DIR}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"✓"*"Ghostty"* ]]
}

@test "_launch: reports ⚠ Ghostty when osascript fails" {
  [[ -d "/Applications/Ghostty.app" ]] || skip "Ghostty.app not installed"
  printf '#!/bin/sh\nexit 1\n' > "${MOCK_BIN}/osascript"
  chmod +x "${MOCK_BIN}/osascript"

  run _launch_src "_launch '${TEST_DIR}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"⚠"*"Ghostty"* ]]
}

@test "_launch: reports ⚠ Ghostty when Ghostty.app not found" {
  [[ ! -d "/Applications/Ghostty.app" ]] || skip "Ghostty.app installed — cannot test absence"

  run _launch_src "_launch '${TEST_DIR}'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"⚠"*"Ghostty"* ]]
}

@test "_launch: osascript receives working directory in script" {
  [[ -d "/Applications/Ghostty.app" ]] || skip "Ghostty.app not installed"
  printf '#!/bin/sh\nprintf "ARGS:%%s\n" "$@"\nexit 0\n' \
    > "${MOCK_BIN}/osascript"
  chmod +x "${MOCK_BIN}/osascript"

  run _launch_src "_launch '${TEST_DIR}'"
  [[ "$output" == *"${TEST_DIR}"* ]]
}
