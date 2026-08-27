---
title: browser-fetch CLI 化——去 MCP、三 skill 迁移、extract-url 归档
migrated: false
---

# browser-fetch CLI 化：设计

## 背景

`tools/browser-fetch-mcp` 当初立项的理由是"常驻进程持有 warm Playwright context + 登录态，摊掉每次调用的冷启动和 cookie 解密成本"，实验测得热复用比冷启动快约 26 倍。

这个收益在生产路径上从未兑现。三个消费者（clip-url、sync-xtimeline、sync-ytchannel）没有一个走 agent 的 MCP 工具调用，全都是自己写的 Python wrapper 脚本（`mcp_fetch_client.py`、`mcp_timeline_client.py`、`mcp_channel_client.py`、`mcp_debug_client.py`、`chrome_profile_config.py`、`detect_xcom_chrome_profile.py`），以 `python3 xxx.py <args>` 被调用，输出文本行给 agent 读。MCP 只活在这些脚本内部，当进程间协议用。

而每个 wrapper 都在**单次调用函数内部**进 `stdio_client`——每抓一次就冷启一个 browser-fetch-mcp 进程（venv → Playwright → 抓 → 全销毁）。sync-xtimeline 有 N 个账号就冷启 N 次。

同时，Phase A 设计里记的跨平台约束仍然成立：MCP 化只覆盖有 MCP client 的平台。而实际的拦路虎比"平台有没有 MCP client"更低一层——每台目标机器的 ambient python 必须装有 `mcp` SDK，wrapper 才能 import。

结论：MCP 这一层今天既没带来性能收益，又构成跨平台障碍。**拆掉它是纯赚的**——进程模型今天就已经是一次性的，改成 CLI 直接调用只会更快，没有性能代价可付，代价已经付过了。

## 决策

| 决策 | 选择 |
|---|---|
| 进程模型 | 只做 CLI，一次调用一个进程。常驻 daemon（原 Phase C 的热复用部分）明确不在本次范围，另议 |
| MCP 去留 | 删除。不保留双传输 |
| 核心逻辑暴露形态 | 独立 CLI 可执行文件，skill 脚本 subprocess 调用（方案 A） |
| extract-url / clip-url 收敛 | 保留 clip-url 名字，extract-url 归档 |
| 多平台范围 | 三个 skill 全部多平台化 |
| 平台清单 | 沿用 extract-url 既有的四个：claude / codex / hermes / pi。不扩到 hskill 的另外三个 target（cursor / openclaw / opencode），那三个从无补丁先例 |
| tool 改名 | `browser-fetch-mcp` → `browser-fetch` |

### 被否掉的方案

**B. 做成 pip 库，skill 脚本直接 import。** 最快，无进程边界，无序列化。但 skill 脚本跑在 ambient python，browser-fetch 需要 playwright 和自己的 venv；要 import 就得把 playwright 装进 ambient python，现在的 venv 隔离和 `browser-fetch.sh` 的自愈式安装全部作废，跨平台安装反而更脆——与本次的四平台目标直接冲突。

**C. 取消 skill 脚本，SKILL.md 里让 agent 直接 bash 调 CLI。** 代码最少。但 vault 路径计算、URL 去重、账号游标这些 skill 特有逻辑今天住在 `vault_config.py` / `cursor.py` 里，没了 wrapper 无处安放——要么塞进共享 CLI（三个消费者的业务逻辑会在共享层互相纠缠），要么让 agent 自己算（不可靠）。

方案 A 胜出的理由：跟今天的调用形状最接近（skill 脚本本来就是被 subprocess 调的），改动收敛在 wrapper 内部，并且保住"共享层只管抓取、skill 层管自己的业务"这条边界。

## CLI 接口面

八个 MCP 工具一对一映射成子命令。不合并、不重新设计参数语义——重设计会让三个 skill 的改造从"换调用方式"变成"换行为"，风险不成比例。

```
browser-fetch article  <url> --out <dir> [--chrome-profile P] [--format path|json]
browser-fetch page     <url> [--auth] [--chrome-profile P]
browser-fetch timeline <profile_url> [--max 20] [--chrome-profile P]
browser-fetch channel  <channel_url> [--max 30] [--chrome-profile P]
browser-fetch eval     <url> --js-file <path> [--chrome-profile P]
browser-fetch profile  get | set <path> | list --host-key K... --cookie-name N...
```

一处偏离原签名：`eval` 的 JS 代码走 `--js-file` 或 stdin，不走 argv。自优化 subagent 迭代的是多行 JS，塞进命令行参数是引号地狱。

### 输出契约

stdout 只有一行 compact JSON，就是原 MCP 工具返回的 dict，字段一个不改。wrapper 的解析逻辑与今天从 `structuredContent` 取值等价，改动量最小。人类可读的进度信息一律走 stderr，不污染 stdout。

### 错误契约

CLI 化必须新增的东西。MCP 侧原本靠抛异常 + `isError` 一档处理，wrapper 只能靠匹配错误文本猜类别。CLI 分两档：

| 退出码 | 语义 | 场景 |
|---|---|---|
| 2 | 调用方用法错，重试无用 | `--auth` 未给 profile；x.com URL 未给 profile；URL scheme 非 http/https。今天都是 `ValueError` |
| 1 | 抓取运行时失败，值得重试或走自优化 | 页面超时、cookie 失效、站点结构变更 |
| 0 | 成功 | stdout 为 JSON |

两种失败都往 stderr 写人类可读消息，stdout 保持空。

这一档区分让 sync-xtimeline 的批量循环能正确决定"跳过这个账号继续下一个"还是"整批中止"——今天做不到。

### 明确不做

内部代码继续用 `playwright.async_api`，不改回 sync。async 当初是 FastMCP 的 event loop 强加的约束，CLI 化后约束消失，但改回 sync 意味着重写 extractors 和抓取逻辑近两千行，收益只是少一层心智负担。CLI 入口用 `asyncio.run()` 包一层即可。

## 包结构

目标形态在仓库里有现成先例：`tools/roster/` 和 `tools/hub/` 就是纯 CLI tool，同样的 `pyproject.toml` + `tool.json` + `.sh` 启动器 + venv 自愈安装。roster 已经是 sync-* 系列的共享 watchlist。browser-fetch 要做的是"变成第二个 roster"，不发明新形态。

```
tools/browser-fetch/
  pyproject.toml          # name/scripts 改名；删掉 mcp 依赖
  tool.json               # name/extraPaths/uninstallPaths/configPaths 全部改名
  browser-fetch.sh        # 启动器改名；新增一次性数据目录迁移
  browser_fetch/
    cli.py                # 新增：argparse 子命令 -> 调 core -> JSON 到 stdout
    core.py               # 从 server.py 剥出，纯业务函数，零 MCP 依赖
    config.py cookies.py extractors.py images.py
    markdown.py pacing.py pacing_log.py profiles.py    # 一行不改，只改包名 import
    server.py             # 删除
  tests/
```

**剥离动作比听起来小。** server.py 783 行里，八个工具函数上面只有一个 `@mcp.tool()` 装饰器，函数体本身完全不知道 MCP 的存在；辅助函数（warm context 管理、profile key 哈希、x.com 抓取）也是纯 Python。剥离 = 去掉装饰器、删掉 `mcp` 的 import 和 `main()`、改模块名。真正新写的代码只有 `cli.py`。

删掉 `mcp>=2.0.0` 依赖顺带解决一个既有尴尬：clip-url 的 wrapper 跑在 ambient python 的 mcp 1.28.1 上（字段 camelCase），tool 自己的 venv 是 mcp 2.0（字段 snake_case），两边命名不一致需要各自适配。这类问题整个消失。

## 数据目录迁移

改名要先付的账。当前机器实际状态：`~/.hskill/browser-fetch-mcp/contexts/` 下有 23 个目录，是各 Chrome profile 对应的 Playwright persistent context——**站点登录态实际落盘在这里**。改名后目录失联，表现是所有需要登录的站点（x.com、公众号）静默退回未登录，不报错，只抓回登录墙页面。

**做法：在 `browser-fetch.sh` 启动时做一次幂等迁移**——老目录存在且新目录不存在就 `mv`。十几行，单机个人工具，够了。同时把测试用的环境变量 `BROWSER_FETCH_MCP_DATA_DIR` 改名为 `BROWSER_FETCH_DATA_DIR`。

已考虑并否掉的替代：代码里留双路径 fallback（分支永远删不掉，两个路径名长期共存）；干脆不改名（名字持续误导，半年后读到还会去找 MCP server）。

## 三个 skill 的改造

### wrapper 层

六个 MCP client 脚本改成 subprocess 调 CLI：

| skill | 脚本 |
|---|---|
| clip-url | `mcp_fetch_client.py`、`mcp_debug_client.py`、`chrome_profile_config.py`、`detect_xcom_chrome_profile.py` |
| sync-xtimeline | `mcp_timeline_client.py` |
| sync-ytchannel | `mcp_channel_client.py` |

改造性质：把 `async with stdio_client(...)` + `session.call_tool(name, args)` 换成 `subprocess.run([cli, subcmd, ...])` + `json.loads(stdout)`。

**硬约束：函数签名和返回值一律不变。** 上游调用者（`fetch_new_tweets.py`、`sync_channels.py`、以及 SKILL.md 里的流程描述）一行都不改，改动完全关在 wrapper 内部。

`browser_fetch_mcp_locate.py` 改名为 `browser_fetch_locate.py`，查找目标从 `browser-fetch-mcp.sh` / `~/.local/bin/browser-fetch-mcp` 改为 `browser-fetch`。它在三个 skill 里各有一份自包含副本，三份都要改。SKILL.md 里引用该脚本的 preflight 步骤和错误文案（含 `hskill install --tool browser-fetch-mcp` 这句）同步更新。

三个 skill 从此都不再要求 ambient python 装 `mcp` SDK。这是四平台的实质解锁点。

### 平台补丁

**sync-xtimeline 和 sync-ytchannel 不派发 subagent。** 已核对：sync-ytchannel 的 SKILL.md 零次提及 subagent；sync-xtimeline 唯一一次提及是明确写着"不派发 subagent——纯文本翻译不需要隔离"。两者全程 `python3 scripts/xxx.py`。因此 CLI 化一旦完成，这两个 skill 天然平台无关，补丁①对它们为空，多平台化成本接近于零，剩下的只是在目标平台跑一次确认。

**只有 clip-url 需要真补丁**，它有三个 subagent 派发点（Subagent 1 抓取 / Subagent 3 自优化 / Subagent 2 打标翻译）。它的 SKILL.md 正文已经写成平台中立（"按当前平台的 subagent 派发机制派发"），缺的只是 `platforms/` 四个文件，以及初始化时加载补丁那一步。

新增 `skills/research/clip-url/platforms/`：

- `SKILL.claude.md`、`SKILL.pi.md`——从 extract-url 移植，两者有真实可用语法。Pi 那份的关键细节必须完整保留：`subagent({ agent: "worker", task: "<任务内容>" })`，必须同时提供 `agent` 和 `task`，只传 `task` 会报错 `Provide exactly one mode`。
- `SKILL.codex.md`、`SKILL.hermes.md`——**占位，且必须写得诚实**。

extract-url 那两份占位补丁写得像是已实现（正文一句"使用 X 平台的 subagent 派发机制"），实际是空的。本次不复制这个做法：占位文件里明确标注"未在该平台验证过，subagent 派发语法待补"，并在 clip-url 的初始化步骤里规定——agent 读到该标注时直接告知用户"本 skill 在当前平台未验证"，而不是让用户撞上语法错误再回头查。

补丁②（网页内容获取）在新架构下整个消失：CLI 自带 Playwright 和 cookie 注入，不再需要平台的 `web_fetch` 或 `curl`。Pi 补丁里"无内置抓取工具、用 curl 兜底"那段直接删除。补丁③（变量注入）只剩 `SKILL_DIR` 一个平台常量——chrome_profile 已由 browser-fetch 侧持久化，clip-url 连传都不传。

## extract-url 归档

用仓库现成的 `archive-skill` 走：移到 `skills/archived/`，从 `skills-index.json` 摘除，重新生成打包配置。

### 归档前必须抢救

`skills/research/extract-url/platforms/` 四份补丁——迁到 clip-url。这是全仓库唯一的多平台派发资产，跟着归档走就没了。

### 归档会当场制造的断头路

clip-url 的 `vault_config.py` 读 `~/.hskill/url-extract/config.json`，且配置缺失时的报错原文是"请先运行 extract-url skill 完成初始化（配置 VAULT_PATH 和固定词表）"。extract-url 一归档，这句提示指向一个不存在的 skill，用户照做会发现无路可走。

**修法：配置目录 `~/.hskill/url-extract/` 保持原地不动**（避免动已有的 Vault 路径和固定词表），改 clip-url 让它自己能完成初始化——补一个初始化流程写入 `VAULT_PATH` 和固定词表，并把 `vault_config.py` 的报错文案改为指向 clip-url 自己的初始化步骤。

配置目录名与 skill 名不一致（`url-extract` vs `clip-url`）是本次接受的遗留怪味，代价是可读性；换取的是不动用户已有数据。

## 测试策略

| 层 | 现状 | 动作 |
|---|---|---|
| core 纯函数 | `test_config` `test_cookies` `test_extractors`×3 `test_images` `test_markdown` `test_pacing` `test_pacing_log` `test_profiles` | 只改包名 import，断言不动 |
| 集成 | `test_server` `test_evaluate_js` `test_fetch_article` `test_fetch_user_timeline` `test_fetch_channel_videos` 五份，均用 `stdio_client` + `ClientSession` 驱动 server | 改成 subprocess 驱动 CLI。JSON 字段不变，换的只是驱动方式，断言基本可留 |
| CLI 层 | 无 | 新增 `tests/test_cli.py`：子命令参数解析、退出码 0/1/2 分档、`--js-file` 与 stdin 两条输入路径、`profile` 三个子命令 |
| wrapper 层 | clip-url 有 `test_mcp_fetch_client` `test_mcp_debug_client` `test_chrome_profile_config` `test_detect_xcom_chrome_profile` `test_browser_fetch_mcp_locate`；sync-xtimeline 有 `test_mcp_timeline_client` `test_browser_fetch_mcp_locate` | 改成 mock subprocess；文件随脚本改名 |
| wrapper 层缺口 | **sync-ytchannel 的 `mcp_channel_client.py` 目前无测试** | 改造时补上 |

仓库统一入口 `npm test` 覆盖 hskill CLI 行为和所有 SKILL.md 格式校验；归档改动 `skills-index.json`，由它验证。

## 实施顺序

顺序不是任意的，三处有硬依赖：

1. **先建 `tools/browser-fetch/`**（剥 core、写 cli、改包名、迁数据目录、改造测试），此阶段 MCP server 仍在旧目录存活，三个 skill 不受影响。
2. **再逐个迁 wrapper**（clip-url → sync-xtimeline → sync-ytchannel），每迁完一个跑一次该 skill 的测试。clip-url 排第一是因为它的四个 wrapper 覆盖了全部八个业务函数，能最早暴露 CLI 接口面的问题。
3. **确认三个 skill 全绿后，才删 `tools/browser-fetch-mcp/`。** 提前删会让回退失去参照。
4. **抢救 `platforms/` 四份补丁到 clip-url，并补上 clip-url 自己的初始化流程**——必须在归档之前完成，否则唯一的多平台派发资产和用户的初始化路径同时断掉。
5. **最后归档 extract-url。**

## 风险与未决

- **Codex 和 Hermes 的 subagent 派发语法今天是空白，本次无法靠读代码补齐。** 要写成真的，只能在那两个平台实际跑一次拿到语法，需要用户手动配合。本次交付的是诚实占位。
- **sync-xtimeline / sync-ytchannel 从未在非 Claude Code 平台跑过**，它们的多平台可用性是推断（基于"不派发 subagent + CLI 化后无平台依赖"），未经实测。
- **常驻 daemon（热复用）不在本次范围。** CLI 落地、看到真实痛点后再决定是否做。届时 CLI 可以退化成薄客户端，接口面不必变。
- 数据目录迁移是一次性、幂等的 `mv`；若用户在迁移前后混用新旧版本启动器，可能出现两个目录并存。单机个人工具，接受此风险，不做双向同步。
