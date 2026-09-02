#!/usr/bin/env bash
# migrate-store.sh — one-time migration into the unified storage root.
#
# Moves three things into <ROOT> (~/.hskill/config.json's knowledgeRoot):
#   <VAULT_PATH>/<hash8>/     -> <ROOT>/articles/<hash8>/   (clip-url)
#   <DATA_DIR>/tweets/        -> <ROOT>/feeds/tweets/        (sync-xtimeline)
#   <DATA_DIR>/youtube/       -> <ROOT>/feeds/youtube/       (sync-ytchannel)
#
# Default: dry-run, prints the plan, no filesystem side effects.
# --apply: actually moves files. Idempotent — safe to rerun.
#
# clip-url's VAULT_PATH is the user's Obsidian vault root and is NEVER
# mv'd wholesale — only subdirectories whose name matches ^[0-9a-f]{8}$
# AND contain a meta.json are moved; everything else (including
# hand-written notes) is left untouched and printed under "跳过".
#
# Usage: bash scripts/migrate-store.sh [--apply]

set -euo pipefail

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
fi

ok()   { printf "\033[32m✓\033[0m %s\n" "$*"; }
info() { printf "\033[2m· %s\033[0m\n"  "$*"; }
warn() { printf "\033[33m⚠\033[0m %s\n" "$*"; }

_json_get() {
  # _json_get <config-path> <key> — prints the value, exits 1 if the file
  # or key is missing (caller wraps with `|| true` under set -e).
  local path="$1" key="$2"
  [[ -f "$path" ]] || return 1
  python3 -c "
import json, sys
try:
    cfg = json.load(open(sys.argv[1], encoding='utf-8'))
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)
value = cfg.get(sys.argv[2])
if value is None:
    sys.exit(1)
print(value)
" "$path" "$key"
}

STORE_CONFIG="${HSKILL_CONFIG:-$HOME/.hskill/config.json}"
VAULT_CONFIG="${HSKILL_EXTRACT_URL_CONFIG:-$HOME/.hskill/url-extract/config.json}"
ROSTER_CONFIG="${HSKILL_ROSTER_CONFIG:-$HOME/.hskill/roster/config.json}"

ROOT="$(_json_get "$STORE_CONFIG" knowledgeRoot || true)"
if [[ -n "$ROOT" ]]; then
  ROOT="$(python3 -c "import os, sys; print(os.path.expanduser(sys.argv[1]))" "$ROOT")"
fi
if [[ -z "$ROOT" ]]; then
  warn "统一存储根未配置（$STORE_CONFIG 缺少 knowledgeRoot），无法迁移。请先跑任一入范围 skill 完成初始化。"
  exit 1
fi

echo ""
echo "统一存储契约迁移"
echo "─────────────────"
if [[ "$APPLY" -eq 1 ]]; then
  info "模式：--apply（将实际搬移文件）"
else
  info "模式：dry-run（只打印计划，不产生任何副作用；加 --apply 执行）"
fi
info "目标根：$ROOT"
echo ""

_move_dir() {
  # _move_dir <src> <dst> <label>
  local src="$1" dst="$2" label="$3"
  if [[ ! -d "$src" ]]; then
    info "${label}：源目录不存在，跳过（${src}）"
    return
  fi
  if [[ -d "$dst" ]]; then
    warn "${label}：目标已存在，跳过（${dst}）——如需重搬，先手动处理目标目录"
    return
  fi
  if [[ "$APPLY" -eq 1 ]]; then
    mkdir -p "$(dirname "$dst")"
    mv "$src" "$dst"
    ok "${label}：$src → $dst"
  else
    info "${label}：将搬 $src → $dst"
  fi
}

# ── clip-url: 只搬 <hash8>/ 且含 meta.json 的子目录 ─────────────────────
VAULT_PATH="$(_json_get "$VAULT_CONFIG" VAULT_PATH || true)"
echo "clip-url（VAULT_PATH → $ROOT/articles/）"
if [[ -z "$VAULT_PATH" ]]; then
  info "未配置 VAULT_PATH（${VAULT_CONFIG}），跳过这一项"
elif [[ ! -d "$VAULT_PATH" ]]; then
  info "VAULT_PATH 不存在（${VAULT_PATH}），跳过这一项"
else
  moved_any=0
  for entry in "$VAULT_PATH"/*/; do
    [[ -d "$entry" ]] || continue
    name="$(basename "$entry")"
    dst="$ROOT/articles/$name"
    if [[ "$name" =~ ^[0-9a-f]{8}$ && -f "${entry}meta.json" ]]; then
      moved_any=1
      if [[ -d "$dst" ]]; then
        warn "  跳过：${name}（目标已存在：${dst}）"
        continue
      fi
      if [[ "$APPLY" -eq 1 ]]; then
        mkdir -p "$ROOT/articles"
        mv "$entry" "$dst"
        ok "  $name → $dst"
      else
        info "  将搬：$name"
      fi
    elif [[ "$name" == "Origin" || "$name" == "Image" ]]; then
      info "  跳过：${name}（扁平布局遗留，由下方「vault 孤儿」一节处理）"
    else
      info "  跳过：${name}（非 8 位十六进制目录名，或无 meta.json）"
    fi
  done
  [[ "$moved_any" -eq 0 ]] && info "  没有可搬的文章目录"
fi
echo ""

# ── sync-xtimeline / sync-ytchannel: 整段 tweets/ youtube/ 搬走 ────────
DATA_DIR="$(_json_get "$ROSTER_CONFIG" DATA_DIR || true)"
echo "sync-xtimeline（DATA_DIR/tweets → $ROOT/feeds/tweets）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（${ROSTER_CONFIG}），跳过这一项"
else
  _move_dir "$DATA_DIR/tweets" "$ROOT/feeds/tweets" "sync-xtimeline"
fi
echo ""

echo "sync-ytchannel（DATA_DIR/youtube → $ROOT/feeds/youtube）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（${ROSTER_CONFIG}），跳过这一项"
else
  _move_dir "$DATA_DIR/youtube" "$ROOT/feeds/youtube" "sync-ytchannel"
fi
echo ""

# ── sync-xtimeline 旧布局（roster 化之前）逐文件并入 ───────────────────
LEGACY_X="${HSKILL_LEGACY_XTIMELINE:-$HOME/.hskill/sync-xtimeline}"
echo "sync-xtimeline 旧布局（$LEGACY_X → $ROOT/feeds/tweets）"
if [[ ! -d "$LEGACY_X" ]]; then
  info "旧目录不存在，跳过这一项"
else
  # digests/ (复数) → digest/；tweets/*.json (扁平) → creators/
  _merge_files() {
    local src="$1" dst="$2"
    [[ -d "$src" ]] || return 0
    for f in "$src"/*; do
      [[ -f "$f" ]] || continue
      local base; base="$(basename "$f")"
      if [[ -e "$dst/$base" ]]; then
        warn "  跳过：$base（目标已存在：$dst/$base）"
        continue
      fi
      if [[ "$APPLY" -eq 1 ]]; then
        mkdir -p "$dst"
        mv "$f" "$dst/$base"
        ok "  $base → $dst/"
      else
        info "  将并入：$base → $dst/"
      fi
    done
  }
  _merge_files "$LEGACY_X/digests" "$ROOT/feeds/tweets/digest"
  _merge_files "$LEGACY_X/tweets"  "$ROOT/feeds/tweets/creators"
  info "  config.json / watchlist.json / view.html 留原地（配置，非产物）"
fi
echo ""

# ── vault 顶层孤儿：扁平布局遗留，无 meta.json，不代造 ──────────────────
echo "vault 孤儿（$VAULT_PATH/{Origin,Image} → $ROOT/articles/_orphans/）"
if [[ -z "$VAULT_PATH" || ! -d "$VAULT_PATH" ]]; then
  info "VAULT_PATH 不可用，跳过这一项"
else
  for name in Origin Image; do
    _move_dir "$VAULT_PATH/$name" "$ROOT/articles/_orphans/$name" "孤儿 $name"
  done
  info "  不生成 meta.json——source_url 无从得知，造假会污染索引"
fi
echo ""

# ── 视频：vdl 已搬完，这里只补 meta.json ───────────────────────────────
echo "视频 meta.json 回填（$ROOT/videos/work/）"
VIDEO_WORK="$ROOT/videos/work"
if [[ ! -d "$VIDEO_WORK" ]]; then
  info "$VIDEO_WORK 不存在——先跑 vdl config set work-root $ROOT/videos，再回来跑本脚本"
elif [[ ! -f "$VIDEO_WORK/database.sqlite" ]]; then
  warn "缺 $VIDEO_WORK/database.sqlite，无法取 title/url，跳过这一项"
else
  APPLY="$APPLY" python3 - "$VIDEO_WORK" <<'PY'
import json, os, sqlite3, sys

work = sys.argv[1]
apply_ = os.environ.get("APPLY") == "1"
db = sqlite3.connect(os.path.join(work, "database.sqlite"))
rows = {r[0]: r for r in db.execute("select id, url, title, ts from tasks")}


def h1_title(task_id):
    """Fall back to the article's own H1 — sqlite's title column is null for
    most tasks, but any task that produced an article carries it there."""
    path = os.path.join(work, task_id, "writing", "article.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line and not line.startswith("#"):
                return None
    return None


written = skipped = 0
for task_id in sorted(os.listdir(work)):
    task_dir = os.path.join(work, task_id)
    if not os.path.isdir(task_dir):
        continue
    row = rows.get(task_id)
    title = (row[2] if row else None) or h1_title(task_id)
    if not row or not row[1] or not title:
        skipped += 1
        continue
    meta = {"source_url": row[1], "title": title, "fetched_at": (row[3] or "")[:10]}
    if apply_:
        with open(os.path.join(task_dir, "meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
    written += 1

verb = "已写入" if apply_ else "将写入"
print(f"  {verb} meta.json：{written} 个")
print(f"  跳过（无 title 或无 url，按用户决定不索引）：{skipped} 个——目录和转录稿留在磁盘上")
PY
fi
echo ""

if [[ "$APPLY" -ne 1 ]]; then
  info "以上只是计划，未产生任何文件系统改动。加 --apply 执行。"
fi
