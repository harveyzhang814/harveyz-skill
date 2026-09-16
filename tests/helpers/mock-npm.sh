#!/usr/bin/env bash
# Mock `npm` binary for install-source.bats. Intercepts `npm pack` and
# `npm install -g` so the local/npm update flow can be exercised without
# touching the real global npm environment.
#
# HSKILL_TEST_NPM_LOG    — file that every invocation's args get appended to (one line each)
# HSKILL_GLOBAL_ROOT     — same global root the CLI under test uses (via lib/install-source.js)
#
# `npm root -g` prints HSKILL_GLOBAL_ROOT so any code path that shells out to
# it directly (rather than reading the env var) still resolves consistently.
set -euo pipefail

: "${HSKILL_TEST_NPM_LOG:?HSKILL_TEST_NPM_LOG not set}"
echo "$*" >> "$HSKILL_TEST_NPM_LOG"

case "$1" in
  pack)
    dest=""
    prev=""
    for arg in "$@"; do
      if [ "$prev" = "--pack-destination" ]; then dest="$arg"; fi
      prev="$arg"
    done
    name="harveyz-skill-0.0.0-mock.tgz"
    touch "${dest}/${name}"
    echo "$name"
    ;;
  install)
    : "${HSKILL_GLOBAL_ROOT:?HSKILL_GLOBAL_ROOT not set}"
    rm -rf "${HSKILL_GLOBAL_ROOT}/harveyz-skill"
    mkdir -p "${HSKILL_GLOBAL_ROOT}/harveyz-skill"
    printf '{"name":"harveyz-skill","version":"%s"}\n' \
      "${HSKILL_TEST_NPM_INSTALLED_VERSION:-0.0.0}" \
      > "${HSKILL_GLOBAL_ROOT}/harveyz-skill/package.json"
    ;;
  root)
    : "${HSKILL_GLOBAL_ROOT:?HSKILL_GLOBAL_ROOT not set}"
    echo "$HSKILL_GLOBAL_ROOT"
    ;;
  *)
    echo "mock-npm: unhandled subcommand: $1" >&2
    exit 1
    ;;
esac
