#!/usr/bin/env bats
# 按 hook-templates.md 写明的布局与块顺序组装 commit-msg、pre-push，逐字使用模板里的块，
# 钉住：pre-push 头部/中段/尾部的切分、tag 命名与附注检查、push_guard 与 allow_direct_commit 的改写规则、
# commit-msg/format 的报错文案。

REFS="${BATS_TEST_DIRNAME}/../references"
TEMPLATE="$REFS/hook-templates.md"
ZERO=0000000000000000000000000000000000000000

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
    -e 's|<merge_script>|scripts/merge-to-staging.sh|g' \
    -e "s|'<pattern 1>' '<pattern 2>' \.\.\.|'^v[0-9]+\\\\.[0-9]+\\\\.[0-9]+\$'|" \
    -e 's|refs/heads/main\|refs/heads/staging|refs/heads/main\|refs/heads/staging|' \
    -e "s|'<pattern>'|'^(feat\|fix)(\\\\(.+\\\\))?: .+'|" \
    -e "s|<format_hint>|格式：<type>(<scope>): <描述>，type 取 feat、fix|"
}

# fixed_part <标题>：取 hook-templates.md 里“**<标题>**”后第一个 sh 代码块（固定头部/中段/尾部）
fixed_part() {
  awk -v title="$1" '
    index($0, title) && !seen { want = 1; seen = 1; next }
    want && /^```sh$/ { on = 1; next }
    on && /^```$/ { exit }
    on { print }
  ' "$TEMPLATE"
}

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  git init -q -b main repo && cd repo
  git config user.email t@example.com && git config user.name t
  echo a > a.txt && git add a.txt && git commit -qm seed
  echo b > b.txt && git add b.txt && git commit -qm second
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

# 按文档顺序组装 pre-push：头部 → merge-via → 中段 → tags → force-push → 尾部
build_pre_push() {
  {
    fixed_part '**pre-push 固定头部：**'
    extract_block 'pre-push/merge-via'
    fixed_part '**pre-push 固定中段'
    extract_block 'pre-push/tags'
    extract_block 'pre-push/force-push'
    fixed_part '**pre-push 固定尾部：**'
  } > "$TMP/pre-push"
}

push_line() { printf '%s %s %s %s\n' "$1" "$2" "$1" "$3" | sh "$TMP/pre-push"; }

@test "pre-push assembled per documented layout is valid sh" {
  build_pre_push
  run sh -n "$TMP/pre-push"
  [ "$status" -eq 0 ]
  grep -q '^while ' "$TMP/pre-push"
  grep -q 'case "$remote_ref" in' "$TMP/pre-push"
}

@test "annotated tag with a valid name is accepted" {
  build_pre_push
  git tag -a v1.0.0 -m release
  run push_line refs/tags/v1.0.0 "$(git rev-parse v1.0.0)" "$ZERO"
  [ "$status" -eq 0 ]
}

@test "lightweight tag is rejected when require_annotated" {
  build_pre_push
  git tag v1.0.1
  run push_line refs/tags/v1.0.1 "$(git rev-parse v1.0.1)" "$ZERO"
  [ "$status" -eq 1 ]
  [[ "$output" == *"git tag -a"* ]] || false
}

@test "badly named tag is rejected" {
  build_pre_push
  git tag -a release-1 -m x
  run push_line refs/tags/release-1 "$(git rev-parse release-1)" "$ZERO"
  [ "$status" -eq 1 ]
  [[ "$output" == *"Tag 命名不符合规范"* ]] || false
}

@test "deleting a tag is not checked" {
  build_pre_push
  run push_line refs/tags/whatever "$ZERO" "$(git rev-parse HEAD)"
  [ "$status" -eq 0 ]
}

@test "force push is still caught with merge-via in front of the case" {
  build_pre_push
  run push_line refs/heads/main "$(git rev-parse HEAD~1)" "$(git rev-parse HEAD)"
  [ "$status" -eq 1 ]
  [[ "$output" == *"禁止强制推送"* ]] || false
}

@test "push_guard false rule turns tag rejections into warnings" {
  build_pre_push
  # 文档规则：pre-push/tags 块内 ❌ 改 ⚠️，删去 exit 1 行
  awk '
    /BEGIN MANAGED: pre-push\/tags/ { on = 1 }
    on && /^ *exit 1$/ { next }
    on { sub(/❌/, "⚠️") }
    { print }
    /END MANAGED: pre-push\/tags/ { on = 0 }
  ' "$TMP/pre-push" > "$TMP/pre-push.guardoff" && mv "$TMP/pre-push.guardoff" "$TMP/pre-push"
  git tag bad-light
  run push_line refs/tags/bad-light "$(git rev-parse bad-light)" "$ZERO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"⚠️"* ]] || false
}

@test "commit-msg format block rejects with a concrete hint and passes conventional subjects" {
  {
    fixed_part '**commit-msg 固定头部：**'
    extract_block 'commit-msg/format'
    printf '%s\n' 'exit 0'
  } > "$TMP/commit-msg"
  run sh -n "$TMP/commit-msg"
  [ "$status" -eq 0 ]
  echo "bad commit" > "$TMP/msg"
  run sh "$TMP/commit-msg" "$TMP/msg"
  [ "$status" -eq 1 ]
  [[ "$output" == *"格式：<type>(<scope>)"* ]] || false
  [[ "$output" == *"bad commit"* ]] || false
  echo "feat(x): add thing" > "$TMP/msg"
  run sh "$TMP/commit-msg" "$TMP/msg"
  [ "$status" -eq 0 ]
}

@test "allow_direct_commit true rule lets a direct commit through with a warning" {
  {
    printf '%s\n' '#!/bin/sh' 'BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)' 'IS_MERGE=0' \
      '[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && IS_MERGE=1'
    # 文档规则：非合并分支里 ❌ 改 ⚠️、exit 1 改 exit 0
    extract_block 'branches.protected/main' | awk '
      /IS_MERGE" -eq 0/ { on = 1 }
      on { sub(/❌/, "⚠️"); sub(/exit 1/, "exit 0") }
      on && /^    fi$/ { on = 0 }
      { print }'
    printf '%s\n' 'exit 0'
  } > "$TMP/pre-commit"
  run sh "$TMP/pre-commit"
  [ "$status" -eq 0 ]
  [[ "$output" == *"⚠️"* ]] || false
}
