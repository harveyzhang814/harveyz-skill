#!/usr/bin/env bats
# 从 hook-templates.md 逐字提取 merge-via 相关 MANAGED 块，代入 staging 与对应标记，
# 在临时仓库里组装成真实 hooks，验证手动合并进合并目标被拒、脚本合并与远端同步合并放行（Spec 5.4 d、第 7 节第 5 条）。

TEMPLATE="${BATS_TEST_DIRNAME}/../references/hook-templates.md"
ZERO=0000000000000000000000000000000000000000

# extract_block <块 ID>：取 BEGIN MANAGED / END MANAGED 两行之间（含两行）的内容，并代入占位符
extract_block() {
  local out
  out="$(awk -v id="$1" '
    index($0, "# --- BEGIN MANAGED: " id " ") == 1 { on = 1 }
    on { print }
    index($0, "# --- END MANAGED: " id) == 1 { on = 0 }
  ' "$TEMPLATE")"
  [ -n "$out" ] || { echo "template has no block: $1" >&2; return 1; }
  printf '%s\n' "$out" | sed \
    -e 's|<merge_target>|staging|g' \
    -e 's|<merge_trailer>|Merge-Via: merge-to-staging.sh|g' \
    -e 's|<merge_script>|scripts/merge-to-staging.sh|g'
}

# 组装三个 hook 并启用（与真实生成结果同构：固定头部 + MANAGED 块 + 固定尾部）
install_hooks() {
  HOOKS="$TMP/hooks"; mkdir -p "$HOOKS"
  {
    printf '%s\n' '#!/bin/sh' 'BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)' '[ -z "$BRANCH" ] && exit 0' \
      'IS_MERGE=0' '[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && IS_MERGE=1'
    extract_block 'branches.protected/<merge_target>'
    printf '%s\n' 'exit 0'
  } > "$HOOKS/pre-commit"
  {
    printf '%s\n' '#!/bin/sh' 'MSG=$(cat "$1")' 'SUBJECT=$(printf '"'"'%s\n'"'"' "$MSG" | head -1)' \
      'SUBJECT=$(printf '"'"'%s\n'"'"' "$SUBJECT" | sed '"'"'/^#/d'"'"' | sed '"'"'s/^[[:space:]]*//'"'"')' \
      '[ -z "$SUBJECT" ] && exit 0'
    extract_block 'commit-msg/merge-via'
    # 现有 commit-msg/format 块首行：合并提交直接放行（merge-via 必须排在它之前才有意义）
    printf '%s\n' '[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && exit 0' 'exit 0'
  } > "$HOOKS/commit-msg"
  {
    printf '%s\n' '#!/bin/sh' 'while IFS=" " read -r local_ref local_sha remote_ref remote_sha; do'
    extract_block 'pre-push/merge-via'
    printf '%s\n' '    case "$remote_ref" in' '    esac' 'done' 'exit 0'
  } > "$HOOKS/pre-push"
  chmod +x "$HOOKS"/*
  git config core.hooksPath "$HOOKS"
}

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  git init -q -b main repo && cd repo
  git config user.email t@example.com && git config user.name t
  echo base > a.txt && git add a.txt && git commit -qm seed
  git branch staging
  git checkout -q -b topic
  echo t > b.txt && git add b.txt && git commit -qm topic
  git checkout -q staging
  git init -q --bare "$TMP/remote.git"
  git remote add origin "$TMP/remote.git"
  git push -q origin staging   # 基线推送先于装 hook，保证后面的远端状态干净
  install_hooks
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

# 不经任何 hook 造一个合并提交挂到 staging：mk_merge <提交信息>
mk_merge() {
  local tree merge
  tree="$(git rev-parse topic^{tree})"
  merge="$(git commit-tree "$tree" -p staging -p topic -m "$1")"
  git update-ref refs/heads/staging "$merge"
}

@test "hand merge into staging is rejected by commit-msg" {
  before="$(git rev-parse staging)"
  run git merge --no-ff -m "Merge branch 'topic'" topic
  [ "$status" -ne 0 ]
  [[ "$output" == *"scripts/merge-to-staging.sh"* ]]
  [ "$(git rev-parse staging)" = "$before" ]
}

@test "hand merge after conflict is rejected" {
  git checkout -q topic && echo topic > a.txt && git commit -qam topic-a --no-verify
  git checkout -q staging && echo main > a.txt && git commit -qam main-a --no-verify
  before="$(git rev-parse staging)"
  run git merge --no-ff topic
  [ "$status" -ne 0 ]
  echo resolved > a.txt && git add a.txt
  run git commit -q --no-edit
  [ "$status" -ne 0 ]
  [[ "$output" == *"scripts/merge-to-staging.sh"* ]]
  [ "$(git rev-parse staging)" = "$before" ]
}

@test "remote sync merge subject is allowed" {
  run git merge --no-ff -m "Merge branch 'staging' of /some/remote" topic
  [ "$status" -eq 0 ]
  [ "$(git rev-list --parents -n1 staging | wc -w)" -eq 3 ]
}

@test "commit carrying the trailer is allowed" {
  run git merge --no-ff -m "Merge branch 'topic'" -m "Merge-Via: merge-to-staging.sh" topic
  [ "$status" -eq 0 ]
  [ "$(git rev-list --parents -n1 staging | wc -w)" -eq 3 ]
  # 别的标记不算数
  git reset -q --hard HEAD~1
  run git merge --no-ff -m "Merge branch 'topic'" -m "Merge-Via: other.sh" topic
  [ "$status" -ne 0 ]
}

@test "pre-push rejects a first-parent commit without trailer" {
  mk_merge "Merge branch 'topic'"
  run git push origin staging
  [ "$status" -ne 0 ]
  [[ "$output" == *"scripts/merge-to-staging.sh"* ]]
  [ "$(git -C "$TMP/remote.git" rev-parse staging)" != "$(git rev-parse staging)" ]
  # 一个带标记的合并盖在上面也救不了范围内的无标记提交
  git checkout -q -b topic2 topic
  echo u > c.txt && git add c.txt && git commit -qm topic2
  git checkout -q staging
  merge="$(git commit-tree "$(git rev-parse topic2^{tree})" -p staging -p topic2 -m "$(printf "Merge branch 'topic2'\n\nMerge-Via: merge-to-staging.sh")")"
  git update-ref refs/heads/staging "$merge"
  run git push origin staging
  [ "$status" -ne 0 ]
}

@test "pre-push allows trailer and remote-sync commits" {
  mk_merge "$(printf "Merge branch 'topic'\n\nMerge-Via: merge-to-staging.sh")"
  git checkout -q topic
  echo v > d.txt && git add d.txt && git commit -qm topic-more
  git checkout -q staging
  tree="$(git rev-parse topic^{tree})"
  merge="$(git commit-tree "$tree" -p staging -p topic -m "Merge branch 'staging' of /some/remote")"
  git update-ref refs/heads/staging "$merge"
  # 范围内的第二父提交（topic 上无标记的提交）不检查，只查 first-parent
  run git push origin staging
  [ "$status" -eq 0 ]
  [ "$(git -C "$TMP/remote.git" rev-parse staging)" = "$(git rev-parse staging)" ]
  # 删除远端分支不归 merge-via 管
  run git push origin :staging
  [ "$status" -eq 0 ]
}

@test "direct commit on staging is still rejected by pre-commit" {
  echo x > e.txt && git add e.txt
  before="$(git rev-parse staging)"
  run git commit -qm "feat: direct"
  [ "$status" -ne 0 ]
  [[ "$output" == *"scripts/merge-to-staging.sh"* ]]
  [ "$(git rev-parse staging)" = "$before" ]
  # 其他分支不受影响
  git checkout -q topic
  run git commit -qm "feat: ok"
  [ "$status" -eq 0 ]
}
