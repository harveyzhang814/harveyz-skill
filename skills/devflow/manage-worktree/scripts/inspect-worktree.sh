#!/usr/bin/env bash
# inspect-worktree.sh — 只读检测：目标目录是不是一个可以直接开工的 linked worktree。
#
# 用法：inspect-worktree.sh [--path <目录>] [--type <分支类型>]
#   --path  待检测目录，默认当前目录
#   --type  要开的分支类型，默认 feature（用来从规则文件里推出基线分支）
#
# stdout 每行一个 key=value，键依次为：
#   root linked branch detached rule_file integration is_integration base hooks verdict
# 每个未通过的项另起一行 reason=<代码>，代码取
#   not-root | not-linked | detached | integration-branch | hooks-missing
#
# 退出码：0 pass / 1 fail / 2 用法错误 / 3 目标不是 git 目录（此时 verdict=n/a）
#
# 只读：不建、不删、不改任何 worktree、分支或配置。
# 纯 bash + git + awk + coreutils，无外部依赖——这个脚本要在任意仓库里能跑
# （兼容 macOS 自带的 bash 3.2 与 BSD awk）。

set -uo pipefail

usage() {
  echo "用法：inspect-worktree.sh [--path <目录>] [--type <分支类型>]${1:+（$1）}" >&2
  exit 2
}

path="."
type="feature"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path) [[ $# -ge 2 && -n "$2" ]] || usage "--path 缺少参数"; path="$2"; shift 2 ;;
    --type) [[ $# -ge 2 && -n "$2" ]] || usage "--type 缺少参数"; type="$2"; shift 2 ;;
    *) usage "未知参数：$1" ;;
  esac
done

not_git() {
  echo "verdict=n/a"
  exit 3
}

# macOS 的 /var 与 /private/var 是同一处：root 与路径比较前都用 pwd -P 归一化。
real_path="$(cd "$path" 2>/dev/null && pwd -P)" || not_git
top="$(git -C "$real_path" rev-parse --show-toplevel 2>/dev/null)" || not_git
root="$(cd "$top" && pwd -P)" || not_git

# ── linked：独立 git dir 与公共 git dir 不同即为 linked worktree ─────────────
git_dir="$(cd "$root" && cd "$(git rev-parse --absolute-git-dir)" && pwd -P)"
common_dir="$(cd "$root" && cd "$(git rev-parse --git-common-dir)" && pwd -P)"
if [[ "$git_dir" != "$common_dir" ]]; then linked="yes"; else linked="no"; fi

# ── 当前分支；detached 时 branch 为空 ───────────────────────────────────────
branch="$(git -C "$root" symbolic-ref --short -q HEAD 2>/dev/null || true)"
if [[ -z "$branch" ]]; then detached="yes"; else detached="no"; fi

# ── 默认分支：origin/HEAD 指向的分支，否则依次取存在的 main、master，都没有则为空 ──
default_branch=""
origin_head="$(git -C "$root" symbolic-ref -q refs/remotes/origin/HEAD 2>/dev/null || true)"
if [[ -n "$origin_head" ]]; then
  default_branch="${origin_head#refs/remotes/origin/}"
else
  for cand in main master; do
    if git -C "$root" show-ref --verify --quiet "refs/heads/$cand"; then
      default_branch="$cand"
      break
    fi
  done
fi

# ── 规则文件：按顺序取第一个存在的 ──────────────────────────────────────────
rule_file="none"
for cand in .hskill/init-workflow/workflow-config.yml workflow-config.yml .claude/workflow-config.yml; do
  if [[ -f "$root/$cand" ]]; then rule_file="$cand"; break; fi
done

# 按缩进解析 branches: → protected: 下的 "- name:" 与其后的 merge_from 列表。
# 只认条目这一层的 name / merge_from 键（iind 为条目短横线的缩进，kind 为条目内键的缩进），
# 条目下更深层的 name:（如 reviewers 列表）不当作分支名。
# mode=names 逐行输出受保护分支名；mode=base 输出第一个 merge_from 含 <type>/* 的分支名。
parse_rules() { # parse_rules <names|base> <文件>
  awk -v mode="$1" -v want="$type/*" '
    function clean(s) {
      sub(/\r$/, "", s)
      sub(/[ \t]+#.*$/, "", s)
      sub(/^[ \t]+/, "", s)
      sub(/[ \t]+$/, "", s)
      gsub(/"/, "", s)
      gsub(/\047/, "", s)
      return s
    }
    function item(v) {
      if (mode == "base" && !done && cur != "" && v == want) { print cur; done = 1 }
    }
    {
      line = $0
      sub(/\r$/, "", line)
      if (line ~ /^[ \t]*(#|$)/) next
      match(line, /^[ \t]*/); ind = RLENGTH
      text = substr(line, ind + 1)
      if (ind == 0 && text !~ /^-/) {
        inb = (text ~ /^branches:/); inprot = 0; inmf = 0
        next
      }
      if (!inb) next
      if (!inprot) {
        if (text ~ /^protected:/) { inprot = 1; pind = ind; iind = -1; kind = -1 }
        next
      }
      if (ind <= pind && text !~ /^-/) { inprot = 0; inmf = 0; next }
      if (text ~ /^-/ && (iind < 0 || ind == iind)) {   # 新的受保护分支条目
        iind = ind
        match(text, /^-[ \t]*/)
        kind = ind + RLENGTH
        text = substr(text, RLENGTH + 1)
        ind = kind; cur = ""; inmf = 0
      }
      if (ind == kind && text ~ /^name:/) {
        sub(/^name:/, "", text)
        cur = clean(text); inmf = 0
        if (mode == "names" && cur != "") print cur
        next
      }
      if (ind == kind && text ~ /^merge_from:/) {
        sub(/^merge_from:/, "", text)
        text = clean(text)
        if (text ~ /^\[.*\]$/) {            # 行内写法 [a, "b/*"]
          inmf = 0
          text = substr(text, 2, length(text) - 2)
          n = split(text, parts, ",")
          for (i = 1; i <= n; i++) item(clean(parts[i]))
        } else {
          inmf = 1
        }
        next
      }
      if (inmf && text ~ /^-/) {
        sub(/^-[ \t]*/, "", text)
        item(clean(text))
        next
      }
      inmf = 0
    }
  ' "$2"
}

# ── integration / base ─────────────────────────────────────────────────────
integration=""
base=""
if [[ "$rule_file" != "none" ]]; then
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    integration="${integration:+$integration }$name"
  done < <(parse_rules names "$root/$rule_file")
  base="$(parse_rules base "$root/$rule_file" | head -1)"
fi
# 没有规则文件（或规则文件里解析不出受保护分支）时，保守地把默认分支当作集成分支
[[ -z "$integration" ]] && integration="$default_branch"
[[ -z "$base" ]] && base="$default_branch"

is_integration="no"
if [[ -n "$branch" ]]; then
  for name in $integration; do
    [[ "$name" == "$branch" ]] && is_integration="yes"
  done
fi

# ── hooks：有 .githooks/ 目录时，core.hooksPath 须指向它 ─────────────────────
# 相对路径按 git 的规则相对工作区根解析；写成 ./.githooks/、本工作区或主工作树下
# .githooks 的绝对路径，都算指向它。
hooks="n/a"
if [[ -d "$root/.githooks" ]]; then
  hooks="missing"
  hp="$(git -C "$root" config --type=path --get core.hooksPath 2>/dev/null || true)"
  if [[ -n "$hp" ]]; then
    [[ "$hp" != /* ]] && hp="$root/$hp"
    hp_real="$(cd "$hp" 2>/dev/null && pwd -P || true)"
    main_root="$(dirname "$common_dir")"
    if [[ -n "$hp_real" && ( "$hp_real" == "$root/.githooks" || "$hp_real" == "$main_root/.githooks" ) ]]; then
      hooks="ok"
    fi
  fi
fi

# ── 判定 ───────────────────────────────────────────────────────────────────
reasons=""
[[ "$real_path" != "$root" ]] && reasons="$reasons not-root"
[[ "$linked" != "yes" ]] && reasons="$reasons not-linked"
[[ "$detached" == "yes" ]] && reasons="$reasons detached"
[[ "$is_integration" == "yes" ]] && reasons="$reasons integration-branch"
[[ "$hooks" == "missing" ]] && reasons="$reasons hooks-missing"

if [[ -z "$reasons" ]]; then verdict="pass"; else verdict="fail"; fi

echo "root=$root"
echo "linked=$linked"
echo "branch=$branch"
echo "detached=$detached"
echo "rule_file=$rule_file"
echo "integration=$integration"
echo "is_integration=$is_integration"
echo "base=$base"
echo "hooks=$hooks"
echo "verdict=$verdict"
for r in $reasons; do echo "reason=$r"; done

[[ "$verdict" == "pass" ]] && exit 0
exit 1
