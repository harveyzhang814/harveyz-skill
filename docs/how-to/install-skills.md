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

| Scope | Claude Code | Cursor | Codex | OpenClaw | Hermes |
|-------|------------|--------|-------|----------|--------|
| user | `~/.claude/skills/` | `~/.cursor/skills/` | `~/.codex/skills/` | `~/.openclaw/skills/` | `~/.hermes/skills/` |
| project | `.claude/skills/` | `.cursor/skills/` | `.codex/skills/` | — (user only) | — (user only) |

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

`update` 更新的是 **hskill 自身**（不是已安装的 skill，那是 `hskill upgrade`）。它有两种来源，且是**粘性**的——沿用当前安装的来源，裸跑永远不跨来源：

| 当前来源 | `hskill update` 的行为 |
|---|---|
| npm（默认） | `npm install -g harveyz-skill@latest` |
| 本地仓库 | 回到记录的仓库路径重新 `npm pack` + 安装 |

切换来源只能显式触发：

```bash
hskill update --local ~/Projects/harveyz-skill   # 切到本地仓库
hskill update --npm                              # 切回 npm registry
```

`--local` 的路径**必须写出来**，没有默认值，也不会回退到当前目录——否则在别的仓库里手滑跑一次就会试图安装别的包。第一次切要打一次全路径，之后粘性接管。

### 当前装的是哪一份

```console
$ hskill version
0.34.0+local

source: local  /Users/you/Projects/harveyz-skill
branch: staging  commit: 3d4192a
```

npm 来源时只有裸版本号一行，没有 `+local` 后缀和后面两行。

来源信息记在全局安装目录里（`$(npm root -g)/harveyz-skill/.hskill-source.json`）。任何一次 `npm install -g` 都会清空重建这个目录，所以即使你绕过 hskill 手工跑 `npm i -g harveyz-skill@latest`，痕迹也会跟着消失、hskill 下次正确报告已回到 npm 来源——记录的来源不可能与实际情况脱节。

### 检查有没有更新

```bash
hskill version --check
```

npm 来源下比对本地版本与 registry 上的 `latest`；本地来源下比对的是**记录的 commit 与仓库当前 HEAD**，而不是版本号——开发分支上版本号常常几十个提交不动，能动的只有 commit。仓库有未提交改动时一律报告"有未打包的改动"，即使 commit 相同。

### 本地来源的仓库被移走或删掉了

`update` 会直接失败并给出两条出路，**不会静默回退到 npm**：

```console
✗ 本地来源仓库不存在：/path/that/is/gone
  改用 npm：   hskill update --npm
  指向新路径： hskill update --local <新路径>
```
