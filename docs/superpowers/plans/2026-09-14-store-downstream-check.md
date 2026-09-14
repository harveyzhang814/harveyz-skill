# 统一存储根 · 下游漂移检测 实施计划

**目标：** 给五份 `store_config.py` 加一个只读的 `check-downstream` 子命令，核对 vdl（`vdl config get`）、scholia（`scholia config list`）当前的有效配置是否等于 `knowledgeRoot` 推出的期望值，漂移时打印可复制的修复命令；并把它接进五份 SKILL.md 的「前置：检查统一存储根」步骤。

**架构：** `knowledgeRoot` 是唯一事实依据，`check-downstream` 单向拿 `get_root()` 推出的期望路径去比对 vdl/scholia 的 CLI 输出，不解析对方的 `settings.conf` 原始文本、不写任何下游文件。命令不存在（工具未装）记 `SKIP`，值不等记 `DRIFT` 并配一行 `fix:` 命令，退出码只由 `DRIFT` 决定。

**技术栈：** Python 3（`subprocess` 调用外部 CLI）、pytest（`subprocess.run` 起子进程 + PATH 注入假可执行文件做 CLI 级测试）。

**规格依据：** `docs/superpowers/specs/2026-09-14-store-downstream-check-design.md`

---

### Task 1: 建分支与 worktree

**文件：** 无代码改动，纯仓库操作

- [ ] **Step 1: 建 worktree 与分支，基线显式写 `staging`**

```bash
git worktree add .claude/worktrees/fix+store-downstream-check -b fix/store-downstream-check staging
```

- [ ] **Step 2: 进入 worktree**

用 `EnterWorktree(path: "<repo 绝对路径>/.claude/worktrees/fix+store-downstream-check")`（`path` 模式，不用 `name`）。

- [ ] **Step 3: 设置 hooks 与合并策略**

```bash
git config core.hooksPath .githooks && git config merge.ff false
```

- [ ] **Step 4: 核对当前分支**

```bash
git rev-parse --abbrev-ref HEAD
```

预期输出：`fix/store-downstream-check`

---

### Task 2: learn-video 的 `store_config.py` 实现 `check-downstream`

**文件：**
- 修改: `skills/research/learn-video/scripts/store_config.py`
- 测试: `skills/research/learn-video/tests/test_store_config.py`

- [ ] **Step 1: 在测试文件末尾追加失败的测试**

在 `skills/research/learn-video/tests/test_store_config.py` 顶部 `SCRIPT = ...` 定义之后加一个 helper，并在文件末尾追加以下测试：

```python
def _write_fake_executable(bin_dir: Path, name: str, stdout: str) -> None:
    path = bin_dir / name
    lines = "\n".join(f"echo '{line}'" for line in stdout.splitlines())
    path.write_text(f"#!/bin/sh\n{lines}\n", encoding="utf-8")
    path.chmod(0o755)


def _run_check_downstream(config_path: Path, path_env: str):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "check-downstream"],
        env={**os.environ, "HSKILL_CONFIG": str(config_path), "PATH": path_env},
        capture_output=True, text=True, timeout=10,
    )


def test_check_downstream_all_ok(isolated_config, tmp_path):
    root = tmp_path / "root"
    _write(isolated_config, knowledgeRoot=str(root))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_executable(bin_dir, "vdl", f"workRoot: {root / 'videos'}")
    _write_fake_executable(
        bin_dir, "scholia",
        "\n".join([
            f"work-dir = {root / 'videos' / 'work'}",
            f"content-dir = {root / 'articles'}",
            f"x-dir = {root / 'feeds' / 'tweets' / 'creators'}",
        ]),
    )
    result = _run_check_downstream(isolated_config, f"{bin_dir}:{os.environ['PATH']}")
    assert result.returncode == 0
    assert "OK: vdl WORK_ROOT" in result.stdout
    assert "OK: scholia work-dir" in result.stdout
    assert "OK: scholia content-dir" in result.stdout
    assert "OK: scholia x-dir" in result.stdout
    assert "DRIFT" not in result.stdout


def test_check_downstream_reports_vdl_drift_and_fix_command(isolated_config, tmp_path):
    root = tmp_path / "root"
    _write(isolated_config, knowledgeRoot=str(root))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_executable(bin_dir, "vdl", "workRoot: /some/stale/path")
    _write_fake_executable(
        bin_dir, "scholia",
        "\n".join([
            f"work-dir = {root / 'videos' / 'work'}",
            f"content-dir = {root / 'articles'}",
            f"x-dir = {root / 'feeds' / 'tweets' / 'creators'}",
        ]),
    )
    result = _run_check_downstream(isolated_config, f"{bin_dir}:{os.environ['PATH']}")
    assert result.returncode == 1
    assert f"DRIFT: vdl WORK_ROOT=/some/stale/path (expect {root / 'videos'})" in result.stdout
    assert f"fix: vdl config set work-root {root / 'videos'}" in result.stdout


def test_check_downstream_reports_partial_scholia_drift(isolated_config, tmp_path):
    root = tmp_path / "root"
    _write(isolated_config, knowledgeRoot=str(root))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_executable(bin_dir, "vdl", f"workRoot: {root / 'videos'}")
    _write_fake_executable(
        bin_dir, "scholia",
        "\n".join([
            "work-dir = /some/stale/videos/work",
            f"content-dir = {root / 'articles'}",
            f"x-dir = {root / 'feeds' / 'tweets' / 'creators'}",
        ]),
    )
    result = _run_check_downstream(isolated_config, f"{bin_dir}:{os.environ['PATH']}")
    assert result.returncode == 1
    assert "DRIFT: scholia work-dir=/some/stale/videos/work" in result.stdout
    assert "OK: scholia content-dir" in result.stdout
    assert "OK: scholia x-dir" in result.stdout


def test_check_downstream_skips_when_tools_not_installed(isolated_config, tmp_path):
    root = tmp_path / "root"
    _write(isolated_config, knowledgeRoot=str(root))
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    result = _run_check_downstream(isolated_config, str(empty_bin))
    assert result.returncode == 0
    assert "SKIP: vdl not installed (command not found)" in result.stdout
    assert "SKIP: scholia not installed (command not found)" in result.stdout


def test_check_downstream_prints_missing_when_config_absent(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check-downstream"],
        env={**os.environ, "HSKILL_CONFIG": str(missing_path)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert result.stderr.strip().startswith("MISSING:")
```

- [ ] **Step 2: 运行测试确认失败**

运行: `cd skills/research/learn-video && python3 -m pytest tests/test_store_config.py -k check_downstream -v`
预期: 5 个新测试全部 FAIL（`check-downstream` 子命令还不存在，退出码/输出不匹配）

- [ ] **Step 3: 实现 `check-downstream`**

把 `skills/research/learn-video/scripts/store_config.py` 整份替换为：

```python
#!/usr/bin/env python3
"""统一存储根解析：读 ~/.hskill/config.json 的 knowledgeRoot 字段，为
clip-url / learn-video / sync-xtimeline / sync-ytchannel 四个 skill 提供
落盘路径。四份内容相同的副本——本仓库既定模式（browser_fetch_locate.py
就在三处各存一份）。

只做"读一个字符串再拼一层固定子目录名"，不做目录创建——各 skill 在真正
写文件时自己 mkdir -p，保持"读路径"与"建目录"分离。

支持 HSKILL_CONFIG 环境变量覆盖 config 路径，供测试注入临时根；每次调用
时读取（不在 import 时绑定），进程内 monkeypatch 才能生效。

check-downstream 子命令核对 vdl / scholia 当前配置是否等于 knowledgeRoot
推出的期望值——knowledgeRoot 是唯一事实依据，vdl/scholia 的值只是被检查
的对象，不参与仲裁。只读，不改任何下游文件；发现漂移只打印修复命令。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

_INIT_HINT = "抓取产物统一存到哪个目录？（直接回车使用默认：~/knowledge）"


def _config_path() -> Path:
    env_cfg = os.environ.get("HSKILL_CONFIG")
    return Path(env_cfg) if env_cfg else Path.home() / ".hskill" / "config.json"


def get_root() -> Path:
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} 不存在，请先完成初始化：{_INIT_HINT}")
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if "knowledgeRoot" not in cfg:
        raise KeyError(f"{config_path} 缺少 knowledgeRoot 字段，请先完成初始化：{_INIT_HINT}")
    return Path(cfg["knowledgeRoot"]).expanduser()


def articles_dir() -> Path:
    return get_root() / "articles"


def videos_dir() -> Path:
    return get_root() / "videos"


def feeds_dir(channel: str) -> Path:
    return get_root() / "feeds" / channel


def _run_downstream_command(cmd):
    """跑一个下游程序的 CLI，拿不到（未安装/非 0 退出）时返回 None。"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _check_vdl():
    output = _run_downstream_command(["vdl", "config", "get"])
    if output is None:
        return [("SKIP", "vdl not installed (command not found)")]
    actual = ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("workRoot:"):
            actual = line.split(":", 1)[1].strip()
    expected = str(videos_dir())
    if actual == expected:
        return [("OK", "vdl WORK_ROOT")]
    return [
        ("DRIFT", f"vdl WORK_ROOT={actual} (expect {expected})"),
        ("FIX", f"vdl config set work-root {expected}"),
    ]


def _check_scholia():
    output = _run_downstream_command(["scholia", "config", "list"])
    if output is None:
        return [("SKIP", "scholia not installed (command not found)")]
    actual = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        actual[key.strip()] = value.strip()
    expected = {
        "work-dir": str(videos_dir() / "work"),
        "content-dir": str(articles_dir()),
        "x-dir": str(feeds_dir("tweets") / "creators"),
    }
    results = []
    for key, exp in expected.items():
        act = actual.get(key, "")
        if act == exp:
            results.append(("OK", f"scholia {key}"))
        else:
            results.append(("DRIFT", f"scholia {key}={act} (expect {exp})"))
            results.append(("FIX", f"scholia config set {key} {exp}"))
    return results


def check_downstream() -> int:
    get_root()  # 触发 MISSING 异常，交给调用方处理
    entries = _check_vdl() + _check_scholia()
    has_drift = False
    for kind, message in entries:
        if kind == "FIX":
            print(f"  fix: {message}")
        elif kind == "DRIFT":
            has_drift = True
            print(f"DRIFT: {message}")
        else:
            print(f"{kind}: {message}")
    return 1 if has_drift else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        try:
            print(f"OK: {get_root()}")
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "check-downstream":
        try:
            sys.exit(check_downstream())
        except (FileNotFoundError, KeyError) as e:
            print(f"MISSING: {e}", file=sys.stderr)
            sys.exit(1)
        return
    print("Usage: store_config.py check|check-downstream", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

运行: `cd skills/research/learn-video && python3 -m pytest tests/test_store_config.py -v`
预期: 全部 PASS（含之前已有的用例，共 14 个）

- [ ] **Step 5: 提交**

```bash
git add skills/research/learn-video/scripts/store_config.py skills/research/learn-video/tests/test_store_config.py
git commit -m "feat(store): store_config.py 加 check-downstream 核对 vdl/scholia 是否同步"
```

---

### Task 3: 分发到其余四份 `store_config.py` / `test_store_config.py`

**文件：**
- 修改: `skills/research/clip-url/scripts/store_config.py`, `skills/research/clip-url/tests/test_store_config.py`
- 修改: `skills/feed/sync-xtimeline/scripts/store_config.py`, `skills/feed/sync-xtimeline/tests/test_store_config.py`
- 修改: `skills/feed/sync-ytchannel/scripts/store_config.py`, `skills/feed/sync-ytchannel/tests/test_store_config.py`
- 修改: `skills/feed/sync-website/scripts/store_config.py`, `skills/feed/sync-website/tests/test_store_config.py`

`store_config.py` 五份内容必须完全相同（既定约定），直接整份覆盖；测试文件除文件头部的既有 docstring/注释差异外，新增的测试函数体也完全相同，只把 Task 2 追加的那五个测试函数原样追加到每份文件末尾。

- [ ] **Step 1: 复制 `store_config.py`**

```bash
for skill in \
  skills/research/clip-url \
  skills/feed/sync-xtimeline \
  skills/feed/sync-ytchannel \
  skills/feed/sync-website; do
  cp skills/research/learn-video/scripts/store_config.py "$skill/scripts/store_config.py"
done
```

- [ ] **Step 2: 验证四份 `store_config.py` 与 learn-video 版本字节相同**

```bash
for skill in \
  skills/research/clip-url \
  skills/feed/sync-xtimeline \
  skills/feed/sync-ytchannel \
  skills/feed/sync-website; do
  diff skills/research/learn-video/scripts/store_config.py "$skill/scripts/store_config.py" && echo "OK: $skill"
done
```

预期: 四行 `OK: <path>`，无 diff 输出

- [ ] **Step 3: 把 Task 2 的五个新测试函数追加到其余四份 `tests/test_store_config.py` 末尾**

对每个 skill 的 `tests/test_store_config.py`，在文件末尾追加与 Task 2 Step 1 完全相同的五个函数（`_write_fake_executable`、`_run_check_downstream`、`test_check_downstream_all_ok`、`test_check_downstream_reports_vdl_drift_and_fix_command`、`test_check_downstream_reports_partial_scholia_drift`、`test_check_downstream_skips_when_tools_not_installed`、`test_check_downstream_prints_missing_when_config_absent`）。四份文件各自已有的 `SCRIPT` 变量、`isolated_config` fixture、`_write` helper 保持不变，不重复定义。

- [ ] **Step 4: 逐个 skill 跑测试确认通过**

```bash
cd skills/research/clip-url && python3 -m pytest tests/test_store_config.py -v
cd ../../feed/sync-xtimeline && python3 -m pytest tests/test_store_config.py -v
cd ../sync-ytchannel && python3 -m pytest tests/test_store_config.py -v
cd ../sync-website && python3 -m pytest tests/test_store_config.py -v
```

预期: 每个 skill 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add skills/research/clip-url/scripts/store_config.py skills/research/clip-url/tests/test_store_config.py \
        skills/feed/sync-xtimeline/scripts/store_config.py skills/feed/sync-xtimeline/tests/test_store_config.py \
        skills/feed/sync-ytchannel/scripts/store_config.py skills/feed/sync-ytchannel/tests/test_store_config.py \
        skills/feed/sync-website/scripts/store_config.py skills/feed/sync-website/tests/test_store_config.py
git commit -m "feat(store): check-downstream 分发到其余四份 store_config.py 副本"
```

---

### Task 4: 五份 SKILL.md 接入 `check-downstream`

**文件：**
- 修改: `skills/research/learn-video/SKILL.md`
- 修改: `skills/research/clip-url/SKILL.md`
- 修改: `skills/feed/sync-xtimeline/SKILL.md`
- 修改: `skills/feed/sync-ytchannel/SKILL.md`
- 修改: `skills/feed/sync-website/SKILL.md`

- [ ] **Step 1: learn-video —— 用 `check-downstream` 替换手写的 vdl 核对段落**

`skills/research/learn-video/SKILL.md` 原文（把这段整体替换）：

```
**再核对 vdl 的落点。** vdl 直接往统一存储根里写，所以它的 `WORK_ROOT` 必须等于 `<knowledgeRoot>/videos`：

```bash
vdl config get | grep -i work
```

不一致就提示用户运行 `vdl config set work-root <knowledgeRoot>/videos`（该命令会问是否迁移旧任务，交互式，让用户自己确认）。**不要代替用户改 `~/.config/vdl/settings.conf`**——那是另一个程序的配置文件。

这两个值存在两个不同的文件里，没有任何机制保证同步；漂了的话归档步骤会当场报错，不会静默写出孤儿 `meta.json`。
```

替换为：

```
**再核对下游是否同步。** vdl、scholia 都直接读写统一存储根，运行 `python3 scripts/store_config.py check-downstream` 核对两者当前配置是否等于 `knowledgeRoot` 推出的期望值：

```bash
python3 scripts/store_config.py check-downstream
```

输出 `DRIFT:` 时，把对应的 `fix:` 命令原样报告给用户，由用户自己决定要不要执行——**不要代替用户改 vdl/scholia 的配置文件**，那是另一个程序的配置。输出 `SKIP:` 表示该下游工具未安装，忽略即可。

这几个值分居不同文件，没有任何机制保证自动同步；漂了的话归档步骤会当场报错，不会静默写出孤儿 `meta.json`。
```

- [ ] **Step 2: clip-url —— 在既有检查段落后插入新段落**

`skills/research/clip-url/SKILL.md` 原文（在这段后面插入新段落，原文本身不改）：

```
已改由 `knowledgeRoot` 统一解析，不再读取其中的 `VAULT_PATH` 字段。
```

插入（紧跟在这句后面新起一段，位于「运行中写入失败时的处理」段落之前）：

```

**再核对下游是否同步。** 运行 `python3 scripts/store_config.py check-downstream` 核对 vdl、scholia 当前配置是否等于 `knowledgeRoot` 推出的期望值。输出 `DRIFT:` 时把对应的 `fix:` 命令原样报告给用户，由用户决定要不要执行——不要代替用户改这些下游程序的配置文件；输出 `SKIP:` 表示对应工具未安装，忽略即可。
```

- [ ] **Step 3: sync-xtimeline —— 同样插入新段落**

`skills/feed/sync-xtimeline/SKILL.md` 原文第 33 行段落结尾：

```
`$HOME` 下的普通目录（如 `~/knowledge`）不受此限制。
```

在这句所在段落后面（第 34 行空行之后、「运行中写入失败时的处理」段落之前）插入与 Step 2 相同的「再核对下游是否同步」段落。

- [ ] **Step 4: sync-ytchannel —— 同样插入新段落**

`skills/feed/sync-ytchannel/SKILL.md` 结构与 sync-xtimeline 完全一致（同一段文案），在对应位置插入同一段「再核对下游是否同步」文字。

- [ ] **Step 5: sync-website —— 同样插入新段落**

`skills/feed/sync-website/SKILL.md` 第 48 行段落结尾：

```
的普通目录（如 `~/knowledge`）不受此限制。
```

在这句所在段落后面（第 49 行空行之后、「运行中写入失败时的处理」段落之前）插入同一段「再核对下游是否同步」文字。

- [ ] **Step 6: 提交**

```bash
git add skills/research/learn-video/SKILL.md skills/research/clip-url/SKILL.md \
        skills/feed/sync-xtimeline/SKILL.md skills/feed/sync-ytchannel/SKILL.md skills/feed/sync-website/SKILL.md
git commit -m "docs(store): 五份 SKILL.md 前置检查接入 check-downstream"
```

---

### Task 5: 全量验证与合并

**文件：** 无新增文件，仅验证与合并

- [ ] **Step 1: 逐 skill 跑完整测试套件**

```bash
cd skills/research/learn-video && python3 -m pytest tests -q
cd ../clip-url && python3 -m pytest tests -q
cd ../../feed/sync-xtimeline && python3 -m pytest tests -q
cd ../sync-ytchannel && python3 -m pytest tests -q
cd ../sync-website && python3 -m pytest tests -q
```

预期: 五个 skill 全部 PASS，无 FAIL

- [ ] **Step 2: 跑仓库根 `npm test`**

运行: `npm test`（在仓库根，即 worktree 根目录）
预期: 退出码 0，SKILL.md frontmatter 校验通过（没有新增字段格式问题）

- [ ] **Step 3: 手动跑一次 `check-downstream` 验证真实环境**

```bash
python3 skills/research/learn-video/scripts/store_config.py check-downstream
```

预期: 对照当前真实 `~/.hskill/config.json`、`vdl config get`、`scholia config list` 的实际值，输出应准确反映当下是否有漂移（之前发现的 scholia 三个字段漂移应该被报出来）

- [ ] **Step 4: 等待用户确认后合并到 staging**

不在本计划自动执行——按仓库协议，回到主工作树，核对 `git rev-parse --abbrev-ref HEAD` 确实是 `staging`，再 `git merge --no-ff fix/store-downstream-check`，完成后 `git worktree remove`。
