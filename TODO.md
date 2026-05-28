# TODO

## hskill — tool lifecycle

### [ ] Tool uninstall mechanism
**背景**：hskill 目前只能安装和更新 tool，没有卸载命令。  
部分 tool（如 p-launch）在安装后会在用户目录写入额外数据：
- `~/.local/bin/p-launch` — 可执行文件
- `~/.local/share/hskill/tools/p-launch.py` — Python 模块
- `~/.local/share/hskill/tools/p-launch.json` — 版本元数据
- `~/.local/share/hskill/p-launch-venv/` — 隔离 venv（pip 依赖）
- `~/.config/p-launch/config.zsh` — 用户配置

**期望行为**：`hskill uninstall p-launch` 清理上述所有文件，并从 `~/.zshrc` 移除 snippet。  
**扩展点**：tool 可在 `tool.json` 里声明 `uninstallPaths[]`，installer 统一处理。
