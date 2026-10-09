#!/usr/bin/env bash
# 用 archify finalize 渲染并校验 OUT/specs/<id>.<type>.json → OUT/diagrams/<id>.html
# 用法: render.sh <OUT> <ARCHIFY> [--repo-root <dir>] [id ...]
# 不给 id 时渲染全部。每张图输出 PASS/FAIL；有失败时退出码 1，失败详情见 diagrams/<id>.out.json
set -u
OUT=$1 ARCHIFY=$2; shift 2
REPO=()
if [ "${1:-}" = "--repo-root" ]; then REPO=(--repo-root "$2"); shift 2; fi

cd "$OUT" || exit 1
mkdir -p diagrams
fail=0
for f in specs/*.json; do
  n=${f#specs/}; id=${n%%.*}; t=${n#*.}; t=${t%.json}
  if [ $# -gt 0 ] && [[ " $* " != *" $id "* ]]; then continue; fi
  if node "$ARCHIFY/bin/archify.mjs" finalize "$t" "$f" "diagrams/$id.html" --quality showcase --json ${REPO[@]+"${REPO[@]}"} > "diagrams/$id.out.json"; then
    echo "PASS $id"
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); m=d.get("meta",{})
if d.get("cards") or m.get("cards"): print("⚠️ "+sys.argv[2]+": cards 在嵌入模式下不显示，内容改写进正文并删掉")
if m.get("subtitle"): print("⚠️ "+sys.argv[2]+": meta.subtitle 在嵌入模式下不显示")' "$f" "$id"
  else
    echo "FAIL $id"; fail=1
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps({"stage": d.get("stage"), "error": d.get("error"), "diagnostics": d.get("diagnostics", [])[:5]}, ensure_ascii=False, indent=1))' "diagrams/$id.out.json" 2>/dev/null || head -c 2000 "diagrams/$id.out.json"
  fi
done
exit $fail
