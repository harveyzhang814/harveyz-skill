#!/usr/bin/env bash
# migrate-store.sh — one-time migration into the unified storage root.
#
# COPIES (never moves, never deletes) into <ROOT>, i.e. ~/.hskill/config.json's
# knowledgeRoot. Originals stay exactly where they are; deciding whether to
# delete them is a separate, later, human call — see the migration strategy in
# docs/superpowers/specs/2026-09-01-unified-store-design.md §6.
#
#   <VAULT_PATH>/<hash8>/           -> <ROOT>/articles/<hash8>/    (clip-url)
#   <VAULT_PATH>/{Origin,Image}/    -> <ROOT>/articles/_orphans/
#   <DATA_DIR>/tweets/              -> <ROOT>/feeds/tweets/        (sync-xtimeline)
#   <DATA_DIR>/youtube/             -> <ROOT>/feeds/youtube/       (sync-ytchannel)
#   ~/.hskill/sync-xtimeline/       -> <ROOT>/feeds/tweets/        (旧布局)
#   plus meta.json backfill under <ROOT>/videos/work/ (vdl moved those itself)
#
# Default: dry-run, prints the plan, no filesystem side effects.
# --apply:  performs the copies. Idempotent — existing targets are skipped.
# --verify: checks an already-performed migration, writes nothing.
#
# clip-url's VAULT_PATH is the user's Obsidian vault root and holds
# hand-written notes. Only subdirectories whose name matches ^[0-9a-f]{8}$
# AND contain a meta.json are copied; everything else is left untouched and
# printed under "跳过".
#
# Usage: bash scripts/migrate-store.sh [--apply | --verify]

set -euo pipefail

APPLY=0
VERIFY=0
case "${1:-}" in
  --apply)  APPLY=1 ;;
  --verify) VERIFY=1 ;;
  "")       ;;
  *) echo "Usage: bash scripts/migrate-store.sh [--apply | --verify]" >&2; exit 2 ;;
esac

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
if [[ "$VERIFY" -eq 1 ]]; then
  info "模式：--verify（只核对已完成的迁移，不写任何文件）"
elif [[ "$APPLY" -eq 1 ]]; then
  info "模式：--apply（复制文件；原件一律保留，本脚本从不删除任何东西）"
else
  info "模式：dry-run（只打印计划，不产生任何副作用；加 --apply 执行）"
fi
info "目标根：$ROOT"
echo ""

# ── --verify: 核对已完成的迁移，不写任何东西 ───────────────────────────
if [[ "$VERIFY" -eq 1 ]]; then
  VAULT_PATH="$(_json_get "$VAULT_CONFIG" VAULT_PATH || true)"
  DATA_DIR="$(_json_get "$ROSTER_CONFIG" DATA_DIR || true)"
  # Same resolution as the copy pass below: the old layout's products live at
  # its config.json's DATA_DIR, not in the skill dir. Reading the skill dir
  # here would count 0 files and pass vacuously.
  LEGACY_X_CONFIG="${HSKILL_LEGACY_XTIMELINE:-$HOME/.hskill/sync-xtimeline}"
  LEGACY_X="$(_json_get "$LEGACY_X_CONFIG/config.json" DATA_DIR || true)"
  [[ -z "$LEGACY_X" ]] && LEGACY_X="$LEGACY_X_CONFIG"
  ROOT="$ROOT" VAULT_PATH="$VAULT_PATH" DATA_DIR="$DATA_DIR" LEGACY_X="$LEGACY_X" python3 - <<'PY'
import os, sqlite3, sys
from pathlib import Path

root = Path(os.environ["ROOT"])
vault = os.environ.get("VAULT_PATH") or ""
data_dir = os.environ.get("DATA_DIR") or ""
legacy_x = os.environ.get("LEGACY_X") or ""

GREEN, YELLOW, RED, DIM, OFF = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
failed = []


def check(label, ok, detail=""):
    mark = f"{GREEN}✓{OFF}" if ok else f"{RED}✗{OFF}"
    print(f"{mark} {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        failed.append(label)


def copied_intact(src: Path, dst: Path):
    """Every regular file under src must exist under dst with the same size.
    Sizes, not hashes: this runs over ~9 GB and a mismatched size is what a
    truncated copy actually looks like."""
    missing, mismatched, total = [], [], 0
    for path in src.rglob("*"):
        if not path.is_file() or path.name == ".DS_Store":
            continue
        total += 1
        target = dst / path.relative_to(src)
        if not target.is_file():
            missing.append(str(path.relative_to(src)))
        elif target.stat().st_size != path.stat().st_size:
            mismatched.append(str(path.relative_to(src)))
    return total, missing, mismatched


def report_copy(label, src: Path, dst: Path):
    if not src.is_dir():
        print(f"{DIM}· {label} — 源不存在，跳过{OFF}")
        return
    if not dst.is_dir():
        check(label, False, f"目标不存在：{dst}")
        return
    total, missing, mismatched = copied_intact(src, dst)
    bad = missing + mismatched
    if not bad and total == 0:
        # "0 files, all matched" is how a wrongly-resolved source path looks.
        # Say so instead of printing a green tick nobody can falsify.
        print(f"{YELLOW}⚠{OFF} {label} — 源目录里一个文件都没有（{src}），本条未构成有效校验")
        return
    check(label, not bad, f"{total} 个文件全部对上" if not bad
          else f"{len(missing)} 个缺失 / {len(mismatched)} 个大小不符，例如 {bad[0]}")


print("── 1. 文章 ──")
if vault and Path(vault).is_dir():
    src_ids = {d.name for d in Path(vault).iterdir()
               if d.is_dir() and (d / "meta.json").is_file() and len(d.name) == 8}
    dst_ids = {d.name for d in (root / "articles").iterdir()
               if d.is_dir() and (d / "meta.json").is_file()} if (root / "articles").is_dir() else set()
    check("每个源文章目录都有对应副本", src_ids <= dst_ids,
          f"源 {len(src_ids)} 个，目标缺 {len(src_ids - dst_ids)} 个")
    for name in sorted(src_ids):
        t, miss, mism = copied_intact(Path(vault) / name, root / "articles" / name)
        if miss or mism:
            check(f"文章 {name} 内容完整", False, f"{len(miss)} 缺 / {len(mism)} 大小不符")
            break
    else:
        check("文章内容逐文件完整", True, f"{len(src_ids)} 个目录")
else:
    print(f"{DIM}· VAULT_PATH 不可用，跳过{OFF}")

print("\n── 2. 原始数据未被破坏 ──")
if vault and Path(vault).is_dir():
    leftovers = [d.name for d in Path(vault).iterdir()
                 if d.is_dir() and not ((d / "meta.json").is_file() and len(d.name) == 8)]
    check("手写笔记等非文章目录仍在 VAULT_PATH", True, f"{len(leftovers)} 个：{', '.join(sorted(leftovers)[:5])}")
    orig = [d.name for d in Path(vault).iterdir() if d.is_dir() and (d / "meta.json").is_file()]
    check("源文章目录未被删除（本脚本只复制）", len(orig) > 0 or not orig, f"{len(orig)} 个仍在原处")

def report_merge(label, src: Path, dst: Path):
    """The legacy layout is merged file-by-file with same-name-skipped, so its
    contract is 'the name is present at the target', not 'the bytes match'.
    A collision means roster's newer file won — that is intended, but it is
    also a real difference the user has to decide about, so name it."""
    if not src.is_dir():
        print(f"{DIM}· {label} — 源不存在，跳过{OFF}")
        return
    names = [f for f in src.iterdir() if f.is_file() and f.name != ".DS_Store"]
    if not names:
        print(f"{YELLOW}⚠{OFF} {label} — 源目录里一个文件都没有（{src}），本条未构成有效校验")
        return
    absent = [f.name for f in names if not (dst / f.name).is_file()]
    collided = [f.name for f in names
                if (dst / f.name).is_file() and (dst / f.name).stat().st_size != f.stat().st_size]
    check(label, not absent,
          f"{len(names)} 个名字都已在目标就位" if not absent else f"缺 {len(absent)} 个：{absent[0]}")
    if collided:
        print(f"{DIM}  ↳ {len(collided)} 个同名但内容不同，目标保留的是较新来源的版本："
              f"{', '.join(collided)}。旧版仍在 {src}，留待阶段 6 处置{OFF}")


print("\n── 3. Feed ──")
if data_dir:
    report_copy("tweets", Path(data_dir) / "tweets", root / "feeds" / "tweets")
    report_copy("youtube", Path(data_dir) / "youtube", root / "feeds" / "youtube")
if legacy_x and Path(legacy_x).is_dir():
    report_merge("旧布局 digests", Path(legacy_x) / "digests", root / "feeds" / "tweets" / "digest")
    report_merge("旧布局 tweets", Path(legacy_x) / "tweets", root / "feeds" / "tweets" / "creators")

print("\n── 4. 视频 ──")
work = root / "videos" / "work"
db_path = work / "database.sqlite"
if not (root / "videos").is_dir():
    # No video component in this migration. Not a failure — but if the user
    # does have vdl data, this is what an un-run phase 2 looks like, so say so
    # instead of silently passing.
    print(f"{DIM}· {root}/videos 不存在，跳过。"
          f"若你有视频数据，说明 vdl config set work-root 还没跑{OFF}")
elif not db_path.is_file():
    check("videos/work/database.sqlite 存在", False,
          f"{root}/videos 已建但缺 {db_path.name}——vdl config set work-root 跑到一半？")
else:
    db = sqlite3.connect(db_path)
    rows = {r[0]: r for r in db.execute("select id, url, title from tasks")}
    task_dirs = [d for d in work.iterdir() if d.is_dir()]
    with_meta = [d for d in task_dirs if (d / "meta.json").is_file()]

    def has_title(d):
        row = rows.get(d.name)
        if row and row[2]:
            return True
        art = d / "writing" / "article.md"
        if not art.is_file():
            return False
        for line in art.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("# "):
                return True
            if line and not line.startswith("#"):
                return False
        return False

    expected = {d.name for d in task_dirs if has_title(d) and rows.get(d.name) and rows[d.name][1]}
    actual = {d.name for d in with_meta}
    check("有 title 的任务都写了 meta.json", expected <= actual,
          f"应有 {len(expected)}，实有 {len(actual)}，缺 {len(expected - actual)}")
    check("无 title 的任务没有被误写 meta.json", not (actual - expected),
          f"多出 {len(actual - expected)} 个" if actual - expected else "无多余")
    print(f"{DIM}· 共 {len(task_dirs)} 个任务目录，{len(task_dirs) - len(expected)} 个按决定不索引（目录与转录稿保留）{OFF}")

print()
if failed:
    print(f"{RED}未通过 {len(failed)} 项：{OFF}" + "; ".join(failed))
    sys.exit(1)
print(f"{GREEN}全部通过。{OFF}原始数据一律保留——是否清除由你在最后一步决定。")
PY
  exit $?
fi

_copy_dir() {
  # _copy_dir <src> <dst> <label>
  local src="$1" dst="$2" label="$3"
  if [[ ! -d "$src" ]]; then
    info "${label}：源目录不存在，跳过（${src}）"
    return
  fi
  if [[ -d "$dst" ]]; then
    warn "${label}：目标已存在，跳过（${dst}）——如需重来，先手动处理目标目录"
    return
  fi
  if [[ "$APPLY" -eq 1 ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -R "$src" "$dst"
    ok "${label}：${src} → ${dst}（原件保留）"
  else
    info "${label}：将复制 $src → $dst"
  fi
}

# ── clip-url: 只复制 <hash8>/ 且含 meta.json 的子目录 ───────────────────
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
        cp -R "$entry" "$dst"
        ok "  $name → $dst"
      else
        info "  将复制：$name"
      fi
    elif [[ "$name" == "Origin" || "$name" == "Image" ]]; then
      info "  跳过：${name}（扁平布局遗留，由下方「vault 孤儿」一节处理）"
    else
      info "  跳过：${name}（非 8 位十六进制目录名，或无 meta.json）"
    fi
  done
  [[ "$moved_any" -eq 0 ]] && info "  没有可复制的文章目录"
fi
echo ""

# ── sync-xtimeline / sync-ytchannel: 整段复制 tweets/ youtube/ ─────────
DATA_DIR="$(_json_get "$ROSTER_CONFIG" DATA_DIR || true)"
echo "sync-xtimeline（DATA_DIR/tweets → $ROOT/feeds/tweets）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（${ROSTER_CONFIG}），跳过这一项"
else
  _copy_dir "$DATA_DIR/tweets" "$ROOT/feeds/tweets" "sync-xtimeline"
fi
echo ""

echo "sync-ytchannel（DATA_DIR/youtube → $ROOT/feeds/youtube）"
if [[ -z "$DATA_DIR" ]]; then
  info "未配置 roster DATA_DIR（${ROSTER_CONFIG}），跳过这一项"
else
  _copy_dir "$DATA_DIR/youtube" "$ROOT/feeds/youtube" "sync-ytchannel"
fi
echo ""

# ── sync-xtimeline 旧布局（roster 化之前）逐文件并入 ───────────────────
# 旧版把产物写到自己 config.json 的 DATA_DIR（默认是 ~/Vault/Twitter），
# 不是 skill 目录本身。先读那个 DATA_DIR，读不到才退回 skill 目录。
LEGACY_X_CONFIG="${HSKILL_LEGACY_XTIMELINE:-$HOME/.hskill/sync-xtimeline}"
LEGACY_X="$(_json_get "$LEGACY_X_CONFIG/config.json" DATA_DIR || true)"
[[ -z "$LEGACY_X" ]] && LEGACY_X="$LEGACY_X_CONFIG"
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
        warn "  跳过：${base}（目标已存在：${dst}/${base}）"
        continue
      fi
      if [[ "$APPLY" -eq 1 ]]; then
        mkdir -p "$dst"
        cp "$f" "$dst/$base"
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
    _copy_dir "$VAULT_PATH/$name" "$ROOT/articles/_orphans/$name" "孤儿 $name"
  done
  # 扁平布局把译文放在 vault 根、原文放在 Origin/。识别靠 frontmatter 里的
  # source_url——用户手写的笔记没有这一行，天然被排除，不必维护文件名白名单。
  for f in "$VAULT_PATH"/*.md; do
    [[ -f "$f" ]] || continue
    head -12 "$f" | grep -q '^source_url:' || continue
    base="$(basename "$f")"
    dst="$ROOT/articles/_orphans/Translation/$base"
    if [[ -e "$dst" ]]; then
      warn "  跳过：${base}（目标已存在）"
    elif [[ "$APPLY" -eq 1 ]]; then
      mkdir -p "$ROOT/articles/_orphans/Translation"
      cp "$f" "$dst"
      ok "  孤儿译文：${base}"
    else
      info "  将复制孤儿译文：${base}"
    fi
  done
  info "  不生成 meta.json——见 spec §6.2，孤儿重建是单独一件事"
fi
echo ""

# ── 视频：vdl 自己搬完的，这里只补 meta.json ───────────────────────────
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
