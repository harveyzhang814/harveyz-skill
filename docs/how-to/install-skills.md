# 如何安装 Skills

## 前提条件

- Node.js >= 18
- npm

---

## 1. 全局安装 hskill

```bash
npm install -g harveyz-skill
```

安装后 `hskill` 命令即可使用。

---

## 2. 安装 Skills

### 交互式安装（推荐）

```bash
hskill
```

按提示依次选择：
1. **Skills / bundle** — 勾选要安装的内容
2. **Scope** — `user`（所有项目共享）或 `project`（仅当前项目）
3. **工具** — Claude Code / Cursor / Codex

### 非交互安装

```bash
# 安装指定 skill
hskill install --skill git-workflow-init --target claude

# 安装整个 bundle
hskill install --bundle dev --target claude

# 安装到项目级别
hskill install --skill mermaid-diagram --target claude --scope project

# 安装多个 skill
hskill install --skill git-workflow-init,mermaid-diagram --target claude

# 覆盖已有安装
hskill install --skill mermaid-diagram --target claude --force
```

---

## 3. 安装路径

| Scope | Claude Code | Cursor | Codex |
|-------|------------|--------|-------|
| user | `~/.claude/skills/` | `~/.cursor/skills/` | `~/.codex/skills/` |
| project | `.claude/skills/` | `.cursor/skills/` | `.codex/skills/` |

**user**：全局共享，一次安装所有项目生效。  
**project**：仅当前目录项目可用，适合团队统一管理（可提交到 git）。

---

## 4. 查看可用 Skills

```bash
hskill list
```

---

## 5. 更新

```bash
hskill update
```
