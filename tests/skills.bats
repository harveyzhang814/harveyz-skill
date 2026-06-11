#!/usr/bin/env bats
# Structural validation for all skills registered in skills-index.json.
# Runs automatically as part of `bats tests/`.
#
# Each check loops over every registered skill; failures are accumulated and
# reported together so one bad skill doesn't hide others.

REPO_ROOT="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)"
INDEX="${REPO_ROOT}/skills-index.json"

# ---------------------------------------------------------------------------
# Helper: extract a single frontmatter field value from a SKILL.md file.
# Strips surrounding single or double quotes from the value.
# Usage: _fm <file> <field>
# ---------------------------------------------------------------------------
_fm() {
  local file="$1" field="$2"
  awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' "$file" \
    | grep "^${field}:" | head -1 \
    | sed "s/^${field}:[[:space:]]*//" | tr -d '"'"'"
}

# ---------------------------------------------------------------------------
# Helper: read the skills array from skills-index.json.
# Returns one "path|bundle" record per line.
# ---------------------------------------------------------------------------
_skill_records() {
  node -e "
    const idx = JSON.parse(require('fs').readFileSync('${INDEX}', 'utf8'));
    idx.skills.forEach(s => console.log(s.path + '|' + s.bundle));
  "
}

# ---------------------------------------------------------------------------
# Helper: read all bundle keys from bundleMeta.
# Returns one key per line.
# ---------------------------------------------------------------------------
_bundle_keys() {
  node -e "
    const idx = JSON.parse(require('fs').readFileSync('${INDEX}', 'utf8'));
    Object.keys(idx.bundleMeta).forEach(k => console.log(k));
  "
}

# ---------------------------------------------------------------------------
# 1. SKILL.md exists
# ---------------------------------------------------------------------------
@test "all skills: SKILL.md file exists" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    if [ ! -f "${skill_md}" ]; then
      failures+=("${path}: SKILL.md not found")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 2. frontmatter block is present (starts and ends with ---)
# ---------------------------------------------------------------------------
@test "all skills: SKILL.md has frontmatter delimiters" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local open_count close_count
    open_count=$(grep -c '^---' "${skill_md}" || true)
    # Need at least two --- lines (opening + closing)
    if [ "${open_count}" -lt 2 ]; then
      failures+=("${path}: frontmatter delimiters missing (found ${open_count} '---' lines, need >=2)")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 3. frontmatter has a non-empty `name:` field
# ---------------------------------------------------------------------------
@test "all skills: frontmatter has non-empty name" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local value
    value=$(_fm "${skill_md}" "name")
    if [ -z "${value}" ]; then
      failures+=("${path}: 'name' field missing or empty")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 4. frontmatter has a non-empty `description:` field
# ---------------------------------------------------------------------------
@test "all skills: frontmatter has non-empty description" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local value
    value=$(_fm "${skill_md}" "description")
    if [ -z "${value}" ]; then
      failures+=("${path}: 'description' field missing or empty")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 5. frontmatter has a non-empty `version:` field
# ---------------------------------------------------------------------------
@test "all skills: frontmatter has non-empty version" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local value
    value=$(_fm "${skill_md}" "version")
    if [ -z "${value}" ]; then
      failures+=("${path}: 'version' field missing or empty")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 6. version conforms to X.Y.Z semantic versioning
# ---------------------------------------------------------------------------
@test "all skills: version is valid semver (X.Y.Z)" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local ver
    ver=$(_fm "${skill_md}" "version")
    [ -z "${ver}" ] && continue  # already caught in test 5

    if ! echo "${ver}" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
      failures+=("${path}: version '${ver}' does not match X.Y.Z")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 7. frontmatter `name` equals the last path segment (directory name)
# ---------------------------------------------------------------------------
@test "all skills: frontmatter name matches directory name" {
  local failures=()
  while IFS='|' read -r path _bundle; do
    local skill_md="${REPO_ROOT}/skills/${path}/SKILL.md"
    [ -f "${skill_md}" ] || continue

    local dir_name fm_name
    dir_name="${path##*/}"
    fm_name=$(_fm "${skill_md}" "name")

    if [ "${fm_name}" != "${dir_name}" ]; then
      failures+=("${path}: name '${fm_name}' != directory '${dir_name}'")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# 8. bundle value exists in bundleMeta
# ---------------------------------------------------------------------------
@test "all skills: bundle is defined in bundleMeta" {
  local failures=()
  # Build a newline-separated list of valid bundle keys once
  local valid_bundles
  valid_bundles=$(_bundle_keys)

  while IFS='|' read -r path bundle; do
    if ! echo "${valid_bundles}" | grep -qx "${bundle}"; then
      failures+=("${path}: bundle '${bundle}' not in bundleMeta")
    fi
  done < <(_skill_records)

  if [ ${#failures[@]} -gt 0 ]; then
    echo "FAILURES:"
    printf '  %s\n' "${failures[@]}"
    return 1
  fi
}
