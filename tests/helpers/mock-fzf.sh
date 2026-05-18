#!/usr/bin/env bash
# Stateful fzf mock for hskill interactive tests.
#
# Each test sets up two env vars before running the CLI:
#   HSKILL_FZF_COUNTER_FILE   — path to a file that tracks call count (auto-created)
#   HSKILL_FZF_RESPONSES_FILE — path to a file with one response per line
#
# On each invocation this script:
#   1. Short-circuits --version probes (requireFzf) without touching the counter
#   2. Reads stdin to unblock the CLI (spawnSync writes to our stdin pipe)
#   3. Increments the counter
#   4. Reads line N from the responses file (N = current call count)
#   5. Empty line or missing line → exits 1 (simulates Esc / nothing selected)
#   6. Otherwise prints that line to stdout and exits 0
#
# Response file format (one entry per line):
#   <output>         — printed verbatim to stdout
#   (empty line)     — simulates Esc/cancel
#
# Multi-select: encode multiple selected lines with <NL> separator.
# Example: "line1<NL>line2<NL>line3" outputs three lines to fzfSelect.
#
# All other CLI flags passed by hskill (--multi, --ansi, --preview, etc.)
# are silently ignored.

# requireFzf() probes fzf with --version before making any real call.
# Return a fake version string without touching the response counter.
for arg in "$@"; do
  if [ "$arg" = "--version" ]; then
    echo "0.0.0 (mock)"
    exit 0
  fi
done

# Drain stdin so the CLI's pipe write doesn't block.
cat > /dev/null

if [ -z "${HSKILL_FZF_COUNTER_FILE}" ] || [ -z "${HSKILL_FZF_RESPONSES_FILE}" ]; then
  echo "mock-fzf: HSKILL_FZF_COUNTER_FILE and HSKILL_FZF_RESPONSES_FILE must be set" >&2
  exit 2
fi

# Increment call counter (atomic enough for sequential tests).
count=$(cat "${HSKILL_FZF_COUNTER_FILE}" 2>/dev/null || echo 0)
count=$((count + 1))
echo "$count" > "${HSKILL_FZF_COUNTER_FILE}"

# Read the Nth response line.
response=$(sed -n "${count}p" "${HSKILL_FZF_RESPONSES_FILE}" 2>/dev/null)

if [ -z "$response" ]; then
  # Nothing selected / Esc.
  exit 1
fi

# Expand <NL> into real newlines (used for multi-select responses).
printf '%s' "$response" | awk '{gsub(/<NL>/, "\n"); printf "%s\n", $0}'
exit 0
