#!/usr/bin/env bash
# 造出「假的 agent-canvas-ctl / agent-canvas-arrange」加一个一次性 git 仓库与它的链接 worktree，
# 供 handoff / fork-topic 的路由 eval 使用：eval 测的是 agent 会不会走对路由流程、
# 会不会如实填 --params，不应真的去碰画布。
#
# 用法：bash setup.sh <routed|old-app|reject-once>
#   routed       路由命令全部可用
#   old-app      模拟没有路由命令的旧版 App：三个路由子命令报「未知子命令」
#   reject-once  第 1 次 create-routed-pty-node 被 INVALID_ARGUMENT 拒绝，之后放行
# 未知模式退出码 2。
#
# stdout 只打三行，后续 eval 逐行消费：
#   STUB_BIN=<桩所在目录，要放进 PATH>
#   STUB_LOG=<调用日志，每次调用追加一行 `<命令文件名> <参数逐个 printf %q>`>
#   WORKTREE=<feature/slugify-numbers 的链接 worktree>
#
# 模式不走环境变量：eval 里的 agent 不会替我们带 env，所以模式写进生成目录里的 mode 文件，
# reject-once 的「第 1 次」靠 count 文件计数。
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  routed|old-app|reject-once) ;;
  *) echo "未知模式: ${MODE:-<空>}（可选 routed|old-app|reject-once）" >&2; exit 2 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 刻意建在 jail 之外（mktemp 在 TMPDIR 下），理由同 accept-worktree/setup.sh：
# harness 会把 jail 里变化的文件当产物收集，.git 里的二进制会让 grader 调用抛异常。
# pwd -P：macOS 的 /var 是 /private/var 的软链，git worktree 记的是真实路径，两边得一致。
D="$(cd "$(mktemp -d)" && pwd -P)"
mkdir -p "$D/bin"

echo "$MODE" > "$D/mode"
echo 0 > "$D/count"
: > "$D/calls.log"
cp "$HERE/describe-develop.json" "$HERE/describe-think.json" "$D/"

# ── 桩：两个命令共用一份脚本，靠 $0 的文件名区分 ───────────────────────────
cat > "$D/bin/agent-canvas-ctl" <<'STUB'
#!/usr/bin/env bash
# 假的 agent-canvas-ctl。先记日志再应答；数据文件都在本脚本上一级目录。
D="$(cd "$(dirname "$0")/.." && pwd)"
MODE="$(cat "$D/mode")"
{
  printf '%s' "$(basename "$0")"
  for a in "$@"; do printf ' %q' "$a"; done
  printf '\n'
} >> "$D/calls.log"

SUB="${1:-}"
[ "$#" -gt 0 ] && shift

unknown() { echo "未知子命令: $SUB" >&2; exit 1; }

# 旧版 App：没有这三个路由命令
if [ "$MODE" = "old-app" ]; then
  case "$SUB" in
    list-node-route-categories|describe-node-route-category|create-routed-pty-node) unknown ;;
  esac
fi

case "$SUB" in
  whoami)
    echo '{"id":"11111111-1111-4111-8111-111111111111","title":"发起节点","kind":"pty"}' ;;
  list-node-route-categories)
    echo '{"configSource":"builtin","categories":[{"name":"develop","description":"产出是代码改动","taskType":"execute"},{"name":"think","description":"产出是结论、对比或 spec","taskType":"plan"}]}' ;;
  describe-node-route-category)
    CAT="${1:-}"
    case "$CAT" in
      develop|think) cat "$D/describe-$CAT.json" ;;
      *) echo "INVALID_ARGUMENT: 类别 \"$CAT\" 不存在。可用类别: develop（产出是代码改动）、think（产出是结论、对比或 spec）" >&2; exit 1 ;;
    esac ;;
  create-routed-pty-node)
    if [ "$MODE" = "reject-once" ]; then
      N="$(( $(cat "$D/count") + 1 ))"
      echo "$N" > "$D/count"
      if [ "$N" -eq 1 ]; then
        echo "INVALID_ARGUMENT: params 缺少字段 scale" >&2
        exit 1
      fi
    fi
    CATEGORY=""
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --category) CATEGORY="${2:-}"; shift ;;
        --category=*) CATEGORY="${1#--category=}" ;;
      esac
      shift
    done
    CATEGORY="${CATEGORY//\\/\\\\}"
    CATEGORY="${CATEGORY//\"/\\\"}"
    printf '{"nodeId":"22222222-2222-4222-8222-222222222222","startRequested":true,"routeId":"route-1","decision":{"category":"%s","final":{"nodeType":"claude-code","tier":"standard","model":"sonnet","effort":"medium"}}}\n' "$CATEGORY" ;;
  create-pty-node)
    echo '{"nodeId":"22222222-2222-4222-8222-222222222222","startRequested":true}' ;;
  link-nodes)
    echo '{"relationId":"rel-1"}' ;;
  send)
    echo '{"messageId":"msg-1","status":"queued"}' ;;
  search-nodes)
    echo '{"results":[]}' ;;
  *)
    echo '{}' ;;
esac
STUB
chmod +x "$D/bin/agent-canvas-ctl"

# arrange：任意子命令都只记日志、回 {}；复用同一份脚本即可（别的子命令都落在 *）。
cp "$D/bin/agent-canvas-ctl" "$D/bin/agent-canvas-arrange"
chmod +x "$D/bin/agent-canvas-arrange"

# ── git 仓库 + 链接 worktree：handoff eval 当作「已建好的交接工作区」────────────
REPO="$D/repo"
WT="$D/wt"
git init -q -b main "$REPO"
git -C "$REPO" config user.email eval@example.com
git -C "$REPO" config user.name eval
git -C "$REPO" config commit.gpgsign false
echo "# slugify-demo" > "$REPO/README.md"
git -C "$REPO" add -A
git -C "$REPO" commit -qm "init"

git -C "$REPO" worktree add -q "$WT" -b feature/slugify-numbers
mkdir -p "$WT/docs/superpowers/specs" "$WT/src"
cat > "$WT/docs/superpowers/specs/2026-11-11-slugify-numbers-test-plan.md" <<'PLAN'
# slugify 保留数字：测试清单

目标：`slugify(s)` 转 URL slug 时保留数字。只改 `src/slugify.js`，不改对外签名。

## 用例
- `slugify("Hello World") === "hello-world"`
- `slugify("Hello, World!") === "hello-world"`
- `slugify("Top 10 Tips") === "top-10-tips"`（保留数字）

## 验证
`node src/slugify.js` 跑上面三条，退出码 0 为全绿。
PLAN
cat > "$WT/src/slugify.js" <<'JS'
// 现状：去标点时把数字一起吃掉了，第三条用例会挂
function slugify(s) {
  return s.toLowerCase().replace(/[^a-z\s]/g, '').trim().replace(/\s+/g, '-')
}

module.exports = { slugify }
JS
git -C "$WT" add -A
git -C "$WT" commit -qm "docs: slugify numbers test plan and current implementation"

echo "STUB_BIN=$D/bin"
echo "STUB_LOG=$D/calls.log"
echo "WORKTREE=$WT"
