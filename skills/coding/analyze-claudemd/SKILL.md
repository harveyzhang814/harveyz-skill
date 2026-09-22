---
name: analyze-claudemd
description: "Audit a project's CLAUDE.md against 17 falsifiable criteria — ownership overlap with the skills and scripts it names, structural coherence around the main flow, and whether every instruction is actually executable by an agent. Reports blocking findings and suggestions with sources, then applies deletions only after explicit approval. Triggers: 'review CLAUDE.md', 'audit CLAUDE.md', 'slim down CLAUDE.md', 'is my CLAUDE.md bloated', 'what should I delete from CLAUDE.md', 'does CLAUDE.md duplicate my skills'."
user_invocable: true
version: "1.0.0"
---

# 评审 CLAUDE.md

拿 17 条可证伪的判据过一遍项目的 `CLAUDE.md`，指出哪些内容不该由它承担、哪些结构判断不出归属、哪些指令 agent 其实执行不了。

**这个 skill 的核心不是"精简"，是"归属"。** 长不是问题，一条知识同时活在两个地方才是问题——改了一处，另一处就在和它对着打架。所以本 skill 绝大部分时间花在读被点名的 skill 和脚本的**源文件**上，而不是读 `CLAUDE.md` 本身。

---

## 触发条件

触发本 skill：

- "评审 / 优化 / 精简 CLAUDE.md"、"CLAUDE.md 该删什么"
- "review CLAUDE.md"、"audit CLAUDE.md"、"is my CLAUDE.md bloated"
- 新接手一个项目，想知道它的 `CLAUDE.md` 有没有和现有 skill 打架

不触发（其他 skill 负责）：

- 评审 **skill 自身**的设计规范 → 用 `init-skill` 的 `references/skill-standard.md`
- 初始化分支保护与 git hooks → `init-workflow`
- 润色文风、改写措辞质量 → 本 skill 只判归属与结构，不做文字润色

---

## 判据表

17 条判据在 `references/criteria.md`（C1–C17，分五组）。Step 3 加载它逐条过，**不要凭记忆复述判据**——判据本身会演进。

---

## 执行步骤

### Step 0 — 定位评审对象

三级 fallback，命中即停：

1. 用户在调用时给了路径 → 用它（`~` 显式展开）
2. 项目根的 `CLAUDE.md` → 用它
3. 都没有 → 列出仓库里的候选（`CLAUDE.md` / `AGENTS.md` / `.claude/CLAUDE.md`）让用户选

用户已经指明对象时不要再问。确认不了就停下问一句，**不要默认挑一个开始读**。

### Step 1 — 执行前置检查

任一失败立即中止并报原因，不要带病往下走：

```bash
git rev-parse --show-toplevel     # 不在 git 仓库 → 中止（Step 2 要按仓库定位权威源）
test -f <目标文件>                  # 不存在 → 中止
git status --short                 # 非空 → 只做只读评审，Step 5 需用户先处理
```

### Step 2 — 建执行体清单

**这一步决定整次评审的成色，不能省。**

1. 从目标文件里抽出所有被点名的可执行体：skill 名、脚本路径、CLI 命令、hook、settings 开关。用 grep 抽，**不要在本 skill 里硬编码任何 skill 名单**——每个项目点名的东西都不一样。
2. 逐个定位它的**权威源**，按这个顺序找：项目内的源文件 → 该 skill 的源仓库 → 最后才是装机副本（`~/.claude/skills/`）。找到装机副本时必须再往上找一层：副本会落后，拿它当权威会同时造出两类误判——把"源里已修"读成"还没修"，把"源里缺了"读成"重复了"。核对版本号能对上再采信。
3. 逐个读完再进 Step 3。**禁止边读边下结论**：一条 `CLAUDE.md` 的约束常常同时被两三个执行体覆盖，只读第一个就判"重复"会删错东西。
4. 读不到源的执行体（外部工具、闭源 CLI）单独列出来，它们相关的判据一律降级成 `[需核实]`，不出阻塞结论。

### Step 3 — 逐条比对判据

读 `references/criteria.md`，C1–C17 逐条过。三件事必须做到：

- **先判文档形态**：C11–C14 那组结构判据只适用于"流程主导型"文档（大部分内容围绕一条主流程展开）。不是流程主导的文档，这四条整组跳过并说明，不要硬套 Step N。
- **每条结论挂证据**：证据形如 `<执行体源文件>:<行号>`，写明它在那儿说了什么。
- **推断与读到分开**：读到的写读到的，推出来的标 `[Agent 推断]`，没查的标 `[需核实]`。

### Step 4 — 输出评审报告

按判据分组，不按发现顺序混排。分三档：

```
━━━ 归属（C3–C8）━━━
❌ CLAUDE.md:217  simulate-user 的"非 jsdom"理由是它自己 description 的中译
   证据：skills/.../simulate-user/SKILL.md:3
⚠️ CLAUDE.md:265  --spec 绝对路径要求，skill 源里确实没有（C7：该改上游）
   证据：skills/.../describe-node/SKILL.md:16-18 无此约束

━━━ 结构（C11–C14）━━━
✓ 流程主导型，Step N 编章完整

阻塞 1 / 建议 1 / 通过 15
```

- **阻塞**：两处都写、改一处会打架的（C3/C4/C5），以及 agent 执行不了的指令（C2）。
- **建议**：结构类（C11–C14）、措辞类（C16），不改也能用。
- 报告末尾给下一步：确认哪几条要删。

### Step 5 — 应用确认过的修改

**默认不改任何文件。** 用户明确点头之后才进这一步：

1. 列出将删/将改的**具体条目**（文件:行号 + 删后留什么），等 y/n。
2. 按项目自己的分支规范落盘。不在受保护分支（`main` / `master` / `staging`）上直接改；项目有合并脚本就用脚本，没有就交回用户手动合并。
3. **不 push、不发布。**
4. C7 命中的条目（该改上游 skill 的）**这一步不动**：上游改完到下游生效之间有窗口期，窗口期内删掉，这条知识在真实环境里会有一段时间完全不存在。把它单独列出来交给用户决定先后。

---

## 不在范围内

- **润色文风与措辞质量**——只判归属与结构。
- **修上游 skill**——C7 只负责指出"这条该由 skill 承担"，改不改、什么时候改由用户定。
- **评审 skill 自身的设计**——那归 `init-skill` 的 `skill-standard.md`。
- **批量评审多个仓库**——一次一个 `CLAUDE.md`。
