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
  # Run the script with a PATH that has no python3 (but keeps system dirs for zsh itself)
  run zsh -c "
    export PATH='${fake_bin}'
    source '${SCRIPT}'
  "
  [ "$status" -ne 0 ]
  [[ "$output" == *"python3"* ]]
}

@test "launcher: exits with error when textual is not installed" {
  # python3 is present but cannot import textual
  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  # Fake python3 that fails 'import textual' but succeeds otherwise
  cat > "${fake_bin}/python3" <<'EOF'
#!/bin/sh
if [ "$1" = "-c" ] && echo "$2" | grep -q "import textual"; then
  exit 1
fi
exec /usr/bin/env python3 "$@"
EOF
  chmod +x "${fake_bin}/python3"
  run env PATH="${fake_bin}:${PATH}" zsh "${SCRIPT}"
  [ "$status" -ne 0 ]
  [[ "$output" == *"textual"* ]]
}

@test "launcher: exits with error when p-launch.py is not found" {
  # python3 + textual both ok, but PYFILE is missing
  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  cat > "${fake_bin}/python3" <<'EOF'
#!/bin/sh
# Succeed for dep check ('import textual'), fail for missing script
if [ "$1" = "-c" ]; then exit 0; fi
exit 2
EOF
  chmod +x "${fake_bin}/python3"
  # Override home so ~/.local/share/hskill/tools/p-launch.py doesn't exist
  run env PATH="${fake_bin}:${PATH}" HOME="${MOCK_HOME}" \
    zsh -c "
      # Patch the dev fallback by setting 0 to a non-existent path
      zsh '${SCRIPT}'
    "
  # Should error (python3 fake exits 2 when given a .py file)
  [ "$status" -ne 0 ]
}

@test "launcher: dev fallback runs p-launch.py next to script" {
  # Create a minimal p-launch.py next to the launcher
  local dir="${TEST_DIR}/tool"
  mkdir -p "$dir"
  cp "${SCRIPT}" "${dir}/p-launch.sh"
  printf '#!/usr/bin/env python3\nprint("ok-from-py")\n' > "${dir}/p-launch.py"

  # Resolve the real python3 path before manipulating PATH
  local real_python3
  real_python3=$(command -v python3)

  # Fake python3: passes dep checks (-c), delegates to real python3 for scripts
  local fake_bin="${TEST_DIR}/fake-bin"
  mkdir -p "$fake_bin"
  cat > "${fake_bin}/python3" <<EOF
#!/bin/sh
if [ "\$1" = "-c" ]; then exit 0; fi
exec "${real_python3}" "\$@"
EOF
  chmod +x "${fake_bin}/python3"

  run env PATH="${fake_bin}:${PATH}" HOME="${MOCK_HOME}" \
    zsh "${dir}/p-launch.sh"
  [[ "$output" == *"ok-from-py"* ]]
}
