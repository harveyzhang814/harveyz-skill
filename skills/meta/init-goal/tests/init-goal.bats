#!/usr/bin/env bats

SKILL_MD="$(cd "${BATS_TEST_DIRNAME}/.." && pwd)/SKILL.md"

_fm() {
  local field="$1"
  awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' "${SKILL_MD}" \
    | grep "^${field}:" | head -1 \
    | sed "s/^${field}:[[:space:]]*//" | tr -d '"'"'"
}

@test "SKILL.md exists" {
  [ -f "${SKILL_MD}" ]
}

@test "frontmatter: name is init-goal" {
  [ "$(_fm name)" = "init-goal" ]
}

@test "frontmatter: version is present and semver-like" {
  local v
  v="$(_fm version)"
  [ -n "${v}" ]
  echo "${v}" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$'
}

@test "frontmatter: user_invocable is true" {
  [ "$(_fm user_invocable)" = "true" ]
}

@test "frontmatter: description is non-empty" {
  local d
  d="$(_fm description)"
  [ -n "${d}" ]
}

@test "body: contains all 8 steps" {
  for i in 1 2 3 4 5 6 7 8; do
    grep -q "## Step ${i}" "${SKILL_MD}"
  done
}

@test "body: step 6 has both sub-questions 6a and 6b" {
  grep -q "子问题 6a" "${SKILL_MD}"
  grep -q "子问题 6b" "${SKILL_MD}"
}

@test "body: contains all 5 template names" {
  grep -q "Fix Until Green" "${SKILL_MD}"
  grep -q "Research Loop" "${SKILL_MD}"
  grep -q "Refine Until Satisfied" "${SKILL_MD}"
  grep -q "Monitor & React" "${SKILL_MD}"
  grep -q "Explore & Map" "${SKILL_MD}"
}

@test "body: prompt.md output format includes all required sections" {
  grep -q "## GOal" "${SKILL_MD}"
  grep -q "## 每轮执行" "${SKILL_MD}"
  grep -q "## 评估" "${SKILL_MD}"
  grep -q "## 约束" "${SKILL_MD}"
  grep -q "## 退出条件" "${SKILL_MD}"
  grep -q "## 过程文档" "${SKILL_MD}"
}

@test "body: references log.md and summary.md" {
  grep -q "log.md" "${SKILL_MD}"
  grep -q "summary.md" "${SKILL_MD}"
}

@test "body: references ~/.hskill/init-goal data directory" {
  grep -q "~/.hskill/init-goal" "${SKILL_MD}"
}
