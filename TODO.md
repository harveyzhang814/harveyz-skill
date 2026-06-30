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

## hub — Phase 3

### [x] 退役 p-launch 和 todo-tool（hub Phase 3）
**优先级**: P3 | **日期**: 2026-06-14

hub Phase 1（core + CLI）和 Phase 2（三栏 TUI）已完成。Phase 3 是最终收尾：
- 在 hskill 中将 p-launch 和 todo-tool 标记为 deprecated，安装时显示退役提示
- `hub` 首次启动的自动迁移已就绪（migrate.py），确认线上验证通过
- 旧命令保持可用直到下一个 major version，不强制删除
- 从 README 和文档中更新入口说明，指向 hub

---

## extract-url — 图片下载修复

### 修复 playwright_xcom.py 图片下载 SSL 验证失败
**优先级**: P2 | **日期**: 2026-06-18

`urllib.request.urlopen` 默认 SSL 验证对 X.com 图片 CDN（`pbs.twimg.com`）失败，图片被静默跳过，仅文字保存成功。常见于 macOS 使用代理/VPN 的环境。

**已验证方案**：在下载前构造 `ssl.create_default_context()`，优先加载 `certifi` 证书包；若 `certifi` 不可用则 fallback 到 `CERT_NONE`。将 `context` 传给 `urlopen`。修复已应用于 `scripts/playwright_xcom.py`，重新抓取验证 6/6 图片下载成功。

---

## harveyz-skill — skill 质量工具

### 开发 Skill 检测并分析各 Skill 间重复内容
**优先级**: P2 | **日期**: 2026-06-15

开发一个专用 Skill，扫描 `skills/` 目录下所有 Skill 的内容，检测不同 Skill 之间的语义重复部分。发现重复后，对比分析各自的上下文、触发场景和职责边界，给出哪个 Skill 更适合承载该内容的建议，最终由用户决策如何处置（保留、迁移或删除）。

---

## harveyz-skill — 论文分析 Skill

### 设计 Agent 单篇精读论文 skill（read-paper）
**优先级**: P2 | **日期**: 2026-06-16

基于 Keshav 三遍阅读法，针对 Agent 与人类认知差异重新设计阅读方法论，实现为单篇精读 skill。核心设计问题：Agent 无认知负荷限制但有 context 限制，"在脑海中重现论文"如何转化为 Agent 可执行步骤，以及结构化输出如何便于后续引用。

---

### 设计 Agent 批量筛选论文 skill（screen-papers）
**优先级**: P2 | **日期**: 2026-06-16

设计用于文献综述前期的批量筛选 skill：给定一批论文，快速输出每篇的相关性判断和优先级排序，决定哪些进入精读（read-paper）流程。需考虑 Agent 并行处理能力与筛选标准的可配置性。

---

## harveyz-skill — Syncthing 多设备同步

### 实现 Agent-Syncthing 多设备文档同步工具
**优先级**: P2 | **日期**: 2026-06-16

开发一个小工具，让 Agent 通过 Syncthing 项目在设备间同步文档。初期目标是同步根目录下的 `.hskill` 文件（skill 运行时数据），后续扩展到 Hermes 性格文件等其他 Agent 配置。

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

## harveyz-skill — question-me skill

### 开发参考 grill-me 风格的 question-me skill
**优先级**: P2 | **日期**: 2026-06-30

参考 grill-me/grilling 的「一次一问 + 给推荐答案 + 决策树依赖顺序」风格，创建一个 skill，在执行任务前帮用户明确更好的指令、查明隐含假设、理清决策因素。核心约束：一次只问一个问题，每问必附推荐答案，能自查的问题先自查再问用户，按决策依赖顺序逐一推进，直到达成 shared understanding 再开始实现。

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
