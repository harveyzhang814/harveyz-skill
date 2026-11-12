#!/usr/bin/env bash
# merge-worktree.sh —「合并」：把当前链接 worktree 的分支，经仓库部署的标准合并脚本并入合并目标。
#
# 用法：merge-worktree.sh        无参数，作用于当前目录
#
# 步骤：
#   ① 对当前目录跑 inspect-worktree.sh（同目录）
#   ② 读 merge_target / merge_script
#   ③ 检查 <工作区根>/<merge_script> 存在且可执行
#   ④ 在工作区根执行该脚本，输出与退出码原样透传
#
# 退出码：
#   0 / 1 / 2  透传合并脚本：0 已合并或已包含；1 出错（含 pre_checks 未过）；2 冲突，标记已落在当前工作区
#   3  当前目录不是 git 目录（带参数调用的用法错误按 1 处理，避免与冲突的 2 混淆）
#   4  仓库未部署 resolved.env（先部署 init-workflow）
#   5  工作区检测未通过（不是链接 worktree 的根目录含子目录、detached HEAD、处于集成分支）
#   6  本仓库未配置合并目标
#   7  本工作区缺合并脚本（本分支早于部署）；不退回 git merge
#
# 不 push，不移除 worktree，不删除分支。检测的 hooks-missing 不影响合并（合并脚本不依赖 hooks），
# 只有 reusable=yes 以外的项（not-root / not-linked / detached / integration-branch）才拒绝。
# 纯 bash + git，兼容 macOS 自带的 bash 3.2。

set -uo pipefail

if [[ $# -gt 0 ]]; then
  echo "用法：merge-worktree.sh（无参数，作用于当前目录）" >&2
  exit 1
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# ── ① 检测 ──────────────────────────────────────────────────────────────────
out="$(bash "$here/inspect-worktree.sh" --path .)"
rc=$?

case "$rc" in
  0|1) ;;
  3)
    echo "当前目录不是 git 目录，无法「合并」。" >&2
    exit 3
    ;;
  4)
    echo "该仓库的集成分支尚未部署新版 init-workflow（缺 .hskill/init-workflow/resolved.env），不「合并」。" >&2
    echo "请先在仓库里运行 init-workflow 部署，再重来。" >&2
    exit 4
    ;;
  *)
    echo "检测脚本异常退出（退出码 ${rc}），不「合并」。" >&2
    exit 1
    ;;
esac

# 逐行读 inspect 输出：out_get <键>，第一个 = 切分，键不存在时输出空串
out_get() {
  local line
  while IFS= read -r line; do
    if [[ "${line%%=*}" == "$1" ]]; then printf '%s' "${line#*=}"; return 0; fi
  done <<< "$out"
  return 0
}

reusable="$(out_get reusable)"
if [[ "$reusable" != "yes" ]]; then
  echo "当前目录不能「合并」：需在链接 worktree 的根目录、处于命名分支、且不是集成分支。未通过项：" >&2
  while IFS= read -r line; do
    case "$line" in reason=hooks-missing) ;; reason=*) echo "  ${line#reason=}" >&2 ;; esac
  done <<< "$out"
  exit 5
fi

# ── ② 合并目标 ───────────────────────────────────────────────────────────────
root="$(out_get root)"
merge_target="$(out_get merge_target)"
merge_script="$(out_get merge_script)"
if [[ -z "$merge_target" || -z "$merge_script" ]]; then
  echo "本仓库未配置合并目标，不「合并」。" >&2
  exit 6
fi

# ── ③ 本工作区里的合并脚本 ───────────────────────────────────────────────────
if [[ ! -f "$root/$merge_script" || ! -x "$root/$merge_script" ]]; then
  echo "本工作区缺合并脚本 ${merge_script}（或不可执行），本分支应早于部署。" >&2
  echo "先把 ${merge_target} 并入本分支再「合并」；本技能不退回 git merge。" >&2
  exit 7
fi

# ── ④ 在工作区根执行，透传输出与退出码 ───────────────────────────────────────
cd "$root" || exit 1
"./$merge_script"
exit $?
