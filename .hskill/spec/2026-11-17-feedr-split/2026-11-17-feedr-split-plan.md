# feedr 拆分 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 superpowers:subagent-driven-development 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** 把 harveyz-skill 的 browser-fetch、roster 和三个 sync-* 的追更编排合并为独立产品 feedr（`~/Projects/feedr`），并把 harveyz-skill 的调用方切到 `feedr`，对用户可见的行为不变。

**Architecture:** feedr 是单个 Python 包，提供单个 CLI，包含 `fetch`、`roster`、`sync`、`init`、`config` 五组命令：
- `sync` 在进程内调用 `fetch` 与 `roster`，平台差异集中在适配器里。
- 两段式 `sync fetch` / `sync commit` 沿用旧脚本的报告与存档格式，用旧脚本预先生成的标准结果（golden files）对照验证。
- harveyz-skill 侧删除各 skill 中的脚本副本，改为调用 `feedr`，然后移除 `tools/browser-fetch`、`tools/roster`。

**Tech Stack:** Python ≥3.11、hatchling、argparse、playwright、pycookiecheat、pytest、pytest-asyncio、uv；harveyz-skill 侧为 bats、node:test。

**Spec:** `.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-spec.md`

**Spec Version and Scope:** v0.1，已批准；范围为全文，含次要决定 S1–S15；未决事项 D21–D23 不在范围内。

## Global Constraints

- 包名、CLI 命令名：`feedr`；版本 `0.1.0`；`requires-python = ">=3.11"`；运行时依赖只有 `playwright>=1.45`、`pycookiecheat>=0.7`；dev 依赖 `pytest>=8.0`、`pytest-asyncio>=0.23`；`asyncio_mode = "auto"`。
- 两个仓库的位置与分支：
  - feedr 仓库：`/Users/harveyzhang96/Projects/feedr`，全新 `git init`，不导入 harveyz-skill 历史。首个提交（仅 `.gitignore`）落在 `main`，其余工作都在 `feature/initial-split` 上。
  - harveyz-skill 侧：在 `/Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+feedr-split`（分支 `feature/feedr-split`）中修改。
- **stdout 输出：** JSON 一律为单行紧凑格式，写法是 `json.dump(payload, sys.stdout, ensure_ascii=False, separators=(",", ":"))` 加换行。原 roster 中非 JSON 的输出（`OK ...`、`EMPTY` 等）原样保留。
- **退出码：** 0 成功，2 用法错误，1 运行时失败。
- **固定的 stderr 首行标记：**
  - `NOT_INITIALIZED: run \`feedr init\``
  - `MISSING_ARCHIVE_ROOT`
  - `MISSING_ROSTER_DIR`
- **环境变量：** 只识别 `FEEDR_HOME`（默认 `~/.feedr`）和 `FEEDR_CHROME_BASE`（默认 `~/Library/Application Support/Google/Chrome`）。不识别 `BROWSER_FETCH_DATA_DIR`、`BROWSER_FETCH_CHROME_BASE`、`HSKILL_ROSTER_CONFIG`。
- **旧数据位置：** 一律用 `Path.home() / ".hskill"` 推导，测试通过 monkeypatch `HOME` 隔离。feedr 的任何代码路径都不得写入或删除 `~/.hskill` 下的文件。
- **存档格式：** 存档文件写法为 `json.dumps(items, indent=2, ensure_ascii=False)`，路径为 `<archive_root>/feeds/{tweets,youtube,website}/creators/<handle>.json`，与旧 `archive_*.py` 逐字节一致。
- **install 提示文案**（skill 侧统一使用）：`feedr 未安装：uv tool install git+https://github.com/harveyzhang96/feedr && feedr fetch install-browser`
- harveyz-skill 的提交遵循仓库 hooks（`docs/reference/git-workflow.md`），提交信息末尾带 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- `docs/`、`.hskill/spec/` 下的历史文档、`CHANGELOG.md` 的历史条目、`scripts/migrate-store.sh` 及其测试 `tests/migrate-store.bats` 都不修改（S14）。

- **执行顺序：** Task 8–13 都会改 `skills-index.json`，必须按编号顺序串行执行，不能并行。
- **真实数据：** Task 14 之前，不得在真实 `HOME` 下执行 `feedr init` 或任何需要浏览器数据的 `feedr fetch`；测试一律设置临时的 `FEEDR_HOME` 和 `HOME`。

## Review Focus

- `~/.feedr/browser/` 复制到一半失败（S13）→ 最终路径下不能留下半成品：先复制到同级临时目录，成功后再 `rename`；失败时删除临时目录，退出码 1。（Task 1）
- `sync commit` 写存档时出错（比如目标目录不可写）→ 游标保持原值，退出码 1。（Task 5）
- `sync` 缺少 `archive_root` → 任何渠道的抓取函数都不被调用，测试断言打桩的抓取函数调用次数为 0。（Task 5）
- 旧 `DATA_DIR` 位于 `~/.hskill` 之外 → init 不复制，`roster_dir` 指向原路径，原路径内容不变。（Task 2）
- X 时间线带置顶旧推文时建立基线 → 基线取 id 最大的那条，由 golden 场景 `x/baseline_pinned` 覆盖。（Task 4、Task 5）

---

### Task 1: feedr 仓库脚手架与 `feedr fetch` 命令组

**Prerequisites:** 无

**Files:**
- Create: `~/Projects/feedr/{.gitignore,pyproject.toml,README.md}`
- Create: `~/Projects/feedr/feedr/__init__.py`（`__version__ = "0.1.0"`）
- Create: `~/Projects/feedr/feedr/paths.py`
- Create: `~/Projects/feedr/feedr/cli.py`（顶层解析器，本任务只挂 `fetch`）
- Create: `~/Projects/feedr/feedr/fetch/`：由 `tools/browser-fetch/browser_fetch/*.py` 复制而来，包名改为 `feedr.fetch`；原 `cli.py` 改为 `feedr/fetch/cli.py`，提供 `register(subparsers)`
- Create: `~/Projects/feedr/tests/fetch/`：由 `tools/browser-fetch/tests/*.py` 复制而来，导入路径改为 `feedr.fetch`
- Test: `~/Projects/feedr/tests/test_paths.py`

**Interfaces:**
- Produces，在 `feedr/paths.py` 中：
  - `feedr_home() -> Path`
  - `config_path() -> Path`
  - `load_config() -> dict`（文件不存在时返回 `{}`）
  - `write_config(cfg: dict) -> None`
  - `class NotInitialized(Exception)`
  - `require_initialized() -> dict`
  - `hskill_home() -> Path`
  - `browser_dir() -> Path`：实现 S13，首次调用时迁移，返回的目录权限为 0700
- Produces：`feedr.cli.main(argv: list[str] | None = None) -> int`；`pyproject.toml` 中 `[project.scripts] feedr = "feedr.cli:main"`
- Produces：`feedr fetch install-browser`，执行 `sys.executable -m playwright install chromium`，结束后输出 `{"status":"ok"}`

- [ ] **Step 1：** 在 `/Users/harveyzhang96/Projects/feedr` 执行 `git init -b main`，写 `.gitignore`（`.venv/`、`__pycache__/`、`.pytest_cache/`、`dist/`），提交 `chore: init repo`，然后执行 `git switch -c feature/initial-split`。
- [ ] **Step 2：编写失败测试 `tests/test_paths.py`**
  - `test_feedr_home_respects_env`：设置 `FEEDR_HOME=tmp/fh`，断言 `feedr_home() == tmp/fh`。
  - `test_load_config_missing_returns_empty`：配置文件不存在时，断言返回 `{}`。
  - `test_require_initialized_raises_without_config`：没有配置文件时，抛出 `NotInitialized`。
  - `test_browser_dir_copies_legacy_contexts`：在 `HOME/.hskill/browser-fetch/contexts/` 下建 `config.json` 和 `site_rules/a.com/rule.json`。调用后，`browser_dir()/config.json` 内容与原文件相同，源目录的文件列表和内容都不变，`oct(stat.st_mode & 0o777) == '0o700'`。
  - `test_browser_dir_creates_empty_without_legacy`：没有旧目录时，返回一个已存在的空目录。
  - `test_browser_dir_partial_copy_leaves_no_target`：monkeypatch `shutil.copytree` 让它抛出 `OSError`。断言抛出异常，`feedr_home()/"browser"` 不存在，`feedr_home()` 下没有残留的临时目录。
  - `test_browser_dir_existing_is_untouched`：`browser/` 已存在时，不从旧目录复制，用 marker 文件验证。
- [ ] **Step 3：** 运行 `pytest tests/test_paths.py -v`。Expected：FAIL（`ModuleNotFoundError: feedr`）。
- [ ] **Step 4：实现 `feedr/paths.py`、`pyproject.toml` 和 `feedr/__init__.py`**
  - `browser_dir()` 先复制到 `feedr_home()/".browser.tmp-<pid>"`，再 `os.rename` 到最终路径。
  - 迁移时在 stderr 打印一行：`feedr: 已从 <src> 复制浏览器数据到 <dst>`。
- [ ] **Step 5：迁入 browser-fetch 代码与测试**
  - 复制 `browser_fetch/*.py` 到 `feedr/fetch/`，全局替换 `browser_fetch` → `feedr.fetch`。
  - `core._data_dir()` 改为返回 `paths.browser_dir()`。
  - `profiles.py` 中的 `BROWSER_FETCH_CHROME_BASE` 改名为 `FEEDR_CHROME_BASE`。
  - 测试中的 `BROWSER_FETCH_DATA_DIR` 一律改为设置 `FEEDR_HOME`，并通过 `browser_dir()` 取得路径。
  - 不迁移 `test_launcher_stdout_contract.py`、`test_launcher_python_version.py`、`test_data_dir_migration.py`（启动脚本已取消，S11），把这三个文件名写进 README 的「迁移说明」。
- [ ] **Step 6：** 实现 `feedr/cli.py` 与 `feedr/fetch/cli.py`：`feedr fetch <原 9 个子命令>` 的参数与输出和原来一致；新增 `install-browser`；提供 `feedr --version`。顶层 `prog="feedr"`。原 `test_cli*.py` 中的 `prog` 和入口改为 `feedr.cli.main(["fetch", ...])`。
- [ ] **Step 7：** 运行 `uv venv && uv pip install -e '.[dev]' && .venv/bin/python -m playwright install chromium && .venv/bin/pytest -q`。Expected：全部 PASS。
- [ ] **Step 8：** 提交 `feat: fetch command group migrated from browser-fetch`。

### Task 2: `feedr init` 与 `feedr config`

**Prerequisites:** Task 1

**Files:**
- Create: `~/Projects/feedr/feedr/init_cmd.py`
- Create: `~/Projects/feedr/feedr/config_cmd.py`
- Modify: `~/Projects/feedr/feedr/cli.py`（挂上 `init`、`config`）
- Test: `~/Projects/feedr/tests/test_init.py`、`~/Projects/feedr/tests/test_config_cmd.py`

**Interfaces:**
- Consumes：Task 1 的 `paths.*`
- Produces：`init_cmd.run(roster_dir: str | None, archive_root: str | None) -> tuple[int, dict]`，返回值为退出码和 stdout 的 payload
  - 成功：`{"status":"INITIALIZED","config":{...},"items":[{"item":"browser"|"roster"|"archive_root","source":str|None,"target":str|None,"action":"copied"|"kept"|"created"|"from_arg"|"from_knowledgeRoot"|"missing"}]}`
  - 已初始化：`{"status":"ALREADY_INITIALIZED","config":{...}}`，退出码 0
- Produces：`feedr config show` 打印配置 JSON，未初始化时打印 `{}`；`feedr config set archive-root <path>` 只改 `archive_root` 这一个键，存储时 `expanduser` 后写绝对路径，未初始化时退出码 1 并输出 `NOT_INITIALIZED`

- [ ] **Step 1：编写失败测试 `tests/test_init.py`**，每个测试结束时都断言伪造的 `HOME/.hskill` 下文件集合和内容的快照没有变化。
  - `test_init_already_initialized_changes_nothing`
  - `test_init_roster_dir_arg_wins`：同时存在 `--roster-dir` 和旧 `DATA_DIR` 时，以参数为准，不复制旧数据。
  - `test_init_copies_roster_under_hskill`：`DATA_DIR=HOME/.hskill/roster`，执行后 `roster_dir == FEEDR_HOME/roster`，`registry.json` 内容一致。
  - `test_init_keeps_roster_outside_hskill`：`DATA_DIR=tmp/vault/roster`，执行后 `roster_dir` 等于该路径，`FEEDR_HOME/roster` 不存在。
  - `test_init_missing_roster_dir_exit2`：退出码 2，stderr 首行为 `MISSING_ROSTER_DIR`，不生成 `config.json`。
  - `test_init_archive_root_from_arg`
  - `test_init_archive_root_from_knowledgeRoot`
  - `test_init_archive_root_missing_omits_key`：`"archive_root" not in config`，退出码 0。
  - `test_init_copy_failure_writes_no_config`：复制 roster 时打桩 `OSError`，退出码 1，不生成 `config.json`。
  - `test_init_migrates_browser_via_paths`：`items` 中 `browser` 一项的 `action == "copied"`。
- [ ] **Step 2：编写失败测试 `tests/test_config_cmd.py`**
  - `test_config_show_uninitialized_prints_empty`
  - `test_config_set_archive_root_only_changes_that_key`
  - `test_config_set_uninitialized_exit1`
- [ ] **Step 3：** 运行 `.venv/bin/pytest tests/test_init.py tests/test_config_cmd.py -v`。Expected：FAIL。
- [ ] **Step 4：** 按 Spec 第 6.2 节的流程图实现 `init_cmd.run` 与 `config_cmd`；`config.json` 最后写入。
- [ ] **Step 5：** 运行 `.venv/bin/pytest -q`。Expected：全部 PASS。
- [ ] **Step 6：** 提交 `feat: init and config commands`。

### Task 3: `feedr roster` 命令组

**Prerequisites:** Task 2

**Files:**
- Create: `~/Projects/feedr/feedr/roster/`：由 `tools/roster/roster/*.py` 复制而来，不复制 `migrate.py` 和 `__main__.py`；CLI 部分改为 `feedr/roster/cli.py`，提供 `register(subparsers)`
- Modify: `~/Projects/feedr/feedr/roster/config.py`：`get_data_dir()` 改为读取 `paths.require_initialized()["roster_dir"]`
- Create: `~/Projects/feedr/tests/roster/`：由 `tools/roster/tests/*.py` 复制而来，不复制 `test_migrate.py` 和两个 launcher 测试
- Test: `~/Projects/feedr/tests/roster/test_gate.py`

**Interfaces:**
- Produces：`feedr roster registry|state|profile|migrate-schema|data-dir ...`，参数与输出和原 roster 一致；没有 `init` 和 `migrate`（S3）
- Produces，供 Task 5 在进程内调用：
  - `feedr.roster.config.get_data_dir() -> Path`
  - `feedr.roster.registry.load(data_dir)`
  - `feedr.roster.state` 中 `get` / `set` / `fail` 对应的函数（沿用原名）

- [ ] **Step 1：编写失败测试 `tests/roster/test_gate.py`**
  - `test_roster_uninitialized_exit1_not_initialized`：执行 `main(["roster","registry","list"])`，退出码 1，stderr 首行以 `NOT_INITIALIZED` 开头，`FEEDR_HOME` 下没有新建任何目录。
  - `test_roster_reads_roster_dir_from_config`
  - `test_roster_has_no_init_or_migrate`：`main(["roster","init","x"]) == 2`。
- [ ] **Step 2：** 运行 `.venv/bin/pytest tests/roster/test_gate.py -v`。Expected：FAIL。
- [ ] **Step 3：迁入代码**
  - 原 `conftest.py` 用 `HSKILL_ROSTER_CONFIG` 隔离，改为写入 `FEEDR_HOME/config.json` 的 `roster_dir`。
  - 原 `test_cli.py` 中调用 `roster.__main__.main([...])` 的地方，改为 `feedr.cli.main(["roster", ...])`。
  - 涉及 `init` 和 `migrate` 的用例删除，并在 README「迁移说明」中列出删除了哪些用例。
- [ ] **Step 4：** 运行 `.venv/bin/pytest -q`。Expected：全部 PASS。
- [ ] **Step 5：** 提交 `feat: roster command group migrated from roster`。

### Task 4: 用旧脚本生成 golden 标准结果

**Prerequisites:** Task 1（需要 feedr 仓库目录已存在）

**Files:**
- Create: `~/Projects/feedr/scripts/gen_golden.py`（一次性脚本，参数为 `--hskill <harveyz-skill 工作区路径> --out tests/golden`）
- Create: `~/Projects/feedr/tests/golden/<platform>/<scenario>/{input.json,report.json,cursors_after.json,archive/<handle>.json}`

**Interfaces:**
- Produces：`input.json` 的结构为 `{"run_time": "2026-01-01T00:00:00+00:00", "handles": [...] | null, "channels": [{"handle","url"}], "cursors": {handle: value|null}, "fetch": {handle: {"items": [...]} | {"error": "msg"} | {"raise": "NoRuleError"|"TransformError"}}, "archive_before": {handle: [...]}}`
- Produces：`report.json` 是旧 `fetch_new_*.run()` 的输出；`archive/` 与 `cursors_after.json` 是对报告中 `new` 的每条加上 `"translated": "T:" + <原文字段>` 后，运行旧 `archive_*.py` 得到的结果。原文字段：x 用 `text`，youtube 和 website 用 `title`。
- 场景清单：
  - `x`：`baseline_pinned`、`new`、`none`、`channel_error`、`handle_not_on_roster`
  - `youtube`：`baseline`、`new`、`none`、`channel_error`、`handle_not_on_roster`
  - `website`：`baseline`、`new`、`none`、`channel_error`、`no_rule`、`transform_error`、`empty_list`

- [ ] **Step 1：** 编写 `gen_golden.py`。把旧 `skills/feed/sync-*/scripts` 加入 `sys.path`，按以下方式打桩：
  - 抓取：`fetch_new_tweets.fetch_timeline`、`fetch_new_videos.fetch_channel_videos`、`fetch_new_articles.fetch_articles`
  - 名册：`roster_client.channels` / `get_cursor` / `set_error` / `set_cursor`，用内存字典记录
  - 存档目录：`config.get_data_dir`，指向临时目录
  - 时间：固定 `datetime.now` 返回 `run_time`
- [ ] **Step 2：** 运行 `python3 scripts/gen_golden.py --hskill /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+feedr-split --out tests/golden`。Expected：三个平台共 17 个场景目录，每个目录都有 4 类文件。
- [ ] **Step 3：** 运行 `python3 scripts/gen_golden.py ... --check`，在临时目录重新生成后与已提交的结果比较。Expected：输出 `IDENTICAL`，证明生成过程是确定的。
- [ ] **Step 4：** 提交 `test: golden fixtures generated from legacy sync scripts`。

### Task 5: `feedr sync` 引擎与 x 适配器

**Prerequisites:** Task 3、Task 4

**Files:**
- Create: `~/Projects/feedr/feedr/sync/{__init__.py,adapters.py,engine.py,cli.py}`
- Modify: `~/Projects/feedr/feedr/cli.py`（挂上 `sync`）
- Test: `~/Projects/feedr/tests/sync/test_engine.py`、`~/Projects/feedr/tests/sync/test_golden.py`、`~/Projects/feedr/tests/sync/test_cursor_x.py`（由 `sync-xtimeline/tests/test_cursor.py` 迁入）

**Interfaces:**
- Consumes：Task 3 的 roster 函数；Task 1 的 `feedr.fetch.core.fetch_user_timeline`
- Produces，在 `adapters.py` 中：
  - `class NeedsCalibration(Exception)`
  - `@dataclass(frozen=True) class Adapter`，字段有 `platform: str`、`archive_subdir: str`、`cursor_type: str`、`item_key: str`、`fetch: Callable[[dict, str | None], Awaitable[list[dict]]]`、`compute_update: Callable[[object, list[dict]], tuple[str, dict | None]]`、`new_key: str`（`compute_update` 返回的新条目所在键：x 为 `"tweets"`，youtube 和 website 为 `"videos"`）、`cursor_key: str`、`empty_needs_calibration: bool`
  - `ADAPTERS: dict[str, Adapter]`
- Produces，在 `engine.py` 中：
  - `async def run_fetch(platform: str, handles: list[str] | None, chrome_profile: str | None, run_time: str | None = None) -> dict`
  - `def run_commit(platform: str, report: dict) -> None`
- Produces：CLI 命令 `feedr sync fetch <platform> [--chrome-profile P] [--handle H]...` 和 `feedr sync commit <platform>`（从 stdin 读取报告）

- [ ] **Step 1：编写失败测试 `tests/sync/test_engine.py`**，在 `adapter.fetch` 处打桩。
  - `test_fetch_without_archive_root_calls_no_fetch`：退出码 1，stderr 首行为 `MISSING_ARCHIVE_ROOT`，打桩函数调用次数为 0。
  - `test_fetch_uninitialized_not_initialized`
  - `test_fetch_report_has_next_and_archive_dir`：`report["next"] == "feedr sync commit x"`；`report["archive_dir"] == str(archive_root/"feeds"/"tweets")`。
  - `test_fetch_does_not_move_cursor`
  - `test_commit_archive_write_failure_keeps_cursor`：存档目录设为不可写（`chmod 0o500`），退出码 1，游标保持原值。
  - `test_commit_twice_is_idempotent`
  - `test_unknown_platform_exit2`
- [ ] **Step 2：编写失败测试 `tests/sync/test_golden.py`**
  - 参数化遍历 `tests/golden/<platform>/*`；本任务只要求 `x` 的场景通过，`youtube` 和 `website` 的场景用 `pytest.mark.xfail(strict=True)` 标记，原因写「Task 6」。
  - 断言 `{k: v for k, v in report.items() if k not in ("next", "archive_dir")} == golden_report`。
  - 按约定加上 `translated` 字段后执行 commit，存档文件逐字节等于 `archive/<handle>.json`，游标等于 `cursors_after.json`。
- [ ] **Step 3：** 运行 `.venv/bin/pytest tests/sync -v`。Expected：FAIL。
- [ ] **Step 4：实现 x 适配器、`engine` 与 `sync/cli.py`**
  - x 适配器的 `fetch` 调用 `fetch_user_timeline(url.rstrip("/") + "/all", chrome_profile, max_tweets=20)`，`compute_update` 沿用旧 `sync-xtimeline/scripts/cursor.py`。
  - `engine` 合并三份旧 `fetch_new_*.run` 与 `archive_*.py` 的公共逻辑。
- [ ] **Step 5：** 运行 `.venv/bin/pytest -q`。Expected：PASS；youtube 和 website 的场景为 xfail。
- [ ] **Step 6：** 提交 `feat: sync engine with two-phase fetch/commit and x adapter`。

### Task 6: youtube 与 website 适配器

**Prerequisites:** Task 5

**Files:**
- Modify: `~/Projects/feedr/feedr/sync/adapters.py`
- Modify: `~/Projects/feedr/tests/sync/test_golden.py`（去掉 xfail 标记）
- Test: `~/Projects/feedr/tests/sync/test_cursor_seen_urls.py`（由 `sync-ytchannel/tests/test_cursor.py` 迁入）

**Interfaces:**
- Consumes：`feedr.fetch.core.fetch_channel_videos`、`feedr.fetch.core.fetch_articles`
- Produces：
  - `ADAPTERS["youtube"]`：`archive_subdir="youtube"`、`item_key="video_id"`
  - `ADAPTERS["website"]`：`archive_subdir="website"`、`item_key="url"`、`empty_needs_calibration=True`
  - website 适配器的 `fetch` 遇到 `NO_RULE` 或 `TRANSFORM_ERROR` 时，抛出 `NeedsCalibration`，判定方式沿用旧 `articles_client.py`；engine 把这类渠道记入 `needs_calibration[handle] = url`

- [ ] **Step 1：** 去掉 `test_golden.py` 中 youtube 和 website 的 xfail 标记，迁入 `test_cursor_seen_urls.py`。
- [ ] **Step 2：** 运行 `.venv/bin/pytest tests/sync -v`。Expected：youtube 和 website 的场景 FAIL（`KeyError: 'youtube'`）。
- [ ] **Step 3：** 实现两个适配器；`max_videos` 等参数的默认值沿用旧 `mcp_channel_client.py` 与 `articles_client.py`。
- [ ] **Step 4：** 运行 `.venv/bin/pytest -q`。Expected：全部 PASS，没有 xfail。
- [ ] **Step 5：** 提交 `feat: youtube and website sync adapters`。

### Task 7: README、安装验证与发布前检查

**Prerequisites:** Task 6

**Files:**
- Modify: `~/Projects/feedr/README.md`
- Test: `~/Projects/feedr/tests/test_cli_surface.py`

**Interfaces:**
- Produces：README 包含产品概念、安装命令（Global Constraints 中的文案）、`init` 流程、`sync fetch`/`commit` 契约、隐私与风险说明（S10）和迁移说明。

- [ ] **Step 1：编写失败测试 `tests/test_cli_surface.py`**
  - `test_top_level_groups`：`--help` 的输出包含 `init`、`config`、`fetch`、`roster`、`sync`。
  - `test_fetch_lists_nine_legacy_subcommands`：输出包含 `profile`、`page`、`eval`、`article`、`timeline`、`channel`、`articles`、`articles-probe`、`articles-rule`。
  - `test_version`：`feedr --version` 输出 `0.1.0`。
- [ ] **Step 2：** 运行 `.venv/bin/pytest tests/test_cli_surface.py -v`。这三个是回归测试，用来守护 Task 1–6 已经实现的命令外观，不要求先失败。Expected：PASS；如果失败，修 CLI，不改断言。
- [ ] **Step 3：** 写 README。
- [ ] **Step 4：** 运行 `uv tool install --force /Users/harveyzhang96/Projects/feedr && feedr fetch install-browser && feedr --help`。Expected：列出 5 个命令组。
- [ ] **Step 5：** 运行 `.venv/bin/pytest -q`。Expected：全部 PASS。
- [ ] **Step 6：** 提交 `docs: README and install notes`。
- [ ] **Step 7：** 停下请用户确认，确认后才执行：`gh repo view harveyzhang96/feedr` 查名称是否被占用（D23）；用户同意后再执行 `gh repo create harveyzhang96/feedr --public --source . --push`。这一步是对外发布，必须由用户确认。

### Task 8: sync-xtimeline 切到 feedr

**Prerequisites:** Task 5（契约字段 `archive_dir` 已经确定）

**Files:**
- Delete：`skills/feed/sync-xtimeline/scripts/` 下的 `fetch_new_tweets.py`、`cursor.py`、`archive_tweets.py`、`roster_client.py`、`roster_locate.py`、`browser_fetch_locate.py`、`browser_fetch_cli.py`、`mcp_timeline_client.py`、`config.py`、`store_config.py`
- Delete：`skills/feed/sync-xtimeline/tests/` 下除 `test_render_digest.py`、`conftest.py` 外的全部测试
- Modify：`skills/feed/sync-xtimeline/scripts/render_digest.py`，改为从 `report["archive_dir"]` 计算 `digest/` 写入路径
- Modify：`skills/feed/sync-xtimeline/tests/{conftest.py,test_render_digest.py}`
- Modify：`skills/feed/sync-xtimeline/SKILL.md`（`version` 0.8.5 → 0.9.0）、`skills/feed/sync-xtimeline/platforms/SKILL.{claude,codex,hermes,pi}.md`
- Modify：`skills-index.json`，更新 `feed/sync-xtimeline` 的 `contentVersion` 和 `contentHash`

**Interfaces:**
- Consumes：`feedr sync fetch x` / `feedr sync commit x`、`feedr config show`、`feedr config set archive-root`

- [ ] **Step 1：** 修改 `test_render_digest.py`：输入报告带 `archive_dir=<tmp>`，断言摘要写到 `<tmp>/digest/digest-*.md`；`conftest.py` 删除 `store_config` 相关的隔离。
- [ ] **Step 2：** 运行 `python3 -m pytest skills/feed/sync-xtimeline/tests -q`。Expected：FAIL（`render_digest` 仍然 `import config`）。
- [ ] **Step 3：** 修改 `render_digest.py`，删除其余脚本和测试。
- [ ] **Step 4：改写 SKILL.md**
  - 初始化节：执行 `command -v feedr`，找不到时给出安装提示文案；按 Spec 第 6.3 节处理 `NOT_INITIALIZED` 和 `MISSING_ARCHIVE_ROOT`；删除 `check-downstream` 一步。
  - run 节：改为 `feedr sync fetch x [--handle H]...` → 翻译 → `render_digest.py` → `feedr sync commit x`。中断语义、失败报告和边界节的说明保持不变，只换命令名。
  - platforms 文件：把 browser-fetch 改为 feedr。
- [ ] **Step 5：** 用 Node 计算 hash：`node -e "const c=require('crypto'),f=require('fs');const b=f.readFileSync('skills/feed/sync-xtimeline/SKILL.md','utf8');console.log(c.createHash('sha256').update(b.replace(/^version:.*$/m,'version: __HASH_PLACEHOLDER__')).digest('hex').slice(0,16))"`，结果写入 `skills-index.json`。
- [ ] **Step 6：** 运行 `python3 -m pytest skills/feed/sync-xtimeline/tests -q && bats tests/skills.bats`。Expected：PASS。
- [ ] **Step 7：** 提交 `feat(sync-xtimeline): 改为调用 feedr sync`。

### Task 9: sync-ytchannel 切到 feedr

**Prerequisites:** Task 6

**Files:** 与 Task 8 对应：
- Delete：`fetch_new_videos.py`、`cursor.py`、`archive_videos.py`、`roster_client.py`、`roster_locate.py`、`browser_fetch_locate.py`、`browser_fetch_cli.py`、`mcp_channel_client.py`、`config.py`、`store_config.py` 及其测试
- Modify：`digest.py`、`tests/{conftest.py,test_digest.py}`、`SKILL.md`（小版本号 +1）、`platforms/*.md`、`skills-index.json`

**Interfaces:**
- Consumes：`feedr sync fetch youtube` / `feedr sync commit youtube`

- [ ] **Step 1：** 修改 `test_digest.py`，使其从 `archive_dir` 计算写入路径。
- [ ] **Step 2：** 运行 `python3 -m pytest skills/feed/sync-ytchannel/tests -q`。Expected：FAIL。
- [ ] **Step 3：** 修改 `digest.py`，删除旧脚本和对应测试。
- [ ] **Step 4：** 改写 SKILL.md 与 platforms 文件，规则与 Task 8 Step 4 相同。
- [ ] **Step 5：** 按 Task 8 Step 5 的方法更新 hash。
- [ ] **Step 6：** 运行 `python3 -m pytest skills/feed/sync-ytchannel/tests -q && bats tests/skills.bats`。Expected：PASS。
- [ ] **Step 7：** 提交 `feat(sync-ytchannel): 改为调用 feedr sync`。

### Task 10: sync-website 切到 feedr（含标定流程）

**Prerequisites:** Task 6

**Files:**
- Delete：`fetch_new_articles.py`、`cursor.py`、`archive_articles.py`、`roster_client.py`、`roster_locate.py`、`browser_fetch_locate.py`、`browser_fetch_cli.py`、`articles_client.py`、`config.py`、`store_config.py` 及其测试
- Keep：`calibration_gate.py` 和 `test_calibration_gate.py`
- Modify：`digest.py`、`tests/{conftest.py,test_digest.py}`、`references/calibrate.md`（`articles-probe`、`articles-rule` 改为 `feedr fetch ...`）、`SKILL.md`（小版本号 +1）、`platforms/*.md`、`skills-index.json`

**Interfaces:**
- Consumes：`feedr sync fetch website` / `feedr sync commit website`；`feedr fetch articles-probe`、`feedr fetch articles-rule set|get|list|rm`

- [ ] **Step 1：** 修改 `test_digest.py`，使其从 `archive_dir` 计算写入路径。
- [ ] **Step 2：** 运行 `python3 -m pytest skills/feed/sync-website/tests -q`。Expected：FAIL。
- [ ] **Step 3：** 修改 `digest.py`，删除旧脚本和对应测试。
- [ ] **Step 4：** 改写 SKILL.md、`calibrate.md` 和 platforms 文件；`needs_calibration` 的自愈流程不变。
- [ ] **Step 5：** 更新 hash。
- [ ] **Step 6：** 运行 `python3 -m pytest skills/feed/sync-website/tests -q && bats tests/skills.bats`。Expected：PASS。
- [ ] **Step 7：** 提交 `feat(sync-website): 改为调用 feedr sync 与 feedr fetch`。

### Task 11: manage-creators 与 capture-opinion 切到 `feedr roster`

**Prerequisites:** Task 3

**Files:**
- Delete：`skills/feed/manage-creators/scripts/roster_locate.py`、`skills/feed/manage-creators/tests/test_roster_locate.py`、`skills/feed/capture-opinion/scripts/roster_locate.py`
- Modify：`skills/feed/manage-creators/SKILL.md`、`skills/feed/manage-creators/references/migration.md`、`skills/feed/capture-opinion/SKILL.md`（两个 skill 的小版本号各 +1）、`skills-index.json`

**Interfaces:**
- Consumes：`feedr roster ...`、`feedr init [--roster-dir D]`、`feedr config show`

- [ ] **Step 1：改写两个 SKILL.md**
  - `<roster>` 一律改为 `feedr roster`。
  - 初始化部分按 Spec 第 6.3 节执行：遇到 `NOT_INITIALIZED` 时先运行 `feedr init`；返回 `MISSING_ROSTER_DIR` 时，按原规则请用户提供目录，再运行 `feedr init --roster-dir <目录>`。
  - 删除对 `~/.hskill/roster/config.json` 的检查。
  - `migrate-schema` 改为 `feedr roster migrate-schema`。
  - `migration.md` 同步修改。
- [ ] **Step 2：** 更新两个 skill 的 hash。
- [ ] **Step 3：** 运行 `bats tests/skills.bats && bash scripts/run-skill-tests.sh`。Expected：PASS；manage-creators 不再有 pytest 套件。
- [ ] **Step 4：** 提交 `feat(manage-creators,capture-opinion): 改为调用 feedr roster`。

### Task 12: clip-url 切到 `feedr fetch`

**Prerequisites:** Task 1

**Files:**
- Delete：`skills/research/clip-url/scripts/browser_fetch_locate.py`、`skills/research/clip-url/tests/test_browser_fetch_locate.py`
- Modify：`skills/research/clip-url/scripts/browser_fetch_cli.py`（调用改为 `[shutil.which("feedr") or 报错, "fetch", *args]`；找不到 feedr 时抛出 `RuntimeError`，消息为安装提示文案）
- Modify：`skills/research/clip-url/scripts/{mcp_fetch_client.py,mcp_debug_client.py,chrome_profile_config.py,detect_xcom_chrome_profile.py}` 中的 browser-fetch 字样与路径引用
- Modify：`skills/research/clip-url/tests/conftest.py`（改用 `FEEDR_HOME` 隔离，安装提示改为 feedr 的安装方式）及受影响的 `test_*.py`
- Modify：`skills/research/clip-url/SKILL.md`（小版本号 +1）、`skills/research/clip-url/references/*.md`、`skills-index.json`

**Interfaces:**
- Consumes：`feedr fetch <子命令>`

- [ ] **Step 1：编写失败测试**：在 `tests/test_mcp_fetch_client.py` 中新增 `test_cli_missing_feedr_raises_install_hint`。monkeypatch `shutil.which` 返回 `None`，断言抛出 `RuntimeError`，消息包含 `uv tool install git+https://github.com/harveyzhang96/feedr`。
- [ ] **Step 2：** 运行 `python3 -m pytest skills/research/clip-url/tests -q`。Expected：新增的测试 FAIL。
- [ ] **Step 3：** 修改 `browser_fetch_cli.py` 和其余脚本，删除 locate 脚本，把 conftest 改为 `FEEDR_HOME`。
- [ ] **Step 4：** 修改 SKILL.md 与 references，把 browser-fetch 改为 feedr；`store_config.py` 不动。
- [ ] **Step 5：** 更新 hash。
- [ ] **Step 6：** 运行 `python3 -m pytest skills/research/clip-url/tests -q`。Expected：PASS；没有安装 feedr 时，依赖真实浏览器的用例按 conftest 跳过。
- [ ] **Step 7：** 提交 `feat(clip-url): 改为调用 feedr fetch`。

### Task 13: 从 harveyz-skill 移除两个工具

**Prerequisites:** Task 8、9、10、11、12

**Files:**
- Delete：`tools/browser-fetch/`、`tools/roster/`（本地未被跟踪的 `tools/browser-fetch-mcp/` 不动，只在交付时汇报）
- Modify：`package.json`（`files` 去掉两个工具目录）
- Modify：`skills-index.json`（`tools` 去掉两条；`toolBundleMeta` 去掉 `research-tools`）
- Modify：`tests/install.bats`（删除 roster 和 browser-fetch 的安装用例）
- Modify：`scripts/run-skill-tests.sh`（注释中的示例不再提到被删的目录）
- Modify：`CHANGELOG.md`（新增一条：browser-fetch、roster 迁出为 feedr）
- Modify：`bin/`、`lib/` 中凡是读取 `research-tools` 的地方（如有）

- [ ] **Step 1：** 运行 `grep -rnE "browser-fetch|roster_locate|browser_fetch_locate|tools/roster|HSKILL_ROSTER_CONFIG|BROWSER_FETCH_DATA_DIR|research-tools" --exclude-dir=node_modules --exclude-dir=docs --exclude-dir=.hskill --exclude-dir=.worktrees . | grep -v "scripts/migrate-store.sh\|tests/migrate-store.bats\|CHANGELOG.md"`。Expected：这一步之前会有若干命中，记下命中清单。
- [ ] **Step 2：** 删除两个工具目录，按命中清单修改上述文件。
- [ ] **Step 3：** 重新运行 Step 1 的 grep。Expected：没有输出；`CHANGELOG.md` 中只有新增的那条提到它们。
- [ ] **Step 4：** 运行 `npm test`。Expected：全部 PASS。
- [ ] **Step 5：** 运行 `npm pack --dry-run 2>&1 | grep -E "tools/(browser-fetch|roster)"`。Expected：没有输出。
- [ ] **Step 6：** 在 PATH 上没有 feedr 的 shell 里（`env PATH=/usr/bin:/bin`）执行 `command -v feedr || echo MISSING`。Expected：`MISSING`。人工核对三个 sync-* SKILL.md 的检查步骤，确认此时会给出安装提示并终止。
- [ ] **Step 7：** 提交 `chore: 移除 tools/browser-fetch 与 tools/roster（迁出为 feedr）`。

### Task 14: 本机切换与真实数据验收（人工）

**Prerequisites:** Task 7、Task 13

**Files:**
- Create：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-cutover.md`（记录每一步的命令输出）

- [ ] **Step 1：** 切换前，用旧工具保存基准：
  - `~/.local/bin/roster registry list > /tmp/before-registry.txt`
  - `~/.local/bin/browser-fetch profile get > /tmp/before-profile.json`
  - `~/.local/bin/browser-fetch articles-rule list > /tmp/before-rules.json`
  
  如果旧 launcher 不在这个路径，用 `command -v` 查找。
- [ ] **Step 2：** 运行 `feedr init`，把迁移报告记入 cutover.md。Expected：`browser` 一项为 `copied`，`roster` 一项为 `copied`，`archive_root` 来自 `knowledgeRoot`，值为 `/Users/harveyzhang96/knowledge`。
- [ ] **Step 3：** 用 `diff` 对比 `feedr roster registry list`、`feedr fetch profile get`、`feedr fetch articles-rule list` 与 Step 1 的基准。Expected：三组都没有差异。
- [ ] **Step 4：** 运行 `feedr fetch timeline https://x.com/<名册中某个账号> --max 5`。Expected：返回推文，不需要重新登录。如果失败，停下并退回方案审查（Spec 第 13 节）。
- [ ] **Step 5：** 用户按 AGENTS.md 合并、部署改动过的 6 个 skill，并核对版本后，分别手动跑一轮：三个 sync-*、clip-url 抓一篇文章、`manage-creators list`、`capture-opinion show <id>`。把结果记入 cutover.md。
- [ ] **Step 6：** 核对 `~/.hskill/roster`、`~/.hskill/browser-fetch` 的文件数量与 Step 1 之前相同（只复制，不删除）。
- [ ] **Step 7：** 提交 `docs(feedr): 切换验收记录`。
