---
migrated: 2026-06-21
docs:
  - reference/hub-reference.md  # hub projects scan 命令接口与 JSON 输出
---

# hub projects scan — 设计文档

## 背景

hub 在新设备上初始化项目列表没有好的路径：`hub projects sync` 强依赖 p-launch 配置，手动 `hub projects add` 逐个注册效率低。

本次新增 `hub projects scan <dirs>` 命令，hub 自己扫描目录找 git 仓库，批量注册项目，完全不依赖 p-launch。

---

## 命令接口

```bash
hub projects scan <dir> [<dir2> ...]  [--json]
```

**示例：**
```bash
hub projects scan ~/Projects
hub projects scan ~/Projects ~/Work --json
```

---

## 扫描行为

- **扫描深度**：固定 2 层，只找 `<dir>/*/.git`，不递归
- **项目名来源**：读 `git remote get-url origin`，从 URL 解析仓库名（`github.com/user/my-repo.git` → `my-repo`）；无 remote 时兜底用目录名
- **冲突处理**：DB 中已有同名项目 → 跳过，不覆盖

---

## 架构

改动涉及 3 个文件：

```
hub/core/projects.py     ← 新增 scan_projects(dirs, db, md_path)
hub/cli/projects.py      ← 新增 scan 子命令
tools/hub/tests/test_scan.py  ← 新增测试
```

### `scan_projects(dirs, db, md_path)` — core 层

```python
def scan_projects(dirs, db, md_path=_DEFAULT_MD):
    added, skipped, failed = [], [], []
    existing = {p["name"] for p in list_projects(db)}

    for d in dirs:
        p = Path(d).expanduser()
        if not p.exists():
            failed.append({"path": str(d), "reason": "directory not found"})
            continue
        for git_dir in sorted(p.glob("*/.git")):
            repo_path = git_dir.parent
            name = _resolve_name(repo_path)  # remote URL → name，兜底目录名
            if name in existing:
                skipped.append(name)
                continue
            try:
                add_project(db, name, path=str(repo_path), md_path=md_path)
                added.append({"name": name, "path": str(repo_path)})
                existing.add(name)
            except Exception as e:
                failed.append({"path": str(repo_path), "reason": str(e)})

    return {"added": added, "skipped": skipped, "failed": failed}
```

### `_resolve_name(repo_path)` — 内部辅助

```python
def _resolve_name(repo_path):
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            return url.rstrip("/").rstrip(".git").split("/")[-1]
    except Exception:
        pass
    return repo_path.name  # 兜底
```

### CLI `scan` 子命令

```python
@app.command("scan")
def projects_scan(
    dirs: list[str] = typer.Argument(..., help="Directories to scan"),
    json_out: bool  = typer.Option(False, "--json"),
):
    """Scan directories for git repos and register them as projects."""
    db = HubDB()
    result = scan_projects(dirs, db, _md_path())
    if json_out:
        _out(result, json_out)
    else:
        for p in result["added"]:
            typer.echo(f"✓ added   {p['name']:<24} {p['path']}")
        for name in result["skipped"]:
            typer.echo(f"· skipped {name:<24} (already registered)")
        for f in result["failed"]:
            typer.echo(f"✗ failed  {f['path']}  ({f['reason']})")
        a, s, f = len(result["added"]), len(result["skipped"]), len(result["failed"])
        typer.echo(f"\nScanned: {a} added, {s} skipped, {f} failed")
```

---

## 错误处理

| 情况 | 行为 |
|------|------|
| `dir` 不存在 | 加入 `failed`，继续处理其他目录 |
| 无 `origin` remote | 兜底用目录名 |
| `git` 命令超时/失败 | 兜底用目录名 |
| 同名项目已存在 | 加入 `skipped`，不覆盖 |

---

## 输出格式

**Human：**
```
✓ added   my-repo        ~/Projects/my-repo
✓ added   another-repo   ~/Projects/another-repo
· skipped hub            (already registered)
✗ failed  /bad/path      (directory not found)

Scanned: 2 added, 1 skipped, 1 failed
```

**JSON（`--json`）：**
```json
{
  "ok": true,
  "data": {
    "added":   [{"name": "my-repo", "path": "/Users/x/Projects/my-repo"}],
    "skipped": ["hub"],
    "failed":  [{"path": "/bad/path", "reason": "directory not found"}]
  }
}
```

---

## 测试

`tests/test_scan.py`，用 `tmp_path` 构造假仓库：

| 测试 | 构造 | 断言 |
|------|------|------|
| 正常扫描 | `tmp/repo-a/.git` + `git remote add origin` | `added` 包含 `repo-a` |
| 无 remote 兜底 | `tmp/repo-b/.git`，无 origin | `added` 包含 `repo-b`（目录名） |
| 跳过已存在 | 先注册 `repo-a`，再 scan | `skipped` 包含 `repo-a` |
| 目录不存在 | `scan(["/nonexistent"])` | `failed` 有记录，不抛异常 |

---

## 不在范围内

- 递归扫描（深度 > 2）
- 更新已有项目的路径或描述
- 自动定期扫描
