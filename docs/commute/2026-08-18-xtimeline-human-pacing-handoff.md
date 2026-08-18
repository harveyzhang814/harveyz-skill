# 交接：实现 fetch_user_timeline 的拟人化抓取节奏

**日期**：2026-08-18
**author 模型**：Opus 5
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：设计已定稿并提交，接手方按 spec 把拟人化抓取节奏实现出来——先用 writing-plans 拆成可执行计划，再按 TDD 落地。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，若文档里有「工作流约定」章节按其开工，没有就直接开工，完成后等原 session 按「最小验收锚点」验收。

---

## 最小验收锚点

逐条实跑，全绿才算达成：

1. **测试全过且有新增**：`cd tools/browser-fetch-mcp && uv run pytest -q` 全绿，用例总数 **> 86**（交接时基线为 86 passed / 59.61s，已实跑验证）。
2. **冷却没有泄漏到校验之前**：`cd tools/browser-fetch-mcp && uv run pytest tests/test_fetch_user_timeline.py -q` 仍在 **5 秒内**跑完（交接时基线 4 passed / 1.86s）。这四个用例全部在参数校验阶段返回、从不启动浏览器；若冷却 sleep 被放在校验之前，每个用例会真睡 20-90 秒，此判据必然失败。
3. **skill 侧零改动**：`git diff staging --stat -- skills/` 输出为空。
4. **节奏可确定性复现**：`pacing.py` 的每个函数传入同一 `random.Random(seed)` 两次调用返回相同结果，且该性质有对应单测覆盖。
5. **测试不真 sleep**：新增的 `tests/test_pacing.py` 单独跑在 **2 秒内**完成（只断言返回的计划与时长数值，不执行等待）。

## 背景与现状

`sync-xtimeline` 抓 X 时间线用的是用户**本人的真实登录态**（从本地 Chrome 解密的 session cookie），但翻页动作是明显的脚本特征：`window.scrollBy` 一次跳三屏（不产生任何输入事件）、固定 800ms 间隔、账号间零间隔串行轮询、viewport 固定 1280x900。风险落点是这个真实账号——被判定为自动化的代价是限流/锁定/强制验证，不是某个可丢弃的测试号。

这轮把翻页改成贴近真人浏览的行为，用运行时长换风险：单账号 15-20 秒 → 最坏约 1.5 分钟。

**现在到哪了**：设计已定稿、已提交，**代码一行未动**。

- 当前分支 `feature/xtimeline-human-pacing`，工作区干净，领先 `staging` 一个提交（`57203bc`，只含 spec 文档）。
- 接手方**继续在这个分支上做**，不要新开分支（本仓库约定一个功能一个分支，累积全部相关改动）。
- 上一轮无关的收尾工作（tweetText 的 `innerText` → `textContent` 修复）已经提交并以 `--no-ff` 并入 staging（`0642e09` / `c65e5f4`），与本任务无关，不要再动。

## 关键决定（别改动）

这些是本次对话里用户逐个拍板的，spec 里有记录但理由分散在各处，列在这里避免接手方重新纠结或推翻：

| 决定 | 理由 |
|---|---|
| **机制全部落在 MCP 工具侧，`skills/research/sync-xtimeline/` 零改动** | 用户明确要求节奏是工具自带的默认行为，任何调用方自动享有，调用方不需要知道它存在。这是本次交接最硬的一条边界。 |
| **保持每账号一次独立浏览器启动，不复用会话** | 用户在「整个 run 复用一个浏览器」和「保持独立」之间明确选了独立，换取天然的失败隔离和逐账号落盘的游标。 |
| **watchlist / 已读游标不内化进 MCP** | 那是 sync-xtimeline 的业务状态不是浏览能力；`browser-fetch-mcp` 由 `clip-url` 共用，不应为单一消费者承担订阅语义。用户在三个选项里选了「保持现状」。 |
| **冷却用落盘时间戳跨调用实现，而不是把整批 URL 传进一次调用** | 逐账号调用才能逐个落盘游标；一次跑满 10 个账号约 25 分钟的批量调用中途失败会全丢。这个"看着像 hack"的时间戳文件是在买健壮性。 |
| **不随机化账号遍历顺序** | 工具一次只看见一个 `profile_url`，结构上看不见列表；固定顺序是很弱的信号，不值得为它把机制拆回 skill 侧。 |
| **时间预算 1-3 分钟/账号** | 用户拍板。跑满 15 轮约 80 秒封顶是**上限不是目标**——抓够 `max_tweets` 就 break，活跃账号 20 秒结束是正常的，不要为凑时长强行多滚。 |
| **只处理行为指纹** | TLS 指纹、Canvas/WebGL 指纹、Playwright 自身的 CDP 痕迹一律不碰，那是另一个量级的工程。 |

## 相关文档索引

| 路径 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-08-17-xtimeline-human-pacing-design.md` | **本次实现的权威依据，必读全文**。含常量数值、函数签名、伪代码、时间预算、错误处理、测试策略、代价与未验证项 |
| `docs/superpowers/specs/2026-08-15-watch-x-design.md` | sync-xtimeline 的原始设计（写作时还叫 watch-x），解释 `fetch_user_timeline` 当初为什么长这样 |
| `skills/research/sync-xtimeline/SKILL.md` | 唯一消费者的运行流程。**只读不改** |
| `docs/reference/testing-guide.md` | 写新测试前按仓库 CLAUDE.md 要求先读 |
| `docs/reference/git-workflow.md` | 分支命名与合并流程 |

## 受影响文件/落点

| 文件 | 动作 |
|---|---|
| `tools/browser-fetch-mcp/browser_fetch_mcp/pacing.py` | **新建**。纯决策函数 + 常量，接收 `random.Random`，不做 I/O、不 sleep |
| `tools/browser-fetch-mcp/tests/test_pacing.py` | **新建**。固定种子的确定性测试 |
| `tools/browser-fetch-mcp/browser_fetch_mcp/config.py` | 扩两个纯 I/O 函数读写 `timeline_pace.json`。**不能塞进 `config.json`**——`set_default_chrome_profile` 是整份覆写的，会把时间戳冲掉 |
| `tools/browser-fetch-mcp/tests/test_config.py` | 扩往返测试，并断言 `set_default_chrome_profile` 之后时间戳仍在 |
| `tools/browser-fetch-mcp/browser_fetch_mcp/server.py` | 改两处：`_xcom_scrape_timeline`（135 行起，滚动编舞）、`fetch_user_timeline`（454 行起，冷却）。常量 `_TIMELINE_MAX_SCROLL_ITERATIONS` / `_TIMELINE_STALL_LIMIT` 在 67-68 行，本次**不需要调整** |
| `tools/browser-fetch-mcp/tests/test_fetch_user_timeline.py` | **不扩覆盖面**，但必须保证现有四个用例仍不触发冷却 sleep |

**两个最容易踩的坑**（spec 里有，这里重点提示）：

1. 冷却必须放在**全部参数校验之后、浏览器启动之前**。放前面会让现有四个 ValueError 用例每个都真睡几十秒。
2. 回滚（backscroll）那一轮抓不到新推文是必然的，**不能计入 `stalls`**，否则会被现有计数器误判成"feed 到底了"而提前 break。

## 验证步骤

```bash
cd tools/browser-fetch-mcp
uv run pytest -q                                  # 全量，交接时基线 86 passed / 59.61s
uv run pytest tests/test_pacing.py -q             # 新增，应 < 2s
uv run pytest tests/test_fetch_user_timeline.py -q # 应 < 5s，基线 4 passed / 1.86s
```

浏览器交互本身不测（需要真实 x.com 登录态与真实页面结构，沿用现有 xcom 抽取的测试策略）。因此**实现完成后无法自证节奏在真实页面上生效**——这一步留给用户手动跑一次 `/sync-xtimeline run` 观察，不属于本次验收范围。

---

## 门禁核对（author 自查）

- 交接目的、最小验收锚点：均在。
- 「相关文档索引」5 个路径 + 「受影响文件/落点」中 4 个已存在文件：全部实跑 `ls` 核对存在（2 个标注**新建**的除外）。
- 「关键决定」7 条均附理由，接手方无需回问原 session。
- 最小验收锚点 5 条均可证伪（有具体命令、具体阈值、具体基线数字，基线为实跑所得）。
- 未写「范围铁律」：spec 的「范围」章节已给出完整 in/out 且被列为必读权威，另写一份会产生两处可能漂移的边界定义；最易越界的两条（不改 skill、不碰指纹层）已进「关键决定」。
- 未写「工作流约定」：`.hskill/handoff/config.md` 不存在，按模板规则跳过；接手方必须知道的那一条（继续留在 `feature/xtimeline-human-pacing` 分支）已内联进「背景与现状」。
