# TODO

## 🚧 待开发

### 重构 extract-url tag 为固定集与候选集分离
**优先级**: P2 | **日期**: 2026-06-14

extract-url skill 抓取文章时生成的 tags 目前全由 LLM 从内容推断，无固定词表，导致：① 每次抓取标签不稳定（同一主题表述不一致）；② 无法保证核心关键词（如 loop engineering）必现；③ 候选标签与确定标签混在一起，难以管理。

**目标**：将 tag 拆分为两类：
- **固定 Tag**（`fixed_tags`）：维护在 skill 目录词表中，每次抓取必定注入，与文章内容无关（如来源站点分类、技术栈、语言等跨文章共性标签）
- **候选 Tag**（`candidate_tags`）：从文章内容提取，模糊/候选性质，定期 review 决定是否升入固定集

**需修改的文件**：
1. `skills/extract-url/` 下新建 `fixed_tags.txt`（初始词表）
2. 修改 `validate_article.py` / `article_utils.py` 的 frontmatter 构建逻辑，将 tag 拆为 `fixed_tags` 和 `candidate_tags` 两个 YAML 列表字段
3. 更新 `references/file-format.md` 文档说明新字段

---

## ✅ 已完成

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

## extract-url — 图片下载修复

### 修复 playwright_xcom.py 图片下载 SSL 验证失败
**优先级**: P2 | **日期**: 2026-06-18

`urllib.request.urlopen` 默认 SSL 验证对 X.com 图片 CDN（`pbs.twimg.com`）失败，图片被静默跳过，仅文字保存成功。常见于 macOS 使用代理/VPN 的环境。

**已验证方案**：在下载前构造 `ssl.create_default_context()`，优先加载 `certifi` 证书包；若 `certifi` 不可用则 fallback 到 `CERT_NONE`。将 `context` 传给 `urlopen`。修复已应用于 `scripts/playwright_xcom.py`，重新抓取验证 6/6 图片下载成功。

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

## harveyz-skill — 推理模式提取前置 skill

### [x] 开发两阶段引导式推理模式提取 skill（元框架前置层）
**已落地为** `skills/experiment/extract-cognition`（认知签名抽取方法论，取代原两阶段锚点设计）。设计见 docs/superpowers/specs/2026-06-22-extract-cognition-design.md。

---

## harveyz-skill — GitHub 相似项目探索 skill

### 探索 GitHub 相似项目借鉴设计的 skill
**优先级**: P2 | **日期**: 2026-06-21

给定一个产品想法或功能方向，在 GitHub 上搜索语义相似的开源项目，分析各项目中可借鉴的模块、特性或设计哲学，而不是整体采用某个项目。目标是帮助用户快速找到参考点，提炼出可引入自己产品的灵感或具体实现思路。

---

## harveyz-skill — sync-design-html 输出路径迁移

### 将 sync-design-html 的 HTML 输出与 manifest 迁移至项目 `.hskill/` 文件夹
**优先级**: P2 | **日期**: 2026-06-22

当前 `sync-design-html` skill 将 HTML 设计备份写入 `docs/superpowers/`，manifest 存放在 `docs/reference/design-html-manifest.json`。按 skill 设计哲学，skill 产出物应归属 `.hskill/` 目录，与项目文档目录解耦。

需完成：将输出路径（HTML 文件 + manifest）统一迁移到项目的 `.hskill/design-html/`，并更新 skill 中的路径引用。

---

## capture-todo — 合并步骤双校验兼容

### 修复 capture-todo 合并步骤同时通过分支来源与提交格式检查
**优先级**: P2 | **日期**: 2026-06-21

当目标项目同时启用分支来源校验（pre-commit 读取 MERGE_MSG，要求 `Merge branch 'xxx'` 格式）和提交格式校验（commit-msg 要求 Conventional Commits 格式）时，`git merge --no-ff -m "..."` 的 `-m` 参数会同时写入 MERGE_MSG，导致两个 hook 的格式要求冲突。修复方向：合并前先手动将 MERGE_MSG 写成标准 git 格式，再用 `-m "chore(...): ..."` 满足 Conventional Commits，两路分开处理。

---


### 设计多平台 Skill 补丁的同步与生命周期管理机制
**优先级**: P2 | **日期**: 2026-06-30

harveyz-skill 项目维护多个跨平台 Skill（如 extract-url），每个平台（Claude Code / Codex / Hermes）有独立的补丁文件（`SKILL.<platform>.md`），采用「主流程 + 各平台差异覆盖」模式。

**问题**：
- 主流程变更时，无法自动知道哪些平台补丁需要同步更新
- 各平台补丁边界不清晰，生命周期状态（active / deprecated / pending-update）无追踪
- 缺乏版本绑定机制

**目标**：设计并实现一套机制，包括：
1. **补丁声明式元数据**：每个补丁文件头部声明覆盖的主流程章节、依赖主流程版本、平台、状态
2. **变更检测脚本**：主流程发布时，自动比对输出哪些补丁需要检查/更新
3. **生命周期状态管理**：active / deprecated / pending-update 三态及其转换规则

---
