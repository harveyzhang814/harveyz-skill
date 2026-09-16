#!/usr/bin/env bats
# validate-handoff.sh 的行为契约。每条对应「测试清单」里的一行。

VALIDATOR="${BATS_TEST_DIRNAME}/../scripts/validate-handoff.sh"

setup() {
  TMP="$(mktemp -d)"
  cd "$TMP" || exit 1
  # macOS 的 mktemp -d 给 /var/...，而 git rev-parse --show-toplevel 给 /private/var/...。
  # 不在这里归一，W24 那条「真实 worktree 不该 WARN」的正向对照会因为路径写法不同而假 WARN。
  TMP="$(pwd -P)"
  git init -q .
  git config user.email t@example.com
  git config user.name t
  echo x > seed.txt && git add seed.txt && git commit -qm seed
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  DOC="$TMP/2026-09-06-demo-handoff.md"
}

teardown() {
  [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"
}

# 用法：write_doc <frontmatter 正文> [正文]。不传正文时用合法的默认正文。
write_doc() {
  local fm="$1"
  local body="${2:-$(printf '# 交接：示例\n\n**交接目的**：把实现交给下一个 session\n\n## 最小验收锚点\n- demo() 返回 1\n')}"
  { printf -- '---\n%s\n---\n\n' "$fm"; printf '%s\n' "$body"; } > "$DOC"
}

VALID_FM='status: 待执行
date: 2026-09-06
author_model: opus-5
acceptance: hard'

@test "01 valid doc -> exit 0, no ERROR" {
  write_doc "$VALID_FM"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}

@test "02 missing frontmatter -> exit 1" {
  printf '# 交接：示例\n\n**交接目的**：x\n\n## 最小验收锚点\n- x\n' > "$DOC"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *frontmatter* ]]
}

@test "03 status not in enum -> exit 1 and lists legal values" {
  write_doc 'status: 完工了
date: 2026-09-06
acceptance: hard'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *status* ]]
  [[ "$output" == *待验收* ]]
}

@test "04 status absent -> exit 1" {
  write_doc 'date: 2026-09-06
acceptance: hard'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *status* ]]
}

@test "05 acceptance not hard/soft -> exit 1" {
  write_doc 'status: 待执行
date: 2026-09-06
acceptance: maybe'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *acceptance* ]]
}

@test "06 date mismatches filename -> exit 1" {
  write_doc 'status: 待执行
date: 2026-09-05
acceptance: hard'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *date* ]]
}

@test "07 branch does not exist -> exit 1" {
  write_doc "$VALID_FM
branch: feature/nope-does-not-exist"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *branch* ]]
}

@test "08 branch field absent -> exit 0 (optional)" {
  write_doc "$VALID_FM"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
}

@test "09 source_node not a uuid -> exit 1" {
  write_doc "$VALID_FM
source_node: not-a-uuid"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *source_node* ]]
}

@test "10 body missing acceptance-anchor section -> exit 1" {
  write_doc "$VALID_FM" "$(printf '# 交接：示例\n\n**交接目的**：x\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *最小验收锚点* ]]
}

@test "11 body missing handoff-purpose line -> exit 1" {
  write_doc "$VALID_FM" "$(printf '# 交接：示例\n\n## 最小验收锚点\n- x\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *交接目的* ]]
}

@test "12 body links to missing path -> exit 0 with WARN" {
  write_doc "$VALID_FM" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [规格](docs/specs/nope.md)。\n\n## 最小验收锚点\n- x\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == *nope.md* ]]
}

@test "13 three errors at once -> all reported in one run" {
  write_doc 'status: 完工了
date: 2026-09-05
acceptance: maybe'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [ "$(grep -c '^ERROR' <<< "$output")" -eq 3 ]
}

@test "14 no arg or missing file -> exit 2 + usage" {
  run bash "$VALIDATOR"
  [ "$status" -eq 2 ]
  [[ "$output" == *用法* ]]
  run bash "$VALIDATOR" "$TMP/nope.md"
  [ "$status" -eq 2 ]
}

@test "15 positive control: branch exists -> exit 0" {
  write_doc "$VALID_FM
branch: $BRANCH"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}

@test "16 positive control: link target exists -> no WARN" {
  mkdir -p docs && echo x > docs/real.md
  write_doc "$VALID_FM" "$(printf '# 交接：示例\n\n**交接目的**：x\n\n见 [规格](docs/real.md)。\n\n## 最小验收锚点\n- x\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *WARN* ]]
}

@test "17 target_node left empty for receiver to fill -> exit 0" {
  write_doc "$VALID_FM
target_node:"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}

@test "18 source_node present but empty -> exit 0" {
  write_doc "$VALID_FM
source_node:"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
}

# ── worktree 字段（验收到位线索）─────────────────────────────────────────────
# 分级依据：路径类问题一律 WARN，结构性写错才 ERROR。ERROR 的含义是「这份文档本身不合规，
# 打回原 session」；而路径是有时效的（accept 可能几天后、甚至换台机器跑），路径不在
# 不等于文档写错。

# 在 $TMP 仓库里另开一条分支的真实 worktree，回显其路径。
make_worktree() {
  git worktree add -q "$TMP/wt" -b "$1" >/dev/null 2>&1
  echo "$TMP/wt"
}

@test "19 worktree field absent -> exit 0" {
  write_doc "$VALID_FM"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *worktree* ]]
}

@test "20 worktree present but empty -> exit 0" {
  write_doc "$VALID_FM
worktree:"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}

@test "21 worktree relative path -> exit 1" {
  write_doc "$VALID_FM
worktree: ../relative/path"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *绝对路径* ]]
}

@test "22 worktree absolute but nonexistent -> exit 0 with WARN" {
  write_doc "$VALID_FM
worktree: /nonexistent/abs/path"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == */nonexistent/abs/path* ]]
}

@test "23 worktree points at a dir that is not a worktree root -> exit 0 with WARN" {
  mkdir -p "$TMP/plain"
  write_doc "$VALID_FM
worktree: $TMP/plain"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == *plain* ]]
}

# 正向对照：没有这条，22/23/25 的绿有可能来自「任何 worktree 值都 WARN」。
# 断言的是「没有 worktree 相关 WARN」，不是「整体无 WARN」——引用路径 WARN 与本次无关。
@test "24 real worktree whose HEAD branch matches branch field -> no worktree WARN" {
  wt="$(make_worktree feat/x)"
  write_doc "$VALID_FM
branch: feat/x
worktree: $wt"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *worktree* ]]
}

@test "25 real worktree whose HEAD branch differs from branch field -> WARN naming both" {
  wt="$(make_worktree feat/x)"
  write_doc "$VALID_FM
branch: $BRANCH
worktree: $wt"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == *feat/x* ]]
  [[ "$output" == *"$BRANCH"* ]]
}

@test "26 worktree without branch fallback -> exit 0 with WARN" {
  wt="$(make_worktree feat/x)"
  write_doc "$VALID_FM
worktree: $wt"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == *branch* ]]
}

@test "27 worktree relative path alongside another ERROR -> both listed, exit 1" {
  write_doc "status: 乱填
date: 2026-09-06
author_model: opus-5
acceptance: hard
worktree: ./rel"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *"status 非法值"* ]]
  [[ "$output" == *绝对路径* ]]
}

# branch 与 worktree 现在是成对的（author 建好工作区后同时填）。只填一半都要喊出来：
# 有 branch 无 worktree ⇒ author 可能没建工作区，接手方不知道去哪开工。
# 反向（有 worktree 无 branch）由 26 覆盖；两个都不填是合法的「就地同分支续做」，由 19 兜底对照。
@test "28 branch without worktree -> exit 0 with WARN" {
  write_doc "$VALID_FM
branch: $BRANCH"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" == *WARN* ]]
  [[ "$output" == *worktree* ]]
}

# ── status=待验收 时必须有接手方自测小节 ───────────────────────────────────
# 「待验收」的全部信息量是「接手方声称做完了」。接手方若没自测就推这个状态，accept 方
# 要花一整轮才发现锚点根本是红的。这条把它变成开跑前一条命令就能查出来的事。
# 只认**标题行**里的「自测」，不认正文里顺嘴提到的——散文提一句不构成一份记录。
# 其余 status 一律不受这条约束（30/31/32 是对照臂：规则确实按 status 分叉，不是恒真）。

@test "29 pending-accept status without self-test section -> exit 1" {
  write_doc 'status: 待验收
date: 2026-09-06
author_model: opus-5
acceptance: hard'
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *自测* ]]
}

@test "30 pending-accept status with self-test section -> exit 0" {
  write_doc 'status: 待验收
date: 2026-09-06
author_model: opus-5
acceptance: hard' "$(printf '# 交接：示例\n\n**交接目的**：把实现交给下一个 session\n\n## 最小验收锚点\n- demo() 返回 1\n\n## 接手方自测记录（2026-09-06）\n- demo() 返回 1 → PASS\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}

@test "31 pending-accept with selftest word in prose only -> exit 1" {
  write_doc 'status: 待验收
date: 2026-09-06
author_model: opus-5
acceptance: hard' "$(printf '# 交接：示例\n\n**交接目的**：把实现交给下一个 session\n\n我已经自测过了，没问题。\n\n## 最小验收锚点\n- demo() 返回 1\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 1 ]
  [[ "$output" == *自测* ]]
}

@test "32 todo status without self-test section -> exit 0" {
  write_doc "$VALID_FM"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *自测* ]]
}

@test "33 other statuses without self-test section -> exit 0" {
  for s in 执行中 已验收 打回; do
    write_doc "status: $s
date: 2026-09-06
author_model: opus-5
acceptance: hard"
    run bash "$VALIDATOR" "$DOC"
    [ "$status" -eq 0 ]
    [[ "$output" != *自测* ]]
  done
}

@test "34 pending-accept with rework self-test heading -> exit 0" {
  write_doc 'status: 待验收
date: 2026-09-06
author_model: opus-5
acceptance: hard' "$(printf '# 交接：示例\n\n**交接目的**：把实现交给下一个 session\n\n## 最小验收锚点\n- demo() 返回 1\n\n### 接手方复修自测记录（第 2 轮）\n- demo() 返回 1 → PASS\n')"
  run bash "$VALIDATOR" "$DOC"
  [ "$status" -eq 0 ]
  [[ "$output" != *ERROR* ]]
}
