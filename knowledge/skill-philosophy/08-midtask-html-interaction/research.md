> 关联文档：[[principle]]
> 示例场景：一个 Skill 在长任务执行到一半时，生成了 3 个候选方案（如 3 种重构/设计/迁移策略），需要向用户展示并收集选择，然后据此继续执行。下文每种思路的"示例写法"都用这同一个场景对比。

## 研究对象

| 生态 | 研究对象 | 定位 |
|------|---------|------|
| G stack | `design-shotgun` | 视觉设计头脑风暴：生成多个设计变体，开对比板，收集结构化反馈，迭代 |
| Superpowers | `brainstorming/visual-companion.md` | brainstorming 技能内嵌的浏览器可视化伴侣，通用基础设施，非某个具体任务专用 |
| MSkill | `improve-codebase-architecture` | 扫描代码库，把重构候选方案渲染成可视化 HTML 报告，再对选中的方案做访谈式深挖 |

三者都不是"最终交付物"用途的 HTML——都发生在任务执行的中途，用来展示中间结果或收集用户的下一步决策，符合本次研究命题的边界。

---

## 一、深度解析

### 1. G stack `design-shotgun`

**核心机制**：Step 4"Comparison Board + Feedback Loop"里，用专用的 `design` 二进制生成对比板并起一个本地 HTTP 服务器：

```bash
$D compare --images "A.png,B.png,C.png" --output board.html --serve
```

服务器随机端口启动、自动打开浏览器、返回 `BOARD_URL`。Claude 不直接问"你喜欢哪个"，而是用 AskUserQuestion 仅作为**阻塞等待机制**（"Do NOT use AskUserQuestion to ask which variant the user prefers. The comparison board IS the chooser."）。用户在网页上评分、评论、点击 Submit/Regenerate 后，前端把结果写成本地文件：

- `feedback.json`（最终选择）
- `feedback-pending.json`（要求重新生成）

Claude 下一轮读取这两个文件之一来判断分支。如果用户点了 Regenerate，Claude 生成新变体后通过 `curl -X POST .../api/reload` 把新 HTML **推送到用户已经打开的同一个标签页**，无需用户重新打开链接，然后再次 AskUserQuestion 等待，循环直到 `feedback.json` 出现。

**关键设计决策**：
- 反馈是结构化 JSON（`preferred`/`ratings`/`comments`/`overall`），不是自由文本——机器直接可读，不需要用户口头转述。
- 显式声明"轮询兜底"路径：服务器起不来就退化为内联展示图片 + AskUserQuestion 纯文本兜底。
- 产物强制写到 `~/.gstack/projects/$SLUG/designs/`，永不写入项目目录或 `/tmp`——因为这是"用户数据"，要跨分支/跨会话持久化。
- 收到反馈后必须再用 AskUserQuestion 向用户复述理解结果确认一遍，才写 `approved.json`。

**原文关键句**：
> "This command generates the board HTML, starts an HTTP server on a random port, and opens it in the user's default browser. **Run it in the background** with `&` because the server needs to stay running while the user interacts with the board."

解读：中途 HTML 交互被当作一个需要显式生命周期管理的**子进程**，而不是一次性文件写入——这是它和 MSkill 静态报告最根本的区别。

### 2. Superpowers `brainstorming/visual-companion.md`

**核心机制**：不是为某个具体任务定制的功能，而是 brainstorming 技能里可复用的通用能力。启动一个带 session key 的本地服务器：

```bash
scripts/start-server.sh --project-dir /path/to/project --open
# 返回 { "url": "http://localhost:PORT/?key=...", "screen_dir": "...", "state_dir": "..." }
```

Claude 把 HTML **内容片段**（不是完整文档，服务器自动套模板）写入 `screen_dir` 里的新文件，服务器"watches a directory for HTML files and serves the newest one"——即文件系统本身就是通信协议，Claude 不需要调用任何 API，只需要写文件。用户在浏览器里点击选项，点击事件被记录成 JSONL 追加到 `state_dir/events`；Claude **在下一轮对话**里读取这个文件，与用户当轮打的字合并作为反馈。

**关键设计决策**：
- 有一条明确、可操作的**触发判据**："would the user understand this better by seeing it than reading it?"——按问题而非按会话决定要不要开浏览器，UI 相关的问题也不必然是"视觉问题"（举了"你想要什么样的向导"vs"这几个向导布局哪个感觉对"的对比例子）。
- 安全性内建：URL 带 session key，服务器拒绝没有 key 的请求，防止局域网内其他人窥探/注入。
- 明确要求"回到终端时推一个 waiting 屏幕清空旧内容"，防止用户对着一个已经过时的选择发呆。
- 文件命名规则："Never reuse filenames"——每屏都是新文件，方便追溯，也让"服务器展示最新文件"这个协议不会因为覆盖写入而产生竞态。
- Claude 结束当前轮次时必须提醒用户 URL（每一步都提醒，不只是第一次），把"等待用户"的动作交给对话轮次边界，而不是某种阻塞调用。

**原文关键句**：
> "The terminal message is the primary feedback; `state_dir/events` provides structured interaction data."

解读：浏览器点击是结构化数据的**补充**，终端文字才是主渠道——即便有结构化回传机制，Superpowers 仍然不完全信任它，要求和文字对齐。这跟 G stack 把 `feedback.json` 当作唯一权威来源的态度不同。

### 3. MSkill `improve-codebase-architecture`

**核心机制**：探索阶段（Explore 子代理找架构摩擦点）结束后，把候选重构方案渲染成**单个自包含的静态 HTML 文件**，写到系统临时目录（`$TMPDIR` 或 `/tmp`），用 `open`/`xdg-open`/`start` 打开：

> "Write a self-contained HTML file to the OS temp directory so nothing lands in the repo... Open it for the user... and tell them the absolute path."

页面用 CDN 版 Tailwind + Mermaid，每个候选方案一张卡片：涉及文件、问题、方案、收益、Before/After 对比图、推荐强度徽章。写完文件后，**没有任何服务器、没有任何回传机制**——Claude 直接在终端问一句大白话："Which of these would you like to explore?"，用户口头回答，Claude 据此进入下一阶段（调用 `/grilling` 技能做访谈式深挖）。

**关键设计决策**：
- HTML 是纯粹的**展示介质**，不承担任何交互闭环职责；选择动作完全发生在终端里，跟没有 HTML 时没有本质区别，只是决策时看到的是图文并茂的卡片而不是文字列表。
- 明确要求"不要往仓库里写文件"——因为这是一次性分析产物，不是项目资产。
- 图表策略上强调**混合**手绘 SVG 与 Mermaid，"不要让每张图都长一个样子，多样性本身就是重点"——极度看重可视化本身的说服力和信息密度，而不是交互能力。
- 报告结尾有"Top recommendation"区块，即 Claude 已经替用户做了一轮预筛，HTML report 既是选项呈现也是论证载体。

**原文关键句**：
> "No paragraphs of explanation. If the diagram needs a paragraph to be understood, redraw the diagram."

解读：这份 HTML 报告存在的唯一理由，是文字/终端做不到"一眼看出架构问题"的信息密度——即典型的"内容本身是视觉性的"场景，而不是想解决"确认交互不够顺滑"的问题。

---

## 二、核心思路提炼

### 思路一：静态快照展示式（MSkill `improve-codebase-architecture`）

**核心逻辑**：HTML 只解决"看得清楚"，不解决"回传得顺畅"——选择动作留在终端，零基础设施。

**特征列表**：
- 单文件、自包含（CDN 引入库，无本地依赖），写到系统临时目录，非项目目录。
- 用 OS 原生 `open` 打开，不起任何进程，写完即结束，没有生命周期要管理。
- 无任何机器可读的回传通道；用户看完后仍用自然语言在终端里说选哪个。
- 视觉呈现本身要做到"自解释"（图表替代大段文字），因为它是论证工具，不是问卷。

**适用场景**：候选方案数量少（2-6 个）、比较维度是空间/结构性的（架构图、布局、依赖关系），且后续决策仍然是"讨论式"的——用户选完之后大概率还要追问细节，终端对话本来就要继续。

**广度/深度策略**：广度优先、深度靠后置——HTML 报告负责把候选方案"摊开看全"，深度访谈（如 `/grilling`）作为独立的下一阶段接管，两者不共享同一交互通道。

**边界**：候选方案会被反复迭代重新生成（比如设计变体要来回改三四轮）时不适用——每次改动都要重新 `open` 一个新文件，用户体验会很割裂；也不适用于选项需要多维度打分/评论这种结构化反馈量大的场景，纯口头转述会丢信息。

**示例写法**（同一场景：3 个重构方案）：
```markdown
Write a self-contained HTML file to $TMPDIR/refactor-review-<timestamp>.html.
Each candidate is a card: files touched, problem, solution, before/after diagram,
recommendation badge (Strong / Worth exploring / Speculative).
End with a "Top recommendation" section.
Open it with `open <path>` (or xdg-open/start) and print the absolute path.
Do NOT propose an implementation yet. Ask the user in the terminal:
"Which of these would you like to explore?"
```

### 思路二：通用会话服务器式（Superpowers `brainstorming/visual-companion`）

**核心逻辑**：把"要不要用浏览器"变成一个逐问题判断的**策略开关**，底层用一套可复用、带鉴权、协议是"写文件"的轻量服务器统一支撑，终端文字仍是反馈的主渠道，浏览器数据是补充。

**特征列表**：
- 服务器是通用基础设施（不属于任何具体功能），靠"写新 HTML 文件到 screen_dir" 驱动画面更新，靠"读 state_dir/events" 驱动状态回传——协议极简，双方都只对文件系统读写。
- 有明确的触发判据（"这道题用看的是不是比用读的更容易懂"），避免滥用浏览器交互。
- 安全性是一等公民：URL 带随机 session key，防止局域网嗅探/误连。
- 每屏文件不复用文件名；离开可视化阶段时主动推一个 "waiting" 占位屏，防止用户盯着过期内容。
- 反馈闭环靠对话轮次边界完成："结束当前轮次 → 用户在浏览器操作 + 在终端回话 → 下一轮读事件文件"，不依赖任何真正的推送/回调。

**适用场景**：整个任务本身就是探索性、多轮次的（brainstorming 式流程），过程中会反复在"这个问题该用图看"和"那个问题该用文字聊"之间切换，需要一套贯穿全程、可长期复用的轻量设施，而不是为单次任务定制。

**广度/深度策略**：按问题粒度切换广度/深度——每一屏只回答一个具体问题（一次只呈现 2-4 个选项），靠多轮小步快跑逐步收敛，而不是一次性摊开所有候选方案。

**边界**：不适合需要"立即看到我刚才操作生效"的强实时场景（它靠新文件覆盖 + 用户回到终端触发下一轮，不是真正的双向推送）；一次性、单轮次的任务用这套基础设施是杀鸡用牛刀（起服务器、管理 session key 的成本用不回来）。

**示例写法**（同一场景：3 个重构方案）：
```markdown
Check server alive (or start it), then write screen_dir/refactor-candidates.html:
<h2>Which refactor direction should we pursue?</h2>
<div class="cards">
  <div class="card" data-choice="a" onclick="toggleSelect(this)">...before/after diagram...</div>
  <div class="card" data-choice="b" ...>...</div>
  <div class="card" data-choice="c" ...>...</div>
</div>
Tell the user: "Showing 3 refactor candidates at <URL>. Take a look and let me
know what you think, or click to select." End turn.
Next turn: read state_dir/events, merge with terminal reply, then push a
waiting.html screen before starting the grilling loop in the terminal.
```

### 思路三：专用双向反馈服务器式（G stack `design-shotgun`）

**核心逻辑**：把浏览器当作**真正的选择器**而不是展示板——结构化反馈（评分/评论/选择）由前端直接写成机器可读的 JSON，Claude 只负责阻塞等待和解析，且支持"用户要求重来"时不换标签页地原地刷新。

**特征列表**：
- 一个任务专属的二进制/服务承担全部渲染 + 服务 + 反馈收集职责（`$D compare --serve`），不是通用基础设施。
- AskUserQuestion 被重新定义为"纯粹的阻塞等待"，而不是"向用户提出选择"——选择这件事完全交给网页做。
- 反馈是强 schema 的 JSON（`preferred`/`ratings`/`comments`/`overall`/`regenerated`），两种文件语义分开（`feedback.json` = 最终提交，`feedback-pending.json` = 要求重来）。
- 支持"原地热更新"：改动后用 `POST /api/reload` 把新内容推给已打开的同一个标签页，用户不用重新点链接。
- 收到反馈后强制再做一次"我理解的是……对吗"的复述确认，才落盘 `approved.json`——不完全信任结构化数据本身。
- 产物路径强制脱离项目目录，写入用户级持久化目录，明确"这是用户数据不是项目文件"。

**适用场景**：候选方案会被反复要求"重新生成"（设计探索本质上是迭代的），且反馈需要结构化维度（每个选项打分、逐项评论）——文字转述会严重损失信息量的场景。

**广度/深度策略**：深度优先，单个候选方案上反复打磨（regenerate/remix 循环），而不是一次性摊开一堆选项走马观花。

**边界**：需要一个专用二进制/服务端组件，实现和维护成本最高；如果只是想让用户"选一个"而不需要来回改，这套双向闭环是过度设计；对没有图形界面/无法起本地端口的环境（纯 headless CI）不适用，必须有轮询兜底路径。

**示例写法**（同一场景：3 个重构方案）：
```bash
$D compare --images "A.png,B.png,C.png" --output board.html --serve
# → BOARD_URL: http://127.0.0.1:N/boards/<id>/
```
```markdown
AskUserQuestion (blocking wait, not "which do you prefer"):
"I've opened a comparison board: <BOARD_URL>. Rate them, leave comments,
click Submit when done — or Regenerate if you want new candidates."

# Next turn: check feedback.json / feedback-pending.json
# feedback.json found → read {preferred, ratings, comments, overall}, confirm, save approved.json
# feedback-pending.json found → regenerate, reload same tab via POST .../api/reload, ask again
```

---

## 三、对比

| 维度 | 静态快照展示式（MSkill） | 通用会话服务器式（Superpowers） | 专用双向反馈服务器式（G stack） |
|------|------------------------|--------------------------------|--------------------------------|
| 是否起服务器 | 否，纯静态文件 | 是，通用轻量服务器 | 是，任务专属服务/二进制 |
| 回传机制 | 无，用户口头转述 | 半结构化：点击事件写 JSONL，终端文字仍是主渠道 | 强结构化：JSON schema，前端直接提交 |
| 是否支持免刷新更新 | 否，每次都是新文件+重新 open | 部分：写新文件由服务器自动识别最新 | 是：HTTP POST 原地 reload 同一标签页 |
| 复用性 | 一次性、任务内嵌 | 通用基础设施，跨技能复用 | 任务专属，依赖专用二进制 |
| 安全考虑 | 无需考虑（无网络服务） | 显式 session key 鉴权 | 未在文档中强调（本地随机端口） |
| 产物归属 | 系统临时目录，即弃 | 项目目录 `.superpowers/brainstorm/`，可持久化 | 用户级目录 `~/.gstack/projects/`，强制持久化 |
| 触发判据 | 隐含：候选方案是空间/结构性的 | 显式："看比读更容易懂"逐问题判断 | 隐含：视觉设计天然需要视觉比较 |
| 失败降级路径 | 不需要（本来就不依赖服务） | 未显式讨论 | 显式："轮询兜底"：服务器起不来就内联展示+纯文本问答 |
| 实现/维护成本 | 最低 | 中——一次性建好可长期复用 | 最高——专属二进制+HTTP 协议+状态机 |

---

## 四、回答 `principle.md` 的悬而未决问题

### 1. 本地文件 vs 启动服务器

**研究结论**：三个生态给出了三种不同的答案，且都是有意为之，不是能力局限：

- MSkill 选择**完全不起服务器**——因为它的交互闭环本来就不需要机器回传，静态文件已经足够，起服务器纯属浪费。
- Superpowers 选择**通用服务器 + 文件系统协议**——因为它要跨多个问题、多轮反复使用，服务器是长期摊销的基础设施投入，用"写文件驱动画面更新"把协议复杂度降到最低。
- G stack 选择**任务专属服务器 + HTTP 协议**——因为它需要"原地刷新同一标签页"这种静态文件做不到的体验，且反馈需要强 schema，愿意为此承担专属二进制的维护成本。

取舍的核心变量是：**candidate 是否会被反复重新生成**（决定要不要"免刷新更新"）和**反馈是否需要结构化数据**（决定要不要机器可解析的回传通道）。两者都为"否"就该用 MSkill 的静态文件方案；两者都为"是"且值得为单个功能投入专属服务，用 G stack 方案；如果是要长期在多个问题上复用同一套能力，走 Superpowers 的通用服务器路线最省成本。

### 2. 双向回传机制

**研究结论**：没有一个生态真正做到"用户点击后 Claude 立刻被唤醒"（三者都不依赖 webhook/回调打断当前轮次）。真实的共同模式是：**前端把选择写成文件，Claude 的轮次先以某种方式结束（AskUserQuestion 阻塞、或提示用户回终端说话），下一轮读文件**。区别只在于：

- MSkill：完全没有文件回传，纯口头转述，最简单但信息损失最大。
- Superpowers：有结构化文件（JSONL 点击事件），但明确说"终端文字才是主渠道，浏览器数据是补充"——不完全信任浏览器回传。
- G stack：有强 schema 的 JSON 文件，且把它当作**唯一权威来源**，AskUserQuestion 只是等待器不是提问器；但收到后仍要求二次口头确认——本质上是"信任回传数据的内容，但不信任回传数据没有歧义"。

所以答案是：**机器可读文件回传是可选的增强项，不是必需项**；即便做了结构化回传，也几乎都保留了终端确认这一步作为兜底，没有一个生态完全把决策权交给浏览器端数据而不做二次校验。

### 3. 什么任务值得用 HTML 而不是终端文本

**研究结论**：三者中只有 Superpowers 把这个问题写成了一条**显式、可操作的判据**："would the user understand this better by seeing it than reading it?"——并且强调这是**逐问题**判断，不是逐会话判断（同一个 brainstorming 过程里，有的问题该用浏览器，有的该留在终端）。MSkill 和 G stack 都没有写出判据，但从场景可以反推出隐含判据是一致的：**内容本身有空间/图形结构**（架构依赖图、UI 视觉设计）时才值得。

三者都不支持"只要任务够长就该有 HTML 进度视图"这种更宽泛的用法——没有一个生态把 HTML 用作纯粹的"进度条"或"防止用户等待焦虑"的工具，全部三个案例里 HTML 都直接承载着需要用户看懂/挑选的**决策内容**本身。也就是说，研究倾向明确支持 `principle.md` 悬而未决问题 3 中的**选项 A（内容驱动的特例工具）**，而非选项 B（长任务的通用基础设施）——三个生态无一例外只在"内容天然可视化"时引入 HTML，从未把它当作长任务的默认进度展示层。

---

## 研究完成

三个生态呈现出一条清晰的复杂度—能力光谱：MSkill（零基础设施、纯展示、终端确认）→ Superpowers（通用轻量服务器、半结构化回传、按问题粒度判断）→ G stack（专属服务器、强结构化双向闭环、支持原地热更新）。没有哪种是"更先进"的替代关系——它们对应的是候选方案是否需要反复重新生成、反馈是否需要结构化数据这两个变量的不同取值，选型应该顺着这两个变量走，而不是默认选最复杂的那一种。

研究结论已回写 `principle.md`。
