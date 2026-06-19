# CHANGELOG — skill-analyzer

## v2.0.0 — 2026-06-19

### Breaking Changes
- 去掉全部 gstack 专用硬编码（文件数量、路径、skill 列表），不再向后兼容 v1.0.0 的分析结果
- 输出路径从 `{项目根}/skill-analysis/analysis/` 变更为 `{skillDir}/{repo-name}/analysis-{date}.md`

### New Features
- 支持任意遵循 harveyz-skill 格式的 skill 仓库
- 新增 Step 0：读取/初始化 `$HOME/.hskill/config.json`，与 learn-skill 共享配置
- 新增 Step 1：三级路径解析（带参 → 检测当前目录 → 询问用户）
- Layer 1 搜索策略升级为四优先级顺序，覆盖根目录全局扫描
- Layer 3 通过调用 `learn-skill` 读取每个 skill，确保读取标准一致

### Removed
- 必检清单中的 gstack 专用文件数量（bin/ = 17 等）
- prohibitions.md 中的 15 条 gstack 专用规则
- 含 WebSearch 的 skill 硬编码列表
- v0.1.0 skill 硬编码列表
- 工具数参考表（各 skill 正确工具数）

---

## v1.0.0 (2026-05-12)

**基于：** v0.9 + 结构性重构

### 主要变更

- 补全 YAML frontmatter（新增 `name`、`description`、`user_invocable`、`version` 字段）
- 新增 `references/` 目录，抽象三份模版：
  - `prohibitions.md` — 完整 23 条禁忌（原 SKILL.md 仅保留第 23 条）
  - `output-template.md` — 分析报告骨架模版
  - `evaluation-template.md` — 评估报告骨架模版
- SKILL.md 中 `禁忌` / `输出格式` / `Layer 1-4` 三个 section 改为引用 references
- 新增 `输出路径` 规范：输出文件保存在被分析项目根目录 `skill-analysis/` 下
- 删除 `research/` 目录（历史实验产物，路径不符合输出规范）

---

## v0.7 (2026-03-28)

**基于：** v0.6 + 第5轮评估反馈

### 核心修复：删除所有"双 allowed-tools 块"相关内容（禁忌 21）

**问题：** 第4轮和第5轮分析报告仍然描述"双 allowed-tools 块"，但经人工源码核查验证：
- **每个 skill 只有 1 个 `allowed-tools` YAML 块**
- `---` 是 frontmatter 分隔符，不是"第二个块"
- `<!-- AUTO-GENERATED -->` 是 HTML 注释，与 allowed-tools 无关
- `# zsh-compatible` 是 bash 脚本注释，与 allowed-tools 无关
- 所有 skill 的 `grep "allowed-tools"` 返回值均为 **1**

"双块一致性验证"是两个错误数据互验的伪命题。

**修复：**
- 禁忌 21：明确不存在"双块"，删除所有相关描述
- 新增概念澄清：YAML frontmatter 结构说明
- 提供正确读取命令：`grep "allowed-tools"` 返回值应为 1

---

## v0.6 (2026-03-27)

**基于：** v0.5 + 第4轮评估反馈

### 禁止伪造 allowed-tools 数据（禁忌 20）

**问题：** v0.5 分析报告大量伪造数据（browse 报8个，实际3个；捏造10个双块等）

**修复：**
- 必须从实际文件读取 allowed-tools
- 提供已知基准数据交叉验证
- 禁忌 20

---

## v0.5 (2026-03-27)

**基于：** v0.4 + 第3轮评估反馈

### 文件清单必须逐项列出（禁忌 17-19）

- lib/ 实际只有 worktree.ts
- 独立 .tmpl 实际有 29 个
- 版本根因必须探讨

---

## v0.4 (2026-03-27)

**基于：** v0.3 + 第2轮评估反馈

### 项目类型检测机制（禁忌 14-15）

---

## v0.3 (2026-03-27)

**基于：** v0.2 + 第1轮评估反馈

### allowed-tools 验证机制（禁忌 11-13）

---

## v0.2 (2026-03-27)

**基于：** v0.1-baseline

### 必检清单（VERSION、数量、Ghost、CI）

---

## v0.1-baseline (2026-03-27)

初始版本：洋葱模型四层框架
