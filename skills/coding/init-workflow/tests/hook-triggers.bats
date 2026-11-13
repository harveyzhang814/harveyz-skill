#!/usr/bin/env bats
# 回归护栏：钉住「哪些 git hook 会在合并时触发」。
# 合并脚本方案依赖这些结论（Spec 第 4 节）；任一失败说明 hook 设计需重新审查，不要改测试迁就。

setup() {
  TMP="$(mktemp -d)"; cd "$TMP" || exit 1; TMP="$(pwd -P)"
  git init -q -b main repo && cd repo
  git config user.email t@example.com && git config user.name t
  echo base > a.txt && git add a.txt && git commit -qm seed
  # seed 提交之后才启用 hook，保证日志只记录被测操作
  mkdir .h
  printf '#!/bin/sh\necho pre-commit >> "%s/log"\n' "$TMP" > .h/pre-commit
  printf '#!/bin/sh\necho commit-msg >> "%s/log"\n' "$TMP" > .h/commit-msg
  chmod +x .h/pre-commit .h/commit-msg
  git config core.hooksPath .h
  REPO="$TMP/repo"
}
teardown() { [[ -n "${TMP:-}" && "$TMP" == /*/* ]] && rm -rf "$TMP"; }

@test "clean merge --no-ff runs commit-msg but not pre-commit" {
  git checkout -q -b topic
  echo t > b.txt && git add b.txt && git commit -qm topic --no-verify
  git checkout -q main
  echo m > c.txt && git add c.txt && git commit -qm main-side --no-verify
  : > "$TMP/log"
  git merge --no-ff -q -m "merge topic" topic
  grep -q commit-msg "$TMP/log"
  run grep -c pre-commit "$TMP/log"
  [ "$output" = "0" ]
}

@test "commit-tree plus update-ref runs no hook" {
  git checkout -q -b topic
  echo t > b.txt && git add b.txt && git commit -qm topic --no-verify
  git checkout -q main
  : > "$TMP/log"
  tree="$(git rev-parse topic^{tree})"
  merge="$(git commit-tree "$tree" -p main -p topic -m "merge topic")"
  git update-ref refs/heads/main "$merge"
  [ "$(git rev-list --parents -n1 main | wc -w)" -eq 3 ]
  [ ! -s "$TMP/log" ]
}

@test "conflicted merge committed by hand runs pre-commit and commit-msg" {
  git checkout -q -b topic
  echo topic > a.txt && git commit -qam topic --no-verify
  git checkout -q main
  echo main > a.txt && git commit -qam main-side --no-verify
  : > "$TMP/log"
  run git merge --no-ff topic
  [ "$status" -ne 0 ]
  echo resolved > a.txt && git add a.txt
  git commit -q --no-edit
  grep -q pre-commit "$TMP/log"
  grep -q commit-msg "$TMP/log"
}
