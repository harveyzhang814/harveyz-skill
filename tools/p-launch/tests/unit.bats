#!/usr/bin/env bats
# Launcher tests for p-launch.sh
# Logic (git operations, branch status) is covered in test_p_launch.py.
# Requires: bats-core (brew install bats-core)

setup() {
  SCRIPT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/p-launch.sh"
  TEST_DIR="$(mktemp -d)"
  MOCK_HOME="${TEST_DIR}/home"
  MOCK_BIN="${TEST_DIR}/bin"
  mkdir -p "${MOCK_HOME}" "${MOCK_BIN}"

  export GIT_CONFIG_NOSYSTEM=1
  export HOME="${MOCK_HOME}"
}

teardown() {
  rm -rf "${TEST_DIR}"
}

# ── Dependency checks ─────────────────────────────────────────────────────────

@test "launcher: exits with error when python3 is missing" {
  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  run zsh -c "
    export PATH='${fake_bin}'
    source '${SCRIPT}'
  "
  [ "$status" -ne 0 ]
  [[ "$output" == *"python3"* ]]
}

# ── venv setup ───────────────────────────────────────────────────────────────

@test "launcher: creates venv on first run" {
  local real_python3
  real_python3=$(command -v python3)

  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  # Fake pip that silently succeeds
  cat > "${fake_bin}/pip" <<'EOF'
#!/bin/sh
exit 0
EOF
  chmod +x "${fake_bin}/pip"

  # Fake python3: creates a minimal venv structure when called with -m venv,
  # delegates real python3 -m venv for proper creation, passes dep checks
  cat > "${fake_bin}/python3" <<EOF
#!/bin/sh
# Pass through to real python3 for venv creation and script execution
exec "${real_python3}" "\$@"
EOF
  chmod +x "${fake_bin}/python3"

  local venv_dir="${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  [ ! -d "$venv_dir" ]

  # Create a minimal py file so the launcher can exec it
  local tools_dir="${MOCK_HOME}/.local/share/hskill/tools"
  mkdir -p "$tools_dir"
  printf 'import sys\nprint("launched")\n' > "${tools_dir}/p-launch.py"

  run env PATH="${fake_bin}:${PATH}" HOME="${MOCK_HOME}" \
    zsh "${SCRIPT}"
  [ -d "$venv_dir" ]
}

@test "launcher: skips venv setup when venv already exists" {
  local real_python3
  real_python3=$(command -v python3)

  # Pre-create a venv
  local venv_dir="${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  "${real_python3}" -m venv "$venv_dir"

  # Put a minimal p-launch.py in place
  local tools_dir="${MOCK_HOME}/.local/share/hskill/tools"
  mkdir -p "$tools_dir"
  printf 'print("launched")\n' > "${tools_dir}/p-launch.py"

  # Fake python3 that would fail if called for venv creation
  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  cat > "${fake_bin}/python3" <<EOF
#!/bin/sh
if echo "\$*" | grep -q "venv"; then
  echo "ERROR: venv should not be created again" >&2
  exit 1
fi
exec "${real_python3}" "\$@"
EOF
  chmod +x "${fake_bin}/python3"

  run env PATH="${fake_bin}:${PATH}" HOME="${MOCK_HOME}" \
    zsh "${SCRIPT}"
  [[ "$output" != *"Setting up"* ]]
  [ "$status" -eq 0 ]
}

@test "launcher: exits with error when p-launch.py is not found" {
  local real_python3
  real_python3=$(command -v python3)

  # Pre-create a venv with real python so dep setup is skipped
  local venv_dir="${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  "${real_python3}" -m venv "$venv_dir"

  # No p-launch.py installed, no dev fallback
  local dir="${TEST_DIR}/tool"
  mkdir -p "$dir"
  cp "${SCRIPT}" "${dir}/p-launch.sh"
  # Do NOT create p-launch.py next to the script

  run env HOME="${MOCK_HOME}" zsh "${dir}/p-launch.sh"
  [ "$status" -ne 0 ]
  [[ "$output" == *"p-launch.py not found"* ]]
}

@test "launcher: dev fallback runs p-launch.py next to script" {
  local real_python3
  real_python3=$(command -v python3)

  # Pre-create a venv so setup is skipped
  local venv_dir="${MOCK_HOME}/.local/share/hskill/p-launch-venv"
  "${real_python3}" -m venv "$venv_dir"

  # Place launcher + minimal py side-by-side (dev setup)
  local dir="${TEST_DIR}/tool"
  mkdir -p "$dir"
  cp "${SCRIPT}" "${dir}/p-launch.sh"
  printf 'print("ok-from-py")\n' > "${dir}/p-launch.py"

  run env HOME="${MOCK_HOME}" zsh "${dir}/p-launch.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok-from-py"* ]]
}
