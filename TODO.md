# TODO

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

### 开发两阶段引导式推理模式提取 skill（元框架前置层）
**优先级**: P2 | **日期**: 2026-06-21

元框架提取的前置步骤，分两阶段执行：

**第一阶段**：独立于用户偏好，综合提取文章的数据方式、分析方式与推理方式，识别文中所有推理链和模式，形成完整的认知方法清单。

**第二阶段**：以用户指出的吸引点为锚点，对该模式作重点阐述或以此为切入口深入分析，但分析对象仍是文章整体——用户输入是导航锚，不是筛选器。文章中若存在多条推理链，锚点模式优先阐述，其余仍保留在输出中。

第一轮抽象的产出（推理 + 分析 + 数据方法全集）作为后续语言框架提取（元框架 skill）的输入基础，融合"从范式提取设计哲学"方法论。

---

## harveyz-skill — GitHub 相似项目探索 skill

### 探索 GitHub 相似项目借鉴设计的 skill
**优先级**: P2 | **日期**: 2026-06-21

给定一个产品想法或功能方向，在 GitHub 上搜索语义相似的开源项目，分析各项目中可借鉴的模块、特性或设计哲学，而不是整体采用某个项目。目标是帮助用户快速找到参考点，提炼出可引入自己产品的灵感或具体实现思路。

---

## capture-todo — 合并步骤双校验兼容

### 修复 capture-todo 合并步骤同时通过分支来源与提交格式检查
**优先级**: P2 | **日期**: 2026-06-21

当目标项目同时启用分支来源校验（pre-commit 读取 MERGE_MSG，要求 `Merge branch 'xxx'` 格式）和提交格式校验（commit-msg 要求 Conventional Commits 格式）时，`git merge --no-ff -m "..."` 的 `-m` 参数会同时写入 MERGE_MSG，导致两个 hook 的格式要求冲突。修复方向：合并前先手动将 MERGE_MSG 写成标准 git 格式，再用 `-m "chore(...): ..."` 满足 Conventional Commits，两路分开处理。

---

