# capture-feature 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 [执行交接时确定的执行技能] 逐项实施；用 `- [ ]` 跟踪步骤。

**Goal:** 新建跨项目的产品功能地图 skill `capture-feature`（脚本 + 精简 SKILL.md + references），改造 capture-vocab 1.3.0 使其查词与新增时联动功能地图，登记发布，并在 agent-canvas 完成试点迁移。

**Architecture:** 单文件标准库脚本 `feature.py` 读写 `<project-root>/.hskill/capture-feature/features/<id>.json`（一对象一文件），所有写入经 `put` 校验；查询只把命中卡片输出给 agent。capture-vocab 在项目存在功能地图时每次 `query`/`add` 查重都 invoke capture-feature；两个 skill 的 SKILL.md 都只留查词路径，其余渐进披露在 `references/`。

**Tech Stack:** Python 3 标准库（json、argparse、pathlib、re、subprocess）、pytest（经 `scripts/run-skill-tests.sh` 自动发现）、bats/node 既有 `npm test`。

**Spec:** `.hskill/spec/2026-11-24-capture-feature/2026-11-24-capture-feature-spec.md`

**Spec Version and Scope:** v0.1，已批准，全文（含次要决定 S1–S15，S13 已被 D19 取代）；未决 D15、D16 不在本计划内。

## Global Constraints

- 所有路径相对 worktree 根 `/Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+capture-feature`。
- `feature.py` 只用 Python 标准库；调用形式 `python3 SKILL_DIR/scripts/feature.py <子命令> [参数]`。
- 退出码：`0` 成功/命中；`1` 未命中、校验不通过或发现问题；`2` 用法错误、找不到数据目录、JSON 无法解析、版本号无法解析。
- 固定输出文案（逐字）：`no feature map`、`no match: <输入>`、`<N> matches: <名1>, <名2>, …`、`no such id: <id>`、`no refs: <path>`、`no candidates`、`wrote features/<id>.json`、`removed <id>`、`has children: <id1>, <id2>`、`ok`、`unknown`；校验错误行前缀 `error: `，警告行前缀 `warn: `；损坏文件 stderr `skip: <文件名>: <原因>`。
- 数据目录定位（S2）：从 cwd 向上找 `.hskill/capture-feature/`；遇到含 `.git` 的目录即停。只读命令找不到 → `no feature map` exit 2；`put` 找不到 → 在该含 `.git` 的目录下创建 `.hskill/capture-feature/features/`；连 `.git` 也找不到 → `no feature map` exit 2。
- 对象 schema 与字段规则以 Spec §4.2 表格为准；序列化（S7）：`json.dumps(obj, ensure_ascii=False, indent=2)` + `"\n"`，键顺序 `schema, id, type, name, aliases, avoid, description, parent, code, versions`，`versions` 内顺序 `introduced, changed, deprecated`；缺省字段写入时补默认值（`aliases: []`、`avoid: []`、`code: []`、`changed: []`、`deprecated: null`），`avoid[].note` 缺省补 `null`。
- 匹配规则与 `skills/coding/capture-vocab/scripts/vocab.py` 的 `normalize` / `bidir_match` 一致（全半角括号统一、去反引号、casefold、strip；双向子串；查询归一化后不足 2 字视为未命中）；参与匹配的是 `name`、`aliases[]`、`avoid[].name`。
- 卡片格式以 Spec §5.1 为准；空行（无别称、无避免、无子项、无代码）不输出；「位置」为根到自身的 `name` 链，用 ` > ` 连接；「版本」行格式 `引入 X；变更 V1（note1）、V2（note2）；废弃 Y`，无变更时省略「；变更 …」段，未废弃写 `废弃 —`。
- 版本号：capture-feature `0.1.0`；capture-vocab `1.3.0`。`description` 英文；正文中文（skill-spec F1–F9）。
- 篇幅（D19）：`skills/coding/capture-feature/SKILL.md` ≤ 2641 字节；`skills/coding/capture-vocab/SKILL.md` ≤ 47 行（原 42 行 + 5）。
- `contentHash` 计算：`sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' SKILL.md | shasum -a 256 | cut -c1-16`。
- 合并只在用户明确说“合并”后经 `manage-worktree`「合并」执行；不 push。

## Review Focus

- `put --replace` 把 `parent` 改成自己的后代（成环）→ exit 1，`error: cycle …`，磁盘文件字节不变。（Task 1）
- 整句查询同时命中名称与 `avoid` 叫法、命中超过 3 条 → 只输出 `<N> matches: …` 一行；`avoid` 命中的卡片「避免」行带 note。（Task 2）
- `features/` 下有一个损坏 JSON → 只读命令 stderr 输出 `skip:` 后照常工作；`check` 报 `invalid`；`put` 不因它报错（但其 id 视为不存在）。（Task 1、Task 3）
- `list --at` 边界：`introduced == VERSION` 计入，`deprecated == VERSION` 不计入，`unknown` 总计入；`--at abc` → exit 2。（Task 2）
- cwd 在项目子目录、项目尚无数据目录时首次 `put` → 在 git 根创建目录并写入；无 `.git` 时 exit 2。（Task 1）

---

### Task 1: 对象写入、校验与基本读取（`put` / `show` / `remove`）

**Prerequisites:** 无

**Files:**
- Create: `skills/coding/capture-feature/scripts/feature.py`
- Create: `skills/coding/capture-feature/tests/conftest.py`
- Test: `skills/coding/capture-feature/tests/test_put.py`

**Interfaces:**
- Produces（`feature.py` 内部，供 Task 2/3 复用）：
  - `find_data_dir(create: bool = False) -> Path | None` —— 返回 `.hskill/capture-feature` 目录
  - `load_all(data_dir: Path) -> dict[str, dict]` —— id → 对象；损坏文件 stderr `skip:` 并跳过
  - `normalize(s: str) -> str`、`bidir_match(a: str, b: str) -> bool`（与 vocab.py 同义）
  - `match_keys(obj: dict) -> list[str]` —— `name` + `aliases` + `avoid[].name`
  - `validate(obj: dict, all_objs: dict, mode: str) -> tuple[list[str], list[str]]` —— (errors, warnings)
  - `serialize(obj: dict) -> str`
  - `render_card(obj: dict, all_objs: dict) -> str`（Task 2 完善「位置/子项」，本任务可先输出全部行）
  - `main(argv: list[str]) -> int`，子命令以 `argparse` 分派
- Produces（测试夹具 `conftest.py`）：
  - `make_project(tmp_path, objects: list[dict], vocab_md: str | None = None) -> Path` —— 建 `.git/` 目录、写对象文件（按 `serialize` 规则）、可选写 `.hskill/capture-vocab/vocab.md`，返回项目根
  - `run_feature(args: list[str], cwd: Path, stdin: str | None = None) -> CompletedProcess`
  - `obj(id, name, parent=None, **kw) -> dict` —— 构造最小合法对象（`type="feature"`、`description="d"`、`versions={"introduced":"unknown"}`）

- [ ] **Step 1: 编写失败测试 `test_put.py`**

```python
def test_put_new_writes_canonical_bytes(tmp_path):      # stdin 为键乱序、缺省字段的合法对象
    # exit 0；stdout == "wrote features/workspace.json"；文件内容 == serialize(补默认值后的对象)
def test_put_new_rejects_existing_id(tmp_path):         # exit 1；stdout 含 "error: "；文件字节不变
def test_put_replace_requires_existing_id(tmp_path):    # exit 1；无新文件
def test_put_rejects_missing_required_field(tmp_path):  # 缺 description → exit 1，"error: " 行提到 description
def test_put_rejects_bad_type(tmp_path):                # type="page" → exit 1
def test_put_rejects_bad_id(tmp_path):                  # id="Work_Space" → exit 1
def test_put_rejects_unknown_parent(tmp_path):          # parent="nope" → exit 1
def test_put_replace_rejects_cycle(tmp_path):           # a<-b<-c，replace a.parent="c" → exit 1，"error: cycle"；三文件字节不变
def test_put_rejects_duplicate_name(tmp_path):          # 归一化后同名 → exit 1
def test_put_warns_on_alias_overlap(tmp_path):          # aliases 与他人 avoid.name 相同 → exit 0，stdout 含 "warn: "
def test_put_creates_dir_at_git_root_from_subdir(tmp_path):  # 无数据目录、cwd=项目/src/x → 在项目根创建并写入
def test_put_without_git_root_exits_2(tmp_path):        # 无 .git → exit 2，"no feature map"
def test_put_ignores_corrupt_sibling(tmp_path):         # 另有 bad.json 损坏 → put 新对象 exit 0；stderr 含 "skip: bad.json"
def test_show_existing_and_missing(tmp_path):           # show workspace → exit 0 含 "## 工作区  [surface]  id=workspace"；show nope → exit 1 "no such id: nope"
def test_readonly_without_data_dir_exits_2(tmp_path):   # show x → exit 2，"no feature map"
def test_remove_leaf_and_refuse_with_children(tmp_path):  # remove 叶子 → "removed c" 文件消失；remove 有子节点 → exit 1 "has children: b"
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `python3 -m pytest skills/coding/capture-feature/tests/test_put.py -v`
Expected: FAIL（`feature.py` 不存在）

- [ ] **Step 3: 在 `feature.py` 实现上列 Produces 接口与子命令 `put --new|--replace`、`show <id>`、`remove <id>`**

Approach: 校验全部完成、`errors` 为空后才写盘；写盘先写同目录临时文件再 `os.replace`。环检测沿拟写对象的 `parent` 链在“现有对象 + 拟写对象”上走，回到自身即成环。

- [ ] **Step 4: 运行本任务全部测试，验证通过**

Run: `python3 -m pytest skills/coding/capture-feature/tests/test_put.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/coding/capture-feature/scripts/feature.py skills/coding/capture-feature/tests/
git commit -m "feat(capture-feature): 对象写入校验与 show/remove"
```

### Task 2: 查询（`lookup` 卡片 / `tree` / `list` / `refs`）

**Prerequisites:** Task 1

**Files:**
- Modify: `skills/coding/capture-feature/scripts/feature.py`
- Test: `skills/coding/capture-feature/tests/test_query.py`

**Interfaces:**
- Consumes: Task 1 的 `find_data_dir`、`load_all`、`normalize`、`bidir_match`、`match_keys`、`render_card`、`make_project`、`run_feature`、`obj`
- Produces: `parse_version(v: str) -> tuple[int, ...]`（无法解析抛 `ValueError`）；`exists_at(obj: dict, version: str) -> bool`；`classify_path(query: str, candidate: str) -> str | None`（`same-file` / `dir-contains`，规则同 vocab.py）

测试夹具：根 `app-window`(应用窗口, surface) → `workspace`(工作区, surface, aliases=["右侧面板"], avoid=[{"name":"抽屉","note":None},{"name":"Workspace","note":"代码内部名，不向用户暴露"}], code=[{"path":"src/PanelArea.tsx","symbol":"PanelArea"}], versions introduced 0.3.0, changed [{"version":"0.5.0","note":"支持多 Tab"}]) → `tab`(Tab)、`view`(视图)；`tab` → `tab-bar`(Tab 栏, entry)；另有 `legacy`(旧面板, introduced 0.1.0, deprecated 0.4.0)。

- [ ] **Step 1: 编写失败测试 `test_query.py`**

```python
def test_lookup_by_name_prints_card(tmp_path):
    # lookup 工作区 → exit 0；stdout 依次含:
    # "## 工作区  [surface]  id=workspace" / "别称: 右侧面板" /
    # "避免: 抽屉；Workspace（代码内部名，不向用户暴露）" / "位置: 应用窗口 > 工作区" /
    # "子项: Tab, 视图" / "代码: src/PanelArea.tsx#PanelArea" / "版本: 引入 0.3.0；变更 0.5.0（支持多 Tab）；废弃 —"
def test_lookup_by_avoid_name_hits(tmp_path):        # lookup 抽屉 → 工作区卡片
def test_lookup_sentence_contains_name(tmp_path):    # "右边的工作区怎么拖宽" → 工作区卡片
def test_lookup_omits_empty_lines(tmp_path):         # lookup 视图 → 无 "别称:"、"避免:"、"子项:"、"代码:" 行
def test_lookup_short_query_is_miss(tmp_path):       # lookup "a" → exit 1，"no match: a"
def test_lookup_miss(tmp_path):                      # exit 1，"no match: zzz"
def test_lookup_degrades_above_three(tmp_path):      # 再加 4 个名称含 "面板" 的对象 → 单行，匹配 r"^(\d+) matches: " 且 N > 3
def test_tree_default_depth_1(tmp_path):             # tree → 根 "应用窗口 [surface] app-window" 与 "旧面板 …" 及其直接子 "  工作区 [surface] workspace"；不含 "Tab"
def test_tree_subtree_depth_2(tmp_path):             # tree workspace --depth 2 → 含 "Tab 栏"
def test_list_type_filter(tmp_path):                 # list --type entry → 仅一行，rstrip 后 == "tab-bar | Tab 栏 | entry | tab |"
def test_list_at_boundaries(tmp_path):               # --at 0.3.0 含 workspace、legacy；--at 0.4.0 不含 legacy；--at 0.2.0 不含 workspace、含 introduced=unknown 的对象
def test_list_at_unparsable_exits_2(tmp_path):       # --at abc → exit 2
def test_refs_same_file_and_dir(tmp_path):           # refs src/PanelArea.tsx → "workspace | 工作区 | same-file | src/PanelArea.tsx#PanelArea"；refs src/ → dir-contains；refs other.ts → exit 1 "no refs: other.ts"
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `python3 -m pytest skills/coding/capture-feature/tests/test_query.py -v`
Expected: FAIL（子命令未实现）

- [ ] **Step 3: 在 `feature.py` 实现 `lookup`、`tree [<id>] [--depth N]`、`list [--type T] [--at VERSION]`、`refs <path>`，补全 `render_card` 的位置/子项/空行省略**

Approach: `tree` 的 `--depth N` 指起点以下展开 N 层（不给 id 时起点为全部根节点，根本身总输出、缩进 0）。`parse_version` 用 `re.split(r'\D+', v)` 取非空段转 int，无数字段抛 `ValueError`；比较用元组。`tree` 行格式 `"  " * depth + f"{name} [{type}] {id}"`；`list` 行格式 `f"{id} | {name} | {type} | {parent or ''} | {','.join(aliases)}"`。

- [ ] **Step 4: 运行 capture-feature 全部测试，验证通过**

Run: `python3 -m pytest skills/coding/capture-feature/tests -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/coding/capture-feature/scripts/feature.py skills/coding/capture-feature/tests/test_query.py
git commit -m "feat(capture-feature): lookup 卡片、tree、list、refs"
```

### Task 3: 写入辅助与体检（`dupcheck` / `suggest-parent` / `project-version` / `check`）

**Prerequisites:** Task 2（同文件，顺序执行）

**Files:**
- Modify: `skills/coding/capture-feature/scripts/feature.py`
- Test: `skills/coding/capture-feature/tests/test_check.py`

**Interfaces:**
- Consumes: Task 1/2 的加载、匹配、`classify_path`
- Produces: 子命令输出格式（Task 4 文档引用）：
  - `dupcheck`：`exact | <id>`、`fuzzy | <id>`、`vocab | <标题名>`
  - `suggest-parent`：`<id> | <name> | <reason>`，reason ∈ `same-file`、`dir-contains`、`name`
  - `check`：`<类别> | <id> | <详情>`，类别 ∈ `invalid`、`id-mismatch`、`missing-parent`、`cycle`、`duplicate-name`、`code-missing`、`symbol-missing`

- [ ] **Step 1: 编写失败测试 `test_check.py`**

```python
def test_dupcheck_exact_on_avoid(tmp_path):        # dupcheck 抽屉 → exit 1，含 "exact | workspace"
def test_dupcheck_fuzzy(tmp_path):                 # dupcheck 工作区面板 → 含 "fuzzy | workspace"
def test_dupcheck_vocab_header(tmp_path):          # vocab.md 含 "## 席位" → dupcheck 席位 → "vocab | 席位"
def test_dupcheck_clean(tmp_path):                 # exit 0，无输出
def test_suggest_parent_by_path_first(tmp_path):   # --name 拖拽手柄 --path src/PanelArea.tsx → 首行 "workspace | 工作区 | same-file"
def test_suggest_parent_by_name(tmp_path):         # --name 工作区 Tab 菜单 → 含 "workspace | 工作区 | name"；最多 5 行
def test_suggest_parent_none(tmp_path):            # exit 1，"no candidates"
def test_project_version_sources(tmp_path):        # package.json {"version":"1.2.0"} → "1.2.0"；仅 pyproject `version = "0.9.1"` → "0.9.1"；仅 git tag v2.0.0 → "v2.0.0"；都无 → exit 1 "unknown"
def test_check_clean_ok(tmp_path):                 # exit 0，stdout == "ok"
def test_check_reports_structural_problems(tmp_path):
    # 手工写入：损坏 JSON、文件名≠id、parent 不存在、a↔b 成环、两对象同名
    # → exit 1；分别含 "invalid |"、"id-mismatch |"、"missing-parent |"、"cycle |"、"duplicate-name |"
def test_check_code(tmp_path):                     # --code：路径不存在 → "code-missing"；文件无该符号 → "symbol-missing"；不加 --code 时不报这两类
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `python3 -m pytest skills/coding/capture-feature/tests/test_check.py -v`
Expected: FAIL

- [ ] **Step 3: 在 `feature.py` 实现 `dupcheck <name> [--alias A …]`、`suggest-parent --name N [--path P …]`、`project-version`、`check [--code]`**

Approach: `dupcheck` 的 vocab 检查只用 `^## (.+)$` 读 `<project-root>/.hskill/capture-vocab/vocab.md` 标题并归一化比对（S9）；`project-version` 读 `pyproject.toml` 用正则 `^version\s*=\s*"([^"]+)"`，git tag 用 `git describe --tags --abbrev=0`（失败视为无）；`check` 直接扫描原始文件（不经 `load_all` 的跳过逻辑）以便报告 `invalid`；代码线索路径相对项目根。

- [ ] **Step 4: 运行 capture-feature 全部测试，验证通过**

Run: `python3 -m pytest skills/coding/capture-feature/tests -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/coding/capture-feature/scripts/feature.py skills/coding/capture-feature/tests/test_check.py
git commit -m "feat(capture-feature): dupcheck、suggest-parent、project-version、check"
```

### Task 4: capture-feature 的 SKILL.md 与 references

**Prerequisites:** Task 3（文档引用全部子命令的确定输出）

**Files:**
- Create: `skills/coding/capture-feature/SKILL.md`
- Create: `skills/coding/capture-feature/references/manage.md` —— add / update / remove / check 流程（Spec §6.1）、对象格式与字段规则（§4.2–4.3）、`avoid` 写法
- Create: `skills/coding/capture-feature/references/migrate.md` —— 从 vocab 迁移的办法（Spec §8 步骤 1–4、清单表头、`_Avoid_`→`avoid` 规则、S15 新增父节点、`文件:行号`→路径+符号）
- Test: `skills/coding/capture-feature/tests/test_skill_doc.py`

**Interfaces:**
- Consumes: Task 1–3 的子命令名、参数与输出文案
- Produces: 斜杠形式 `/capture-feature query|add|update|remove|check <term>`（Task 5 引用 `query`、`add`）

- [ ] **Step 1: 编写失败测试 `test_skill_doc.py`**

```python
def test_skill_md_within_budget():        # len(SKILL.md.encode()) <= 2641
def test_frontmatter():                   # name == "capture-feature"；version == "0.1.0"；user_invocable: true；description 非空且无 CJK 字符
def test_referenced_files_exist():        # SKILL.md 中出现的 references/*.md 路径都存在
def test_skill_md_has_query_only():       # 含 "feature.py lookup"；不含 "put --new"（写操作只在 references）
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `python3 -m pytest skills/coding/capture-feature/tests/test_skill_doc.py -v`
Expected: FAIL（文件不存在）

- [ ] **Step 3: 编写 `SKILL.md`（调用格式、`query` 步骤、「要做的事 → 读哪份」表）与两份 references**

Approach: `query` 步骤照 Spec §6.1：exit 0 按卡片回答，按「代码」行直接打开文件/`rg` 符号；`N matches` 挑最相关再 `lookup`；exit 1 说明无此功能；exit 2 或脚本不可用说明地图不可用，不读整个目录。卡片「避免」行的叫法不得用于回复、文档、commit。description 写明触发：looking up or adding user-perceivable product features, UI surfaces, interaction entries, their hierarchy and code locations; invoked by capture-vocab.

- [ ] **Step 4: 运行本任务测试与仓库格式检查，验证通过**

Run: `python3 -m pytest skills/coding/capture-feature/tests -v && npx bats tests/skills.bats`
Expected: PASS（`tests/skills.bats` 含全部 SKILL.md 的 frontmatter 格式检查）

- [ ] **Step 5: 提交**

```bash
git add skills/coding/capture-feature/SKILL.md skills/coding/capture-feature/references skills/coding/capture-feature/tests/test_skill_doc.py
git commit -m "feat(capture-feature): SKILL.md 与 references（渐进披露）"
```

### Task 5: capture-vocab 1.3.0 联动功能地图

**Prerequisites:** 无（只引用 Task 4 的斜杠形式，已在 Interfaces 固定）

**Files:**
- Modify: `skills/coding/capture-vocab/SKILL.md` —— `version: "1.3.0"`；query 段在 `vocab.py lookup` 之后加一步：存在 `.hskill/capture-feature/` 时 invoke capture-feature 用同一输入跑 `query`，两边结果合并回答，两边都未命中才按字面理解；capture-feature 未安装时提示「功能地图存在但 capture-feature 未安装」
- Modify: `skills/coding/capture-vocab/references/manage.md` —— add 第 1 步查重同时 invoke capture-feature `query`，命中功能并入第 5 步三选一；第 2 步后插入归属判断（D8：用户能否直接看到或操作），归功能地图且用户确认 → 停止本流程、invoke capture-feature `add <term>` 并带上已推断的定义与代码线索
- Modify: `skills/coding/capture-vocab/references/project-setup.md` —— 补一句：启用功能地图只需安装 capture-feature，项目指令无需新增内容
- Test: `skills/coding/capture-vocab/tests/test_skill_doc.py`

**Interfaces:**
- Consumes: `/capture-feature query <term>`、`/capture-feature add <term>`（Task 4）

- [ ] **Step 1: 编写失败测试 `test_skill_doc.py`**

```python
def test_skill_md_line_budget():          # SKILL.md 行数 <= 47
def test_version_bumped():                # frontmatter version == "1.3.0"
def test_query_invokes_capture_feature(): # SKILL.md 含 ".hskill/capture-feature/" 与 "capture-feature"
def test_add_routes_to_capture_feature(): # references/manage.md 含 "capture-feature" 且含 "add"
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `python3 -m pytest skills/coding/capture-vocab/tests/test_skill_doc.py -v`
Expected: FAIL（版本仍为 1.2.3，未提及 capture-feature）

- [ ] **Step 3: 按 Files 所列修改三份文档**

- [ ] **Step 4: 运行 capture-vocab 全部测试（含原有 `test_vocab.py` 原样通过），验证通过**

Run: `python3 -m pytest skills/coding/capture-vocab/tests -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add skills/coding/capture-vocab
git commit -m "feat(capture-vocab): 1.3.0 查词与新增联动 capture-feature"
```

### Task 6: 登记与发布准备

**Prerequisites:** Task 4、Task 5

**Files:**
- Modify: `skills-index.json` —— `skills` 新增 `{"path": "coding/capture-feature", "bundle": "coding", "installScope": "project", "contentHash": <计算值>, "contentVersion": "0.1.0"}`（紧跟 `coding/capture-vocab` 条目）；capture-vocab 条目 `contentHash` 重算、`contentVersion` 改 `"1.3.0"`；`bundleMeta.coding` 在 `capture-vocab` 后加 ` + capture-feature`
- Modify: `package.json` —— `files` 在 `"skills/coding/capture-vocab/"` 后加 `"skills/coding/capture-feature/"`
- Modify: `CHANGELOG.md` —— `## [Unreleased]` 的 `### Added` 加 capture-feature 0.1.0 条目，`### Changed`（无则新建）加 capture-vocab 1.3.0 条目

- [ ] **Step 1: 计算两个 contentHash**

Run: `for s in capture-feature capture-vocab; do sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' skills/coding/$s/SKILL.md | shasum -a 256 | cut -c1-16; done`
Expected: 两行 16 位十六进制

- [ ] **Step 2: 按 Files 所列修改三处并写入 Step 1 的值**

- [ ] **Step 3: 运行全量测试，验证通过**

Run: `npm test`
Expected: PASS（含 F1–F9 格式检查与两个 skill 的 pytest）

- [ ] **Step 4: 验证打包包含新 skill**

Run: `npm pack --dry-run 2>&1 | grep -c 'skills/coding/capture-feature/'`
Expected: ≥ 5（SKILL.md、scripts/feature.py、两份 references、tests 若未被 .npmignore 排除则更多）

- [ ] **Step 5: 提交**

```bash
git add skills-index.json package.json CHANGELOG.md
git commit -m "chore(capture-feature): 登记 skills-index、npm files 与 CHANGELOG"
```

### Task 7: 合并、部署与 agent-canvas 试点迁移

**Prerequisites:** Task 6；用户明确说“合并”

本任务跨仓库、以人工确认为主，不走红绿循环；验收对应 Spec §11 第 10–12 条。

- [ ] **Step 1: 合并到 staging**：在本 worktree 调用 `manage-worktree`「合并」；先 `git rev-parse --abbrev-ref HEAD` 确认为 `feature/capture-feature`。Expected: 合并脚本 exit 0。
- [ ] **Step 2: 部署两个 skill 到 `~/.claude/skills/`**（仓库 AGENTS.md「部署与发布」）：

```bash
T=$(mktemp -d)
git -C /Users/harveyzhang96/Projects/harveyz-skill archive staging skills/coding/capture-feature skills/coding/capture-vocab | tar -x -C "$T"
rsync -a --exclude '.DS_Store' "$T/skills/coding/capture-feature/" ~/.claude/skills/capture-feature/
rsync -a --exclude '.DS_Store' "$T/skills/coding/capture-vocab/" ~/.claude/skills/capture-vocab/
grep '^version:' ~/.claude/skills/capture-feature/SKILL.md ~/.claude/skills/capture-vocab/SKILL.md
```

Expected: `0.1.0` 与 `1.3.0`。
- [ ] **Step 3: 在 agent-canvas 开迁移工作**：在 agent-canvas 仓库先走其 `route-work` 路由，分支 `chore/capture-feature-pilot`；按 `~/.claude/skills/capture-feature/references/migrate.md` 产出 53 条词条的迁移清单（含新增父节点、`aliases`/`avoid` 拆分、路径+符号），交用户逐条确认。
- [ ] **Step 4: 写入与清理**：按父在前顺序 `put --new` 全部迁移对象 → 全部成功后从 `vocab.md` 删除对应段落 → `feature.py check --code`。Expected: `ok`。
- [ ] **Step 5: 验收抽查**：3 个只在 `avoid`/`aliases` 中的旧叫法（至少 1 句同时含 vocab 术语）经 capture-vocab 拿到正确卡片；「分支/Worktree 追踪机制」由 vocab 命中且定义与迁移前一致。记录结果到迁移提交信息或交付说明。
- [ ] **Step 6: 提交并按 agent-canvas 规则合并**（`scripts/merge-to-staging.sh`，用户说合并时）。
