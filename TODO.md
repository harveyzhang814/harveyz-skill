# TODO

## 🚧 待开发

### 统一存储根写入代理（特权隔离后台）
**优先级**: P3 | **日期**: 2026-09-14

背景：`learn-video`/`clip-url`/`sync-xtimeline`/`sync-ytchannel`/`sync-website` 五个 skill 共用 `knowledgeRoot` 写产物。这次排查发现，当执行环境（如 Agent Canvas 宿主的 Claude Code 会话）对 `knowledgeRoot` 所在目录没有写权限时，agent 有过"静默把 `knowledgeRoot` 改到别的路径"来绕过失败的先例——本轮已经用两个动作缓解：① 把默认根从 `~/Documents/knowledge` 换成 `~/knowledge`（`$HOME` 下普通目录不受 macOS TCC 对 Documents/Desktop/Downloads 的隐私保护限制，从根源避免权限问题）；② 在五份 SKILL.md 里加了"写入失败必须停下问用户，禁止擅自换路径"的护栏指令。

这两步是本期够用的最小修复。更彻底、但代价也更高的方向是做权限隔离：写一个独立的小后台程序，只有它持有 Full Disk Access（如果以后确实需要放在受保护目录下），路径硬编码在程序里（不从 agent 可写的配置文件读取），agent 只能通过它暴露的固定语义接口（如"写 `<root>/articles/<hash8>/`"）间接写入，自己拿不到高权限、也改不了目标路径——利用 macOS TCC 授权绑定代码签名身份的特性，后台程序被重新构建/签名后旧授权失效，必须人工在系统设置里重新同意，从而把"agent 能不能把写入路径导向别处"这件事提高到"需要人工介入"的门槛。

当前规模下① + ②已经够用，这一项只在以后出现"确实需要放在受保护目录下"或"需要更强审计/隔离"的场景时才启动。

---

### 按 description-trigger-role 研究优化所有 skill 的 description
**优先级**: P3 | **日期**: 2026-07-04

根据 `knowledge/skill-philosophy/07-description-trigger-role` 的研究结论，审视并优化 `skills/` 下所有 Skill 的 description 字段：移除操作内容与工作流摘要，改写为纯触发条件语言，补充合法额外信息（症状/情境/可达性声明）。

---

### [x] 调整 extract-url 标签生成顺序为先原文后翻译
**优先级**: P1 | **日期**: 2026-07-08

`extract-url` skill 当前 Subagent 2 流程是先翻译全文（阶段 1），再基于译文生成 `description`/`tags`/`candidate_tags`（阶段 2）。应改为先基于原文生成 `description` 和 `tags`/`candidate_tags`，再翻译全文，调整 SKILL.md 中「翻译 + 打标」步骤的阶段顺序与提示文案。

---

### [x] 调研 extract-url 索引存储方案
**优先级**: P2 | **日期**: 2026-07-17

extract-url 目前用集中式 SQLite（`url-index.db`）维护所有文章的索引。调研方向：改成每个文章文件夹下维护独立的 `meta.json` 是否更合适，对比两种方案在查询、并发写入、迁移成本、与 Obsidian 生态兼容性等维度的优劣，产出结论后再决定是否实施。

---

### 为 manage-dir 添加文档 formatter 维护机制
**优先级**: P1 | **日期**: 2026-08-01

`manage-dir` skill 目前缺少针对每份文档的 formatter 维护机制。在实际使用过程中会沉淀大量方法论，包括对文档本身的定义方式——例如「Explanation」这类分类标签不够直观地表达出人管理视角与 Agent 方法论视角之间的侧重差异。这类定义应放进对应文档的 formatter 中管理，而非停留在笼统的分类标签上。

---

### handoff 验收新增回归面核对
**优先级**: P2 | **日期**: 2026-10-13

`handoff` skill 的 accept 阶段（Phase 3）目前只跑交接文档里点名的最小验收锚点，锚点没点名的既有回归测试没有任何环节会去跑。agent-canvas 10-09「统一 PTY 注入」那次：交接锚点只点名了新功能的 6 条 E2E，没有回归草稿框原有的 12 个 E2E，author 和 accept 都只跑锚点点名的，合入 staging 后才被追问补测，补测又查出 4 个脚本因新锚点过时、3 个是 harness 既有的红。

要做的：在 Phase 3 第 3 步（跑最小验收锚点）之后新增「回归面核对」。锚点跑完后，用 `git diff $(git merge-base <集成分支> HEAD)..HEAD --name-only` 取这次实际改动面（不用 `<集成分支>..HEAD`，集成分支前进后会把别人合入的改动混进来），找出被波及组件现有的回归测试，锚点没点名的也跑；红了先在分叉点上跑同一条命令归因，本次改动引入的按回归打回，既有的红在验收记录里写明；锚点遗漏同样记入验收记录。

需协调的一点：Phase 3 第 3 步把最小验收锚点称为「唯一固定依据」。回归红是产品真的坏了，不算临时加判据，措辞要把这层说清。

已定的范围：只改 accept 阶段；不加 author 阶段要求（漏点名的成本由 accept 兜底）；不加 `.hskill/handoff/config.md` 的项目专属段（找 E2E 靠 `ls scripts`、隔离跑法 `sim.js` 已按 `AGENT_CANVAS_HOME` 解析、真人驱动的判断属于 `simulate-user`）。

落点：`skills/coding/handoff/SKILL.md`，需升版本、更新 `skills-index.json` 的 `contentHash` / `contentVersion`、补 CHANGELOG；单独开分支，与 `fix/describe-node-explicit-spec` 互不相关，各自走 `publish-skill`。完成后可删 agent-canvas 记忆 `feedback_handoff_anchors_must_name_regression_e2e`。

---

## mermaid-diagram — 渲染样式增强

### [ ] CSS 注入提升 Mermaid 渲染质量
**背景**：当前 doc-forge 用 Playwright 在浏览器中渲染 Mermaid，但样式控制依赖 `%%{init}%%` themeVariables，能力有限（无法控制节点圆角、阴影、字体等）。

**方向**：在 HTML 页面注入 `<style>` 块直接重写 Mermaid 输出的 SVG 样式，无需自建渲染器。

**可做的事**：
- 节点圆角 `.node rect { border-radius: 4px; }`
- 阴影效果 `filter: drop-shadow(...)`
- 自定义字体 `.label { font-family: 'Gotham', 'PingFang SC'; }`
- 边线粗细 `.edgePath path { stroke-width: 1.5px; }`
- 更精细的 subgraph 样式

**实现位置**：`skills/writing/doc-forge/scripts/md_to_pdf.py`，在渲染前向 HTML 注入品牌 CSS。
**工作量**：2-3 天。

---

## harveyz-skill — 论文分析 Skill

### 设计 Agent 批量筛选论文 skill（screen-papers）
**优先级**: P2 | **日期**: 2026-06-16

设计用于文献综述前期的批量筛选 skill：给定一批论文，快速输出每篇的相关性判断和优先级排序，决定哪些进入精读（read-paper）流程。需考虑 Agent 并行处理能力与筛选标准的可配置性。

---

## harveyz-skill — Syncthing 多设备同步

### 用 sync-agent 将 `~/.hermes` 同步到多设备
**优先级**: P2 | **日期**: 2026-06-18

sync-agent 已完成，现在将 Hermes agent 配置目录 `~/.hermes` 纳入同步范围。在 `~/.hskill/sync-agent/config.json` 的 `folders` 中添加该路径，运行 `hskill sync setup` 应用，并在所有目标设备上完成对端配置。

---

## harveyz-skill — release log 追踪

### 添加 hermes release log 自动抓取与追踪分析
**优先级**: P2 | **日期**: 2026-06-18

针对 openclaw/hermes 仓库，开发自动抓取 release log 并进行追踪分析的能力。目标是定期获取新版本发布记录，提取关键变更、功能新增和 breaking change，形成可供后续查阅的结构化追踪报告。

---

## harveyz-skill — 元框架提取 skill

### 开发从文档提取思维元框架的 skill
**优先级**: P2 | **日期**: 2026-06-18

给定任意输入（文档、Skill、文章、对话等），提取其背后的思维元框架——即决策逻辑、分析结构、推理模式等认知层面的框架，而非内容本身。目标是让用户能复用他人的思维方式，而不只是结论。

---

## extract-url — 词表初始化

### 填入 fixed_tags.txt 初始词条
**优先级**: P2 | **日期**: 2026-07-01

`~/.hskill/url-extract/fixed_tags.txt` 已自动创建模板，但词条全为注释示例，无真实词条。首次实测（alex_prompter 文章）时 `tags` 字段命中率低。需手动填入 topic / technology / source / language / domain 五类初始词条，让后续抓取的 `tags` 产生有意义的命中，并通过 candidate_tags 的 review 来逐步扩充词表。

---

## harveyz-skill — GitHub 相似项目探索 skill

### 探索 GitHub 相似项目借鉴设计的 skill
**优先级**: P2 | **日期**: 2026-06-21

给定一个产品想法或功能方向，在 GitHub 上搜索语义相似的开源项目，分析各项目中可借鉴的模块、特性或设计哲学，而不是整体采用某个项目。目标是帮助用户快速找到参考点，提炼出可引入自己产品的灵感或具体实现思路。

---

## hskill — tool lifecycle

### [x] Tool uninstall mechanism
**背景**：hskill 目前只能安装和更新 tool，没有卸载命令。  
部分 tool（如 p-launch）在安装后会在用户目录写入额外数据：
- `~/.local/bin/p-launch` — 可执行文件
- `~/.local/share/hskill/tools/p-launch.py` — Python 模块
- `~/.local/share/hskill/tools/p-launch.json` — 版本元数据
- `~/.local/share/hskill/p-launch-venv/` — 隔离 venv（pip 依赖）
- `~/.config/p-launch/config.zsh` — 用户配置

**期望行为**：`hskill uninstall p-launch` 清理上述所有文件，并从 `~/.zshrc` 移除 snippet。  
**扩展点**：tool 可在 `tool.json` 里声明 `uninstallPaths[]`，installer 统一处理。

---

## harveyz-skill — pdf-math-translate skill 优化

### 审查优化 pdf-math-translate skill 内容质量
**优先级**: P2 | **日期**: 2026-07-16

刚从外部贡献进 `skills/research/pdf-math-translate/` 的 skill，需要全面内容质量审查：SKILL.md 中所有可执行路径硬编码为另一台机器的用户名（`/Users/harveyopenclaw/...`），在其他机器上无法直接跑通，需改为自适应检测或参数化；同时检查 SKILL.md 结构、触发词（description）、文档完整性是否符合仓库 skill 规范（参考 `docs/reference/skill-spec.md`）。

---
