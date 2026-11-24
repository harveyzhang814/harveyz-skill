#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ID_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
TYPES = ("surface", "feature", "entry")
KEY_ORDER = ("schema", "id", "type", "name", "aliases", "avoid", "description", "parent", "code", "versions")
VERSION_KEY_ORDER = ("introduced", "changed", "deprecated")


def find_data_dir():
    cur = Path.cwd().resolve()
    while True:
        candidate = cur / ".hskill" / "capture-feature"
        if candidate.is_dir():
            return candidate
        if (cur / ".git").exists() or cur.parent == cur:
            return None
        cur = cur.parent


def find_git_root():
    cur = Path.cwd().resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def project_root(data_dir):
    return data_dir.parent.parent


def load_all(data_dir):
    objs = {}
    fdir = data_dir / "features"
    if not fdir.is_dir():
        return objs
    for path in sorted(fdir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
            errs = _field_errors(data)
            if errs:
                raise ValueError("; ".join(e[len("error: "):] for e in errs))
            if data["id"] != path.stem:
                raise ValueError(f"id {data['id']} does not match file name")
        except (ValueError, OSError) as e:
            print(f"skip: {path.name}: {e}", file=sys.stderr)
            continue
        objs[data["id"]] = data
    return objs


def normalize(s):
    if not s:
        return ""
    s = s.replace('（', '(').replace('）', ')')
    s = s.replace('`', '')
    s = s.casefold()
    return s.strip()


def bidir_match(a, b):
    if not a or not b:
        return False
    return a in b or b in a


def match_keys(obj):
    keys = [obj.get("name", "")]
    keys += list(obj.get("aliases") or [])
    keys += [a.get("name", "") for a in (obj.get("avoid") or [])]
    return keys


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


def canonical(obj):
    """Fill defaults and order keys; assumes obj already passed field validation."""
    versions = obj.get("versions") or {}
    out = {
        "schema": obj["schema"],
        "id": obj["id"],
        "type": obj["type"],
        "name": obj["name"],
        "aliases": list(obj.get("aliases") or []),
        "avoid": [{"name": a["name"], "note": a.get("note")} for a in (obj.get("avoid") or [])],
        "description": obj["description"],
        "parent": obj["parent"],
        "code": [],
        "versions": {
            "introduced": versions["introduced"],
            "changed": [{"version": c["version"], "note": c.get("note")} for c in (versions.get("changed") or [])],
            "deprecated": versions.get("deprecated"),
        },
    }
    for c in obj.get("code") or []:
        item = {"path": c["path"]}
        if c.get("symbol") is not None:
            item["symbol"] = c["symbol"]
        out["code"].append(item)
    return out


def serialize(obj):
    return json.dumps(canonical(obj), ensure_ascii=False, indent=2) + "\n"


def _field_errors(obj):
    errs = []
    if not isinstance(obj, dict):
        return ["error: object must be a JSON object"]
    if obj.get("schema") != 1 or isinstance(obj.get("schema"), bool):
        errs.append("error: schema must be 1")
    oid = obj.get("id")
    if not isinstance(oid, str) or not ID_RE.match(oid):
        errs.append("error: id must match ^[a-z0-9]+(-[a-z0-9]+)*$")
    if obj.get("type") not in TYPES:
        errs.append("error: type must be one of surface, feature, entry")
    if not _is_str(obj.get("name")):
        errs.append("error: name must be a non-empty string")
    if not _is_str(obj.get("description")):
        errs.append("error: description must be a non-empty string")
    if "parent" not in obj:
        errs.append("error: parent is required (id or null)")
    elif obj["parent"] is not None and not isinstance(obj["parent"], str):
        errs.append("error: parent must be a string or null")
    aliases = obj.get("aliases", [])
    if not isinstance(aliases, list) or not all(_is_str(a) for a in aliases):
        errs.append("error: aliases must be a list of non-empty strings")
    avoid = obj.get("avoid", [])
    if not isinstance(avoid, list) or not all(
        isinstance(a, dict) and _is_str(a.get("name")) and (a.get("note") is None or isinstance(a.get("note"), str))
        for a in avoid
    ):
        errs.append("error: avoid must be a list of {name, note}")
    code = obj.get("code", [])
    if not isinstance(code, list) or not all(
        isinstance(c, dict) and _is_str(c.get("path")) and (c.get("symbol") is None or isinstance(c.get("symbol"), str))
        for c in code
    ):
        errs.append("error: code must be a list of {path, symbol?}")
    versions = obj.get("versions")
    if not isinstance(versions, dict) or not _is_str(versions.get("introduced")):
        errs.append("error: versions.introduced is required")
    else:
        changed = versions.get("changed", [])
        if not isinstance(changed, list) or not all(
            isinstance(c, dict) and _is_str(c.get("version")) and (c.get("note") is None or isinstance(c.get("note"), str))
            for c in changed
        ):
            errs.append("error: versions.changed must be a list of {version, note}")
        dep = versions.get("deprecated")
        if dep is not None and not isinstance(dep, str):
            errs.append("error: versions.deprecated must be a string or null")
        stamps = [("introduced", versions.get("introduced"))]
        if isinstance(dep, str):
            stamps.append(("deprecated", dep))
        if isinstance(changed, list):
            stamps += [("changed.version", c.get("version")) for c in changed if isinstance(c, dict)]
        for label, v in stamps:
            if label == "introduced" and v == "unknown":
                continue
            try:
                parse_version(v)
            except (ValueError, TypeError):
                errs.append(f"error: versions.{label} is not a parsable version: {v!r}")
    return errs


def validate(obj, all_objs, mode):
    errors = _field_errors(obj)
    warnings = []
    if errors:
        return errors, warnings
    oid = obj["id"]
    if mode == "new" and oid in all_objs:
        errors.append(f"error: id already exists: {oid}")
    if mode == "replace" and oid not in all_objs:
        errors.append(f"error: no such id to replace: {oid}")
    others = {k: v for k, v in all_objs.items() if k != oid}
    parent = obj["parent"]
    if parent is not None and parent != oid and parent not in others:
        errors.append(f"error: parent does not exist: {parent}")
    merged = dict(others)
    merged[oid] = obj
    seen = {oid}
    cur = parent
    while cur is not None:
        if cur in seen:
            errors.append(f"error: cycle through parent chain at {cur}")
            break
        seen.add(cur)
        cur = merged.get(cur, {}).get("parent")
    nname = normalize(obj["name"])
    for other in others.values():
        if normalize(other.get("name", "")) == nname:
            errors.append(f"error: name already used by {other['id']}: {obj['name']}")
    own = {normalize(k) for k in [obj["name"]] + list(obj.get("aliases") or []) + [a["name"] for a in obj.get("avoid") or []]}
    for other in others.values():
        overlap = own & {normalize(k) for k in match_keys(other)}
        for k in sorted(overlap):
            if k == nname and normalize(other.get("name", "")) == nname:
                continue
            warnings.append(f"warn: '{k}' also matches {other['id']}")
    return errors, warnings


def _chain(obj, all_objs):
    names = []
    seen = set()
    cur = obj
    while cur is not None and cur["id"] not in seen:
        seen.add(cur["id"])
        names.append(cur["name"])
        cur = all_objs.get(cur.get("parent"))
    return list(reversed(names))


def render_card(obj, all_objs):
    lines = [f"## {obj['name']}  [{obj['type']}]  id={obj['id']}", obj["description"]]
    if obj.get("aliases"):
        lines.append("别称: " + ", ".join(obj["aliases"]))
    if obj.get("avoid"):
        parts = [a["name"] + (f"（{a['note']}）" if a.get("note") else "") for a in obj["avoid"]]
        lines.append("避免: " + "；".join(parts))
    lines.append("位置: " + " > ".join(_chain(obj, all_objs)))
    children = [o["name"] for o in all_objs.values() if o.get("parent") == obj["id"]]
    if children:
        lines.append("子项: " + ", ".join(children))
    if obj.get("code"):
        lines.append("代码: " + "; ".join(c["path"] + (f"#{c['symbol']}" if c.get("symbol") else "") for c in obj["code"]))
    v = obj["versions"]
    text = f"引入 {v['introduced']}"
    if v.get("changed"):
        text += "；变更 " + "、".join(c["version"] + (f"（{c['note']}）" if c.get("note") else "") for c in v["changed"])
    text += f"；废弃 {v.get('deprecated') or '—'}"
    lines.append("版本: " + text)
    return "\n".join(lines)


def parse_version(v):
    parts = [p for p in re.split(r'\D+', v) if p]
    if not parts:
        raise ValueError(f"unparsable version: {v}")
    return tuple(int(p) for p in parts)


def exists_at(obj, version):
    target = parse_version(version)
    v = obj["versions"]
    if v["introduced"] != "unknown" and parse_version(v["introduced"]) > target:
        return False
    dep = v.get("deprecated")
    if dep and parse_version(dep) <= target:
        return False
    return True


def _strip_line_suffix(path):
    return re.sub(r':\d+$', '', path)


def classify_path(query, candidate):
    q = _strip_line_suffix(query)
    c = _strip_line_suffix(candidate)
    if q == c:
        return "same-file"
    if c.endswith('/') and q.startswith(c):
        return "dir-contains"
    if q.endswith('/') and c.startswith(q):
        return "dir-contains"
    return None


def _require_data_dir():
    data_dir = find_data_dir()
    if data_dir is None:
        print("no feature map")
        return None
    return data_dir


def cmd_show(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    if args.id not in objs:
        print(f"no such id: {args.id}")
        return 1
    print(render_card(objs[args.id], objs))
    return 0


def cmd_put(args):
    data_dir = find_data_dir()
    if data_dir is None:
        root = find_git_root()
        if root is None:
            print("no feature map")
            return 2
        data_dir = root / ".hskill" / "capture-feature"
    try:
        obj = json.loads(sys.stdin.read())
    except ValueError as e:
        print(f"error: stdin is not valid JSON: {e}")
        return 2
    objs = load_all(data_dir)
    mode = "new" if args.new else "replace"
    errors, warnings = validate(obj, objs, mode)
    if not errors and mode == "new" and (data_dir / "features" / f"{obj['id']}.json").exists():
        errors.append(f"error: features/{obj['id']}.json already exists")
    for line in errors + warnings:
        print(line)
    if errors:
        return 1
    fdir = data_dir / "features"
    fdir.mkdir(parents=True, exist_ok=True)
    target = fdir / f"{obj['id']}.json"
    tmp = fdir / f".{obj['id']}.json.tmp"
    tmp.write_text(serialize(obj), encoding="utf-8")
    os.replace(tmp, target)
    print(f"wrote features/{obj['id']}.json")
    return 0


def cmd_remove(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    if args.id not in objs:
        print(f"no such id: {args.id}")
        return 1
    children = sorted(o["id"] for o in objs.values() if o.get("parent") == args.id)
    if children:
        print("has children: " + ", ".join(children))
        return 1
    (data_dir / "features" / f"{args.id}.json").unlink(missing_ok=True)
    print(f"removed {args.id}")
    return 0


def cmd_lookup(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    query = normalize(args.term)
    hits = []
    if len(query) >= 2:
        hits = [o for o in objs.values() if any(bidir_match(normalize(k), query) for k in match_keys(o) if k)]
    if not hits:
        print(f"no match: {args.term}")
        return 1
    if len(hits) > 3:
        print(f"{len(hits)} matches: {', '.join(h['name'] for h in hits)}")
        return 0
    print("\n".join(render_card(h, objs) for h in hits))
    return 0


def cmd_tree(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    if args.id:
        if args.id not in objs:
            print(f"no such id: {args.id}")
            return 1
        starts = [objs[args.id]]
    else:
        starts = [o for o in objs.values() if o.get("parent") is None]

    def walk(o, depth, limit):
        print("  " * depth + f"{o['name']} [{o['type']}] {o['id']}")
        if depth >= limit:
            return
        for child in objs.values():
            if child.get("parent") == o["id"]:
                walk(child, depth + 1, limit)

    for o in starts:
        walk(o, 0, args.depth)
    return 0


def cmd_list(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    if args.at:
        try:
            parse_version(args.at)
            selected = [o for o in objs.values() if exists_at(o, args.at)]
        except ValueError as e:
            print(f"error: {e}")
            return 2
    else:
        selected = list(objs.values())
    for o in selected:
        if args.type and o["type"] != args.type:
            continue
        print(f"{o['id']} | {o['name']} | {o['type']} | {o.get('parent') or ''} | {','.join(o.get('aliases') or [])}")
    return 0


def cmd_refs(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    found = False
    for o in objs.values():
        for c in o.get("code") or []:
            tier = classify_path(args.path, c["path"])
            if tier:
                sym = f"#{c['symbol']}" if c.get("symbol") else ""
                print(f"{o['id']} | {o['name']} | {tier} | {c['path']}{sym}")
                found = True
    if not found:
        print(f"no refs: {args.path}")
        return 1
    return 0


def _data_dir_or_empty():
    data_dir = find_data_dir()
    if data_dir is not None:
        return data_dir
    root = find_git_root()
    if root is None:
        print("no feature map")
        return None
    return root / ".hskill" / "capture-feature"


def cmd_dupcheck(args):
    data_dir = _data_dir_or_empty()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    mine = [normalize(k) for k in [args.name] + list(args.alias or []) if normalize(k)]
    rows = []
    for o in objs.values():
        theirs = [normalize(k) for k in match_keys(o) if normalize(k)]
        if set(mine) & set(theirs):
            rows.append(f"exact | {o['id']}")
        elif any(len(m) >= 2 and len(t) >= 2 and bidir_match(m, t) for m in mine for t in theirs):
            rows.append(f"fuzzy | {o['id']}")
    vocab = project_root(data_dir) / ".hskill" / "capture-vocab" / "vocab.md"
    if vocab.is_file():
        for title in re.findall(r'^## (.+)$', vocab.read_text(encoding="utf-8"), re.MULTILINE):
            if normalize(title) in mine:
                rows.append(f"vocab | {title.strip()}")
    for row in rows:
        print(row)
    return 1 if rows else 0


def cmd_suggest_parent(args):
    data_dir = _data_dir_or_empty()
    if data_dir is None:
        return 2
    objs = load_all(data_dir)
    name = normalize(args.name)
    rank = {"same-file": 0, "dir-contains": 1, "name": 2}
    best = {}

    def offer(o, reason):
        if o["id"] not in best or rank[reason] < rank[best[o["id"]][1]]:
            best[o["id"]] = (o, reason)

    for o in objs.values():
        for path in args.path or []:
            for c in o.get("code") or []:
                tier = classify_path(path, c["path"])
                if tier:
                    offer(o, tier)
        keys = [normalize(k) for k in [o["name"]] + list(o.get("aliases") or [])]
        if any(len(k) >= 2 and k in name for k in keys):
            offer(o, "name")
    ranked = sorted(best.values(), key=lambda t: (rank[t[1]], t[0]["name"]))[:5]
    if not ranked:
        print("no candidates")
        return 1
    for o, reason in ranked:
        print(f"{o['id']} | {o['name']} | {reason}")
    return 0


def cmd_project_version(args):
    cur = Path.cwd().resolve()
    root = cur
    while True:
        if (cur / ".git").exists():
            root = cur
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            v = json.loads(pkg.read_text(encoding="utf-8")).get("version")
            if isinstance(v, str) and v:
                print(v)
                return 0
        except ValueError:
            pass
    pyp = root / "pyproject.toml"
    if pyp.is_file():
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyp.read_text(encoding="utf-8"), re.MULTILINE)
        if m:
            print(m.group(1))
            return 0
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"], cwd=root, capture_output=True, text=True
        )
        if out.returncode == 0 and out.stdout.strip():
            print(out.stdout.strip())
            return 0
    except OSError:
        pass
    print("unknown")
    return 1


def cmd_check(args):
    data_dir = _require_data_dir()
    if data_dir is None:
        return 2
    root = project_root(data_dir)
    fdir = data_dir / "features"
    problems = []
    valid = {}
    for path in sorted(fdir.glob("*.json")) if fdir.is_dir() else []:
        stem = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            problems.append(f"invalid | {stem} | {e}")
            continue
        errs = _field_errors(data)
        if errs:
            problems.append(f"invalid | {stem} | " + "; ".join(e[len('error: '):] for e in errs))
            continue
        if data["id"] != stem:
            problems.append(f"id-mismatch | {stem} | file name does not match id {data['id']}")
        valid[data["id"]] = data
    for o in valid.values():
        if o["parent"] is not None and o["parent"] not in valid:
            problems.append(f"missing-parent | {o['id']} | parent {o['parent']} does not exist")
    for o in valid.values():
        seen = {o["id"]}
        cur = o["parent"]
        while cur is not None and cur in valid:
            if cur in seen:
                if cur == o["id"]:
                    problems.append(f"cycle | {o['id']} | parent chain returns to itself")
                break
            seen.add(cur)
            cur = valid[cur]["parent"]
    by_name = {}
    for o in valid.values():
        by_name.setdefault(normalize(o["name"]), []).append(o["id"])
    for ids in by_name.values():
        for dup in ids[1:]:
            problems.append(f"duplicate-name | {dup} | same name as {ids[0]}")
    if args.code:
        for o in valid.values():
            for c in o["code"]:
                target = root / c["path"]
                if not target.exists():
                    problems.append(f"code-missing | {o['id']} | {c['path']}")
                elif c.get("symbol") and target.is_file():
                    text = target.read_text(encoding="utf-8", errors="replace")
                    if c["symbol"] not in text:
                        problems.append(f"symbol-missing | {o['id']} | {c['path']}#{c['symbol']}")
    if problems:
        print("\n".join(problems))
        return 1
    print("ok")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="feature.py")
    sub = p.add_subparsers(dest="cmd")
    sp = sub.add_parser("show")
    sp.add_argument("id")
    sp.set_defaults(fn=cmd_show)
    sp = sub.add_parser("put")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--new", action="store_true")
    g.add_argument("--replace", action="store_true")
    sp.set_defaults(fn=cmd_put)
    sp = sub.add_parser("remove")
    sp.add_argument("id")
    sp.set_defaults(fn=cmd_remove)
    sp = sub.add_parser("lookup")
    sp.add_argument("term")
    sp.set_defaults(fn=cmd_lookup)
    sp = sub.add_parser("tree")
    sp.add_argument("id", nargs="?")
    sp.add_argument("--depth", type=int, default=1)
    sp.set_defaults(fn=cmd_tree)
    sp = sub.add_parser("list")
    sp.add_argument("--type", choices=TYPES)
    sp.add_argument("--at")
    sp.set_defaults(fn=cmd_list)
    sp = sub.add_parser("refs")
    sp.add_argument("path")
    sp.set_defaults(fn=cmd_refs)
    sp = sub.add_parser("dupcheck")
    sp.add_argument("name")
    sp.add_argument("--alias", action="append")
    sp.set_defaults(fn=cmd_dupcheck)
    sp = sub.add_parser("suggest-parent")
    sp.add_argument("--name", required=True)
    sp.add_argument("--path", action="append")
    sp.set_defaults(fn=cmd_suggest_parent)
    sp = sub.add_parser("project-version")
    sp.set_defaults(fn=cmd_project_version)
    sp = sub.add_parser("check")
    sp.add_argument("--code", action="store_true")
    sp.set_defaults(fn=cmd_check)
    return p


def main(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    if not getattr(args, "fn", None):
        parser.print_usage()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
