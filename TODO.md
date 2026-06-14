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
