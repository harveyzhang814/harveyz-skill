# Shared Project Index Design

## 概述

将 todo-tool 的项目索引迁移到共享位置，同时让 p-launch 自动同步索引并支持 CLI 按 GitHub repo 名打开项目。

## 背景

todo-tool 维护 `~/.hskill/todo-tool/PROJECTS.md` 作为项目注册表，name 字段已使用 GitHub repo 名。p-launch 独立扫描本地目录，使用本地目录名，两者数据孤立。

## 用户故事

- 用户运行 `p-launch open cocoScribe` 直接打开项目的 Cursor + Ghostty
- todo-tool 创建任务时，项目列表来自共享索引，name 与 GitHub repo 名一致
- p-launch 启动 TUI 时，自动将扫描到的 repo 同步到共享索引，无需手动注册

## 架构设计

### 共享索引位置

```
~/.hskill/public/PROJECTS.md
```

格式与现有 todo-tool 索引完全一致：

```markdown
# Project Index

- **repo-name** `/local/path`
  optional description
```

`name` = GitHub repo 名，提取规则：`git remote get-url origin` 末段，去掉 `.git` 后缀、去掉用户名前缀。

### todo-tool 变更

**`projects_index.py`**：

- `get_index_path()` 返回 `~/.hskill/public/PROJECTS.md`
- 一次性 merge 迁移（仅运行一次）：
  1. 检查 `~/.hskill/public/.migrated` flag 文件是否存在
  2. 不存在则执行迁移：读取旧文件 `~/.hskill/todo-tool/PROJECTS.md`，与新文件（可能已由 p-launch 创建）merge——对新文件中缺少 description 的条目从旧文件补填
  3. 迁移完成后写入 `~/.hskill/public/.migrated`
  4. flag 文件权限不足时 stderr 输出 warning，继续运行（不中断）
- 旧文件 `~/.hskill/todo-tool/PROJECTS.md` 保留不删除

### p-launch 变更

**`p_launch.py`**：

解析器复制自 todo-tool（两工具独立，不共享模块）：在 `p_launch.py` 内实现 `_load_index(path)` 和 `_write_index(projects, path)`，约 30 行。

新增函数 `extract_github_name(path: Path) -> str | None`：
- 运行 `git remote get-url origin`
- 解析 HTTPS（`https://github.com/user/repo.git`）或 SSH（`git@github.com:user/repo.git`）格式
- 返回末段去 `.git`，失败返回 `None`

新增函数 `sync_to_index(repos: list[Path]) -> None`：
- 读共享索引**一次**
- 对每个 repo 调用 `extract_github_name()`，无 remote 则跳过
- upsert：已存在则更新 path，保留 description；不存在则追加
- **清理**：移除本地 path 不再存在于任何 repo 扫描结果中的条目（同名冲突时后扫描覆盖，stderr warning）
- 写入**一次**，使用 `fcntl.flock()` 独占锁防止并发损坏
- 任何异常 → stderr 输出一行 warning，不抛出（后台静默失败是比崩溃更坏的）
- 写入前 `~/.hskill/public/` 目录不存在则自动创建

在 `load_repos()` 扫描完成后，后台线程调用 `sync_to_index()`（不阻塞 TUI）。

新增 CLI 入口 `open_project(name: str)`：
- 读取共享索引，按 name 查找 path
- 调用现有 `launch_project(path)`
- 未找到时打印可用项目名列表
- 索引不存在时优雅报错（提示先启动 TUI 以初始化索引）

`__main__` 入口：
```bash
p-launch open <repo-name>   # CLI 模式（p-launch.sh 已透传 $@）
p-launch                    # TUI 模式（现有行为）
```

## 数据流

```
p-launch 启动
  → collect_repos() 扫描本地目录
  → TUI 渲染（不等待 sync）
  → [后台] sync_to_index():
      fcntl.flock(LOCK_EX)
      读 ~/.hskill/public/PROJECTS.md
      upsert + 清理本地不存在的条目
      写回
      fcntl.flock(LOCK_UN)
      失败 → stderr warning

p-launch open <name>
  → 读 ~/.hskill/public/PROJECTS.md
  → 找到 path → launch_project(path)
  → 未找到 → 打印可用列表

todo-tool 读项目列表
  → get_index_path() → ~/.hskill/public/PROJECTS.md
  → 检查 ~/.hskill/public/.migrated
  → 未标记则执行 merge 迁移（fcntl.flock 保护写入）
  → 标记完成后正常读取
```

## 边界情况

- **无 remote 的 repo**：跳过，不写入索引，TUI 正常显示
- **同名冲突**（两个本地目录对应同一 GitHub 名）：后扫描到的 path 覆盖前一个，stderr 输出 warning
- **旧索引保留**：`~/.hskill/todo-tool/PROJECTS.md` 迁移后不删除
- **`~/.hskill/public/` 目录**：写入前自动创建
- **`.migrated` flag 权限不足**：stderr warning，不中断，下次启动重试 merge（幂等）

## NOT in scope

- 非 GitHub remote（GitLab、自建）的 name 解析 — 当前全部项目在 GitHub
- 索引 UI（在工具内编辑 description）— 手动编辑 PROJECTS.md 即可
- 跨机器同步 PROJECTS.md — 独立问题
- description 自动生成 — 超出范围

## 测试策略

### todo-tool (`tests/test_projects_index.py` 扩展)

**路径变更**：
- `get_index_path()` 返回新路径

**Migration merge**：
- 旧文件存在，新文件不存在 → copy
- 旧文件存在，新文件已存在（p-launch 先创建，无 description）→ 从旧文件补填 description
- 两者都不存在 → 返回 []
- `.migrated` 存在 → 跳过 merge（不重复运行）
- `.migrated` 写入失败 → stderr warning，继续

### p-launch (`tests/test_p_launch.py` 扩展)

**`extract_github_name()`**：
- HTTPS URL（`https://github.com/user/repo.git`）→ `"repo"`
- SSH URL（`git@github.com:user/repo.git`）→ `"repo"`
- 无 remote → `None`
- 非 GitHub remote（自建域名）→ `None`（拒绝非 github.com）

**`sync_to_index()`**：
- 新 repo → 追加到索引
- 已有 repo，path 变化 → 更新 path，保留 description
- 无 remote 的 repo → 跳过
- 本地 path 不存在的旧条目 → 从索引移除（清理）
- 同名冲突 → 后者覆盖 + stderr warning
- 读一次写一次（验证文件 IO 次数）

**CLI `open`**：
- name 在索引中存在 → `launch_project()` 被调用
- name 不存在 → 打印可用列表
- 索引文件不存在 → 优雅报错

## 实施任务

```
Lane A (todo-tool) ─────────────────────────────────────
  T1 (P1): projects_index.py — 更新 get_index_path() + merge 迁移 + flag
  T2 (P2): test_projects_index.py — 迁移 merge 测试（5 cases）

Lane B (p-launch) — 并行 ────────────────────────────────
  T3 (P1): p_launch.py — 解析器复制 + extract_github_name + sync_to_index
            （读一次写一次，fcntl.flock，清理，stderr）
  T4 (P1): p_launch.py — CLI open + __main__ 入口
  T5 (P2): test_p_launch.py — extract/sync/open 测试（12 cases）

合并后:
  T6 (P1): 集成验证 — 运行 p-launch open <name>，确认 todo-tool 项目列表一致
```

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 4 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

OUTSIDE VOICE (Claude subagent): migration ordering, advisory lock, silent failures, migration re-runs — all addressed in decisions.

VERDICT: ENG CLEARED — ready to implement.

NO UNRESOLVED DECISIONS
