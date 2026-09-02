#!/usr/bin/env python3
"""Rebuild flat-layout orphan articles into proper <ROOT>/articles/<hash8>/
entities.

The pre-folder-layout version of clip-url wrote the original to
<VAULT>/Origin/<title>.md, the translation to <VAULT>/<title>.md, and images
to <VAULT>/Image/<prefix>_img_N.ext, with references written vault-relative
as `Image/<prefix>_img_N.ext`. None of that carries a meta.json, so
migrate-store.sh parks it under articles/_orphans/ untouched.

But the frontmatter does carry source_url / origin_title / fetch_date, so a
real meta.json can be derived rather than fabricated — which is the whole
reason this script is allowed to write into the index at all.

Deliberately conservative. A group is rebuilt only when it is unambiguous:

  - hash8 = md5(source_url)[:8] has no existing articles/<hash8>/ entity
  - exactly one Origin/*.md maps to that hash8

Two or more files sharing a source_url means the same article was fetched
more than once; picking a winner is a human call, so those are left alone and
reported.

Copies only. The vault is never modified.

Usage: python3 scripts/rebuild-orphan-articles.py [--apply]
"""
import hashlib
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

GREEN, YELLOW, DIM, OFF = "\033[32m", "\033[33m", "\033[2m", "\033[0m"

IMG_REF = re.compile(r"(!\[[^\]]*\]\()Image/([A-Za-z0-9_]+)_(img_[^)]+)(\))")
FRONT_KEYS = ("source_url", "origin_title", "fetch_date")


def read_frontmatter(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for i, line in enumerate(fh):
            if i > 20:
                break
            for key in FRONT_KEYS:
                if line.startswith(f"{key}:"):
                    out[key] = line.split(":", 1)[1].strip().strip('"').strip("'")
    return out


def rewrite_refs(text: str) -> tuple[str, set]:
    """`Image/<prefix>_img_2.png` (vault-relative, flat layout) becomes
    `../Image/img_2.png` (relative to Origin/ or Translation/, nested layout).
    Returns the rewritten text plus the prefixes it referenced."""
    prefixes = set()

    def sub(m):
        prefixes.add(m.group(2))
        return f"{m.group(1)}../Image/{m.group(3)}{m.group(4)}"

    return IMG_REF.sub(sub, text), prefixes


def main():
    apply_ = "--apply" in sys.argv[1:]

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                          / "skills" / "research" / "clip-url" / "scripts"))
    import store_config

    root = store_config.get_root()
    cfg_path = os.environ.get("HSKILL_EXTRACT_URL_CONFIG") or \
        str(Path.home() / ".hskill" / "url-extract" / "config.json")
    vault = Path(json.loads(Path(cfg_path).read_text(encoding="utf-8"))["VAULT_PATH"])

    origin_dir = vault / "Origin"
    if not origin_dir.is_dir():
        print(f"{DIM}· {origin_dir} 不存在，无事可做{OFF}")
        return 0

    groups = defaultdict(list)
    for path in sorted(origin_dir.glob("*.md")):
        front = read_frontmatter(path)
        url = front.get("source_url")
        if not url:
            print(f"{YELLOW}⚠{OFF} 跳过 {path.name}：frontmatter 无 source_url")
            continue
        groups[hashlib.md5(url.encode("utf-8")).hexdigest()[:8]].append((path, front))

    print(f"\n孤儿文章重建（{'--apply' if apply_ else 'dry-run'}）")
    print("─────────────────")
    print(f"{DIM}· 目标根：{root}{OFF}")
    print(f"{DIM}· 来源：{vault}{OFF}\n")

    rebuilt = skipped = 0
    for hash8, entries in sorted(groups.items()):
        dest = root / "articles" / hash8
        names = ", ".join(p.name for p, _ in entries)
        if dest.exists():
            print(f"{DIM}· 跳过 {hash8}：已是正式实体（{names}）{OFF}")
            skipped += 1
            continue
        if len(entries) > 1:
            print(f"{YELLOW}⚠{OFF} 跳过 {hash8}：{len(entries)} 个文件共用同一个 source_url，"
                  f"选哪个是人工判断")
            for p, _ in entries:
                print(f"{DIM}    - {p.name}{OFF}")
            skipped += 1
            continue

        src, front = entries[0]
        translation = vault / src.name
        origin_text, prefixes = rewrite_refs(src.read_text(encoding="utf-8"))
        pieces = [f"Origin/{src.name}"]
        if translation.is_file():
            trans_text, trans_prefixes = rewrite_refs(
                translation.read_text(encoding="utf-8"))
            prefixes |= trans_prefixes
            pieces.append(f"Translation/{src.name}")

        images = []
        for prefix in sorted(prefixes):
            for img in sorted((vault / "Image").glob(f"{prefix}_img_*")):
                images.append((img, img.name[len(prefix) + 1:]))
        if images:
            pieces.append(f"Image/ {len(images)} 张")

        print(f"{GREEN}✓{OFF} {hash8}  {front.get('origin_title', src.stem)[:48]}")
        print(f"{DIM}    {' + '.join(pieces)}{OFF}")

        if apply_:
            (dest / "Origin").mkdir(parents=True, exist_ok=True)
            (dest / "Origin" / src.name).write_text(origin_text, encoding="utf-8")
            if translation.is_file():
                (dest / "Translation").mkdir(parents=True, exist_ok=True)
                (dest / "Translation" / src.name).write_text(trans_text, encoding="utf-8")
            if images:
                (dest / "Image").mkdir(parents=True, exist_ok=True)
                for img, newname in images:
                    shutil.copyfile(img, dest / "Image" / newname)
            meta = {
                "source_url": front["source_url"],
                "title": front.get("origin_title") or src.stem,
                "fetched_at": front.get("fetch_date", ""),
            }
            (dest / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        rebuilt += 1

    verb = "已重建" if apply_ else "将重建"
    print(f"\n{verb} {rebuilt} 篇，跳过 {skipped} 组。原始文件一律保留在 {vault}。")
    if not apply_:
        print(f"{DIM}· 以上只是计划，未产生任何文件系统改动。加 --apply 执行。{OFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
