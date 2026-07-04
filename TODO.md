# TODO

## 🚧 待开发

### 按 description-trigger-role 研究优化所有 skill 的 description
**优先级**: P3 | **日期**: 2026-07-04

根据 `knowledge/skill-philosophy/07-description-trigger-role` 的研究结论，审视并优化 `skills/` 下所有 Skill 的 description 字段：移除操作内容与工作流摘要，改写为纯触发条件语言，补充合法额外信息（症状/情境/可达性声明）。

---

## ✅ 已完成

### 约定 skill 任务在 session 中的回报信息格式
**完成日期**: 2026-07-02

以 extract-url 为例落地：新增 `count_article_stats.py` 统计字符/代码块/图片；SKILL.md 步骤 4 定义四种状态卡片（完成/失败/部分完成/已跳过）；批量流程每篇即时输出 + 汇总行；通用卡片壳规范写入 `knowledge/skill-philosophy/04-completion-report/standard.md`。

---

### 重构 extract-url tag 为固定集与候选集分离
**完成日期**: 2026-07-02

`article_utils.py` 实现 `load_fixed_tags` / `move_fixed_from_candidate` / `enforce_tag_separation`；`validate_article.py` 调用兜底移位；`file-format.md` 更新 `tags` / `candidate_tags` 字段说明及 `fixed_tags.txt` 格式规范。词表路径：`~/.hskill/url-extract/fixed_tags.txt`（需手动填入初始词条）。

---

### 开发参考 grill-me 风格的 question-me skill
**完成日期**: 2026-07-01

实现了 question-me skill（`skills/coding/question-me/`）：Phase 0-4 流程（自查 → 意图校准 3 问 → 动态深挖 → 摘要确认），内部决策树格式（`[status] id=XX [dep=YY] 文本`），render_tree.py 生成可视化 HTML（card 树 + 自动刷新），9 项单元测试覆盖解析/树构建/环检测。

---

### 设计多平台 Skill 补丁的同步与生命周期管理机制
**完成日期**: 2026-07-01

实现了完整的热修生命周期管理方案：fix-skill v2.1.0 自动写入 HOTFIXES.md，新增 sync-hotfix v1.1.1 处理合并回源（HOTFIXES.md 扫描 + Step 5 全文件 diff 安全网）。方法论文档见 `docs/explanation/skill-hotfix-lifecycle.md`，格式规范见 `docs/reference/hotfix-lifecycle.md`。

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
