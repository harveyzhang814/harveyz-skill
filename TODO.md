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

### 退役 p-launch 和 todo-tool（hub Phase 3）
**优先级**: P3 | **日期**: 2026-06-14

hub Phase 1（core + CLI）和 Phase 2（三栏 TUI）已完成。Phase 3 是最终收尾：
- 在 hskill 中将 p-launch 和 todo-tool 标记为 deprecated，安装时显示退役提示
- `hub` 首次启动的自动迁移已就绪（migrate.py），确认线上验证通过
- 旧命令保持可用直到下一个 major version，不强制删除
- 从 README 和文档中更新入口说明，指向 hub

---

## harveyz-skill — skill 质量工具

### 开发 Skill 检测并分析各 Skill 间重复内容
**优先级**: P2 | **日期**: 2026-06-15

开发一个专用 Skill，扫描 `skills/` 目录下所有 Skill 的内容，检测不同 Skill 之间的语义重复部分。发现重复后，对比分析各自的上下文、触发场景和职责边界，给出哪个 Skill 更适合承载该内容的建议，最终由用户决策如何处置（保留、迁移或删除）。

---

## harveyz-skill — Syncthing 多设备同步

### 实现 Agent-Syncthing 多设备文档同步工具
**优先级**: P2 | **日期**: 2026-06-16

开发一个小工具，让 Agent 通过 Syncthing 项目在设备间同步文档。初期目标是同步根目录下的 `.hskill` 文件（skill 运行时数据），后续扩展到 Hermes 性格文件等其他 Agent 配置。

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
