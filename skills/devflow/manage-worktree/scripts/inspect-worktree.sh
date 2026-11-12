#!/usr/bin/env bash
# inspect-worktree.sh — 只读检测：目标目录是不是一个可以直接开工的 linked worktree。
#
# 用法：inspect-worktree.sh [--path <目录>] [--type <分支类型>] [--branch <分支名>]
#   --path    待检测目录，默认当前目录
#   --type    要开的分支类型，默认 feature（用来从 resolved.env 取基线分支）
#   --branch  要为之建 worktree 的分支名，只用来算 default_path；不给时 default_path 为空
#
# stdout 每行一个 key=value，键依次为：
#   root linked branch detached resolved integration is_integration base merge_target
#   merge_script default_path hooks reusable verdict
# resolved 是 resolved.env 的相对路径，未部署时为 missing；merge_target / merge_script 在
# resolved.env 没有这两个键（未配置合并目标）时为空。
# reusable=yes 表示除 hooks 外全部通过（可直接复用为任务工作区）。
# 每个未通过的项另起一行 reason=<代码>，代码取
#   not-root | not-linked | detached | integration-branch | hooks-missing
#
# base 取自 resolved.env 的 base.<--type>；该键不存在时为空（不退回默认分支），
# 调用方据此不新建 worktree。
#
# 退出码：0 pass / 1 fail / 2 用法错误 / 3 目标不是 git 目录（此时 verdict=n/a）/
#         4 resolved.env 不可用，只输出三行 resolved、verdict=n/a、reason：
#           reason=workflow-not-deployed  仓库未部署（resolved=missing）
#           reason=resolved-invalid       文件在但缺 integration_branches 或其值为空
#                                         （resolved=<相对路径>）
# 非 git 先于退出码 4 判断。
#
# 策略来源：两步读取 resolved.env，不解析任何规则文件、不 source 它（逐行读取）。
#   ① 引导：依次取目标工作区根、主工作树根下的 resolved.env，用第一份得到 base.<--type>
#      （没有则 base.feature，再没有则第一个集成分支，只用于定位②）；
#   ② 权威：git show <基线分支>:.hskill/init-workflow/resolved.env 的内容为准。
# 主工作树停在别的分支、或目标工作区早于部署，都不影响取值。
#
# 只读：不建、不删、不改任何 worktree、分支或配置。
# 纯 bash + git + coreutils，无外部依赖——这个脚本要在任意仓库里能跑
# （兼容 macOS 自带的 bash 3.2）。

set -uo pipefail

usage() {
  echo "用法：inspect-worktree.sh [--path <目录>] [--type <分支类型>] [--branch <分支名>]${1:+（$1）}" >&2
  exit 2
}

path="."
type="feature"
want_branch=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --path) [[ $# -ge 2 && -n "$2" ]] || usage "--path 缺少参数"; path="$2"; shift 2 ;;
    --type) [[ $# -ge 2 && -n "$2" ]] || usage "--type 缺少参数"; type="$2"; shift 2 ;;
    --branch) [[ $# -ge 2 && -n "$2" ]] || usage "--branch 缺少参数"; want_branch="$2"; shift 2 ;;
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
main_root="$(dirname "$common_dir")"   # 主工作树的根，不是当前链接 worktree 的根

# ── 当前分支；detached 时 branch 为空 ───────────────────────────────────────
branch="$(git -C "$root" symbolic-ref --short -q HEAD 2>/dev/null || true)"
if [[ -z "$branch" ]]; then detached="yes"; else detached="no"; fi

# ── resolved.env 的逐行读取：env_get <键> <文本>，键不存在返回 1 ───────────────
# 只认行首 key=value（第一个 = 切分），# 开头为注释；不 source、不 eval。
env_get() {
  local key="$1" line
  while IFS= read -r line; do
    line="${line%$'\r'}"
    case "$line" in ''|'#'*) continue ;; esac
    if [[ "${line%%=*}" == "$key" ]]; then printf '%s' "${line#*=}"; return 0; fi
  done <<< "$2"
  return 1
}

resolved_rel=".hskill/init-workflow/resolved.env"

# ── ① 引导：目标工作区根、主工作树根下第一份 resolved.env → 基线分支名 ──────────
boot=""
for dir in "$root" "$main_root"; do
  if [[ -f "$dir/$resolved_rel" ]]; then boot="$(cat "$dir/$resolved_rel")"; break; fi
done
# 定位用的分支只取自这份文件：base.<--type>，没有则 base.feature，再没有则第一个集成分支；
# 不按默认分支猜。文件在、却连集成分支都没有 → 视为无效。
invalid() {
  echo "resolved=$resolved_rel"
  echo "verdict=n/a"
  echo "reason=resolved-invalid"
  exit 4
}
boot_base=""
if [[ -n "$boot" ]]; then
  boot_base="$(env_get "base.$type" "$boot" || true)"
  [[ -z "$boot_base" ]] && boot_base="$(env_get base.feature "$boot" || true)"
  if [[ -z "$boot_base" ]]; then
    boot_int="$(env_get integration_branches "$boot" || true)"
    boot_base="${boot_int%% *}"
  fi
  [[ -z "$boot_base" ]] && invalid
fi

# ── ② 权威：基线分支上已提交的那份；取不到视为未部署 ─────────────────────────
env_text=""
if [[ -n "$boot" && -n "$boot_base" ]]; then
  env_text="$(git -C "$root" show "$boot_base:$resolved_rel" 2>/dev/null || true)"
fi
if [[ -z "$env_text" ]]; then
  echo "resolved=missing"
  echo "verdict=n/a"
  echo "reason=workflow-not-deployed"
  exit 4
fi

# ── integration / base / merge / default_path：全部来自权威那份 ───────────────
# 没有集成分支就判断不了 is_integration，整份视为无效；base.<--type> 缺失时 base 为空
# （调用方据此不新建），绝不退回默认分支。
integration="$(env_get integration_branches "$env_text" || true)"
[[ -z "${integration// /}" ]] && invalid
base="$(env_get "base.$type" "$env_text" || true)"
merge_target="$(env_get merge_target "$env_text" || true)"
merge_script="$(env_get merge_script "$env_text" || true)"
worktree_dir="$(env_get worktree_dir "$env_text" || true)"
worktree_dir="${worktree_dir:-.worktrees}"

# default_path：<主工作树根>/<worktree_dir>/<分支名，/ 换成 +>；不给 --branch 时为空
default_path=""
[[ -n "$want_branch" ]] && default_path="$main_root/$worktree_dir/${want_branch//\//+}"

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
if [[ -z "${reasons// hooks-missing/}" ]]; then reusable="yes"; else reusable="no"; fi

echo "root=$root"
echo "linked=$linked"
echo "branch=$branch"
echo "detached=$detached"
echo "resolved=$resolved_rel"
echo "integration=$integration"
echo "is_integration=$is_integration"
echo "base=$base"
echo "merge_target=$merge_target"
echo "merge_script=$merge_script"
echo "default_path=$default_path"
echo "hooks=$hooks"
echo "reusable=$reusable"
echo "verdict=$verdict"
for r in $reasons; do echo "reason=$r"; done

[[ "$verdict" == "pass" ]] && exit 0
exit 1
