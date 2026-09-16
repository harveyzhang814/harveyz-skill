# 统一存储根 · 下游漂移检测设计

## 元信息

- **设计日期**：2026-09-14
- **状态**：待实施
- **涉及组件**：`clip-url`、`learn-video`、`sync-xtimeline`、`sync-ytchannel`、`sync-website` 五份 `scripts/store_config.py`；五份 SKILL.md 的「前置：检查统一存储根」步骤
- **前置文档**：`2026-09-01-unified-store-design.md`（定义 `knowledgeRoot` 与五个 skill 的落盘契约）
- **本文范围**：只加一个只读检测子命令，核对两个下游程序（vdl、scholia）的当前配置是否与 `knowledgeRoot` 一致，不新增任何写操作，不改动 `check` 子命令已有的行为

---

## 0. 主线

> `knowledgeRoot` 是唯一事实依据；vdl、scholia 的配置只是被检查的对象，不参与仲裁。

可证伪：只要检测逻辑用了 vdl 或 scholia 自己配置文件里的值去判断"谁对谁错"，而不是单向拿 `knowledgeRoot` 推出的期望值去比对它们，主线即被推翻。

---

## 1. 背景

`2026-09-01-unified-store-design.md` 定义了 `knowledgeRoot`（`~/.hskill/config.json`）作为五个 skill 的唯一存储根依据，但明确记下一项遗留代价（该文档 §5.2）：**`knowledgeRoot` 与 vdl 的 `WORK_ROOT`（`~/.config/vdl/settings.conf`）分居两个文件，无机制保证同步**，且原则上"skill 不代改 vdl 的配置文件——那是另一个程序的配置"。

2026-09-14 的一次 `knowledgeRoot` 迁移（`~/Documents/knowledge` → `~/knowledge`）中，vdl 的 `WORK_ROOT` 被人工同步，但另一个下游消费者 **scholia**（渲染层，读 `meta.json` 给视频卡片用，配置在 `~/.config/scholia/settings.conf` 的 `WORK_DIR`/`CONTENT_DIR`/`X_DIR`）被漏掉，静默停在旧路径。发现纯属偶然（人工翻配置文件时看到的），没有任何机制会主动暴露这类漂移。

本文只解决"发现不了漂移"这一件事，不解决"要不要自动修复"——修复仍然是人工决定。

---

## 2. 检测对象与唯一事实依据

`knowledgeRoot`（`~/.hskill/config.json`，经 `store_config.get_root()` 读出）是唯一事实依据。检测是单向的：先用 `get_root()` 推出期望值，再去问 vdl、scholia 各自当前的**有效值**，不等即漂移。

| 下游 | 取值方式 | 期望值 |
|---|---|---|
| vdl | 执行 `vdl config get`，解析 `workRoot:` 一行 | `store_config.videos_dir()`，即 `<knowledgeRoot>/videos` |
| scholia | 执行 `scholia config list`，解析 `work-dir` / `content-dir` / `x-dir` 三行 | `<knowledgeRoot>/videos/work`、`store_config.articles_dir()`、`store_config.feeds_dir('tweets') / 'creators'` |

两个命令都通过各自程序自带的 CLI 读取（`vdl config get`、`scholia config list`），不自行解析 `settings.conf` 的文本格式——两边配置文件的注释语法、引号处理、未设置时的默认值回退逻辑都由各自程序自己负责，检测脚本只认它们 CLI 报出来的"当前有效值"。

`vdl`、`scholia` 命令均不在 `PATH` 上（对应工具未安装）时，该项记为 `SKIP`，不计入失败——不是所有安装了这五个 skill 的环境都同时装了这两个下游工具。

---

## 3. 输出与退出码

新增子命令 `store_config.py check-downstream`，与现有 `check` 子命令完全独立，不改动 `check` 原有的 stdout 格式与退出码语义（现有 287 个测试断言其行为，不能动）。

输出示例：

```
OK: vdl WORK_ROOT
DRIFT: scholia work-dir=/Users/x/Documents/knowledge/videos/work (expect /Users/x/knowledge/videos/work)
  fix: scholia config set work-dir /Users/x/knowledge/videos/work
SKIP: vdl not installed (command not found)
```

- 每个下游、每个字段一行（vdl 一行；scholia 最多三行，`work-dir`/`content-dir`/`x-dir` 各判各的）
- `DRIFT` 行下面紧跟一行 `fix:`，给出可直接复制执行的修复命令（vdl 用 `vdl config set work-root <期望值>`；scholia 用 `scholia config set <key> <期望值>`）
- 存在任意一条 `DRIFT` → 退出码 1；否则（全 `OK` 和/或 `SKIP`）→ 退出码 0

---

## 4. 调用点

五份 SKILL.md 的「前置：检查统一存储根」步骤，在现有 `python3 scripts/store_config.py check` 之后追加一步：

```bash
python3 scripts/store_config.py check-downstream
```

把输出原样报告给用户。出现 `DRIFT` 时不自动执行 `fix:` 命令——是否执行由用户决定，这条延续既有原则（skill 不代改下游程序的配置）。

---

## 5. 代码位置

五份 `scripts/store_config.py`（clip-url / learn-video / sync-xtimeline / sync-ytchannel / sync-website）各自的 `main()` 里加相同的 `check-downstream` 分支与配套的下游检测函数——延续本仓库既有约定（`store_config.py` 本身就是"每个 skill 自带一份相同副本"，不新起共享脚本）。

用 `subprocess` 调用 `vdl` / `scholia` 两个外部命令；命令不存在（`FileNotFoundError`）按 `SKIP` 处理，不抛异常。

---

## 6. 明确不做

- 不自动执行 `vdl config set` / `scholia config set`——只报告、只给命令，执行权在用户
- 不检查 Browser Fetch——它存的是浏览器会话态（`~/.hskill/browser-fetch/contexts/`），不是 `knowledgeRoot` 语义下的归档产物
- 不解析 vdl / scholia 的 `settings.conf` 原始文本——一律走它们自己的 CLI
- 不改 vdl、scholia 的源码
- 不改现有 `check` 子命令的行为

---

## 7. 测试要点

| 场景 | 断言 |
|---|---|
| vdl / scholia 均一致 | 全 `OK`，退出码 0 |
| vdl 漂移 | 输出含 `DRIFT: vdl ...` 与对应 `fix:` 行，退出码 1 |
| scholia 三个字段中只有一个漂移 | 只有那一行是 `DRIFT`，其余两行 `OK`，退出码 1 |
| 命令不在 PATH 上（mock `shutil.which` 或临时改 `PATH`） | 该下游记 `SKIP`，不影响退出码 |
| 现有 `check` 子命令 | 行为不变，不受本次改动影响 |
