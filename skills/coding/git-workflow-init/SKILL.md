---
name: git-workflow-init
description: "Initialize or update git branch management standards: reads workflow-config.yml, audits config, incrementally generates and deploys git hooks (pre-commit, commit-msg, pre-push, post-checkout), and generates workflow docs. Triggers: initializing a new git repo, first-time git setup, user asks to set/update branch protection or naming rules, reinstalling git hooks, or syncing after skill/template updates."
user_invocable: true
version: "4.1.0"
---

# Git 工作流初始化

读取 `workflow-config.yml`，审核配置，差量部署 git hooks。
重新运行时自动检测配置变更、用户手改冲突、用户代码与新规则的交叉冲突，一次性汇总让用户决策后再写入。

---

## 执行步骤

### Step 1 — 确认 git 仓库

```bash
git rev-parse --show-toplevel
```

若不在 git 仓库中，询问用户是否先执行 `git init`，用户拒绝则优雅停止。

---

### Step 2 — 读取配置

按以下顺序查找 `workflow-config.yml`：

1. 项目根目录 `workflow-config.yml`
2. 项目根目录 `.claude/workflow-config.yml`

若两处均不存在，询问用户：
- 使用默认配置（从此 skill 的 `references/workflow-config.yml` 复制到项目根目录）
- 还是中止并自行创建后重新运行

找到后读取并解析 YAML。

---

### Step 3 — 审核配置

对配置内容逐项检查，**发现所有问题后一次性报告，不逐条中止**。

**结构校验：**
- `meta.preset` 若存在，必须是 `gitflow`、`github-flow`、`trunk-based`、`custom` 之一
- `commit_message.format` 必须是 `conventional`、`regex`、`none` 之一
- 若 `format: regex`，必须同时存在 `pattern` 字段

**逻辑校验：**
- `branches.protected` 中任何分支的 `merge_from` 不得包含自身（循环依赖）
- `push_rules.block_force_push` 中的分支建议与 `branches.protected` 保持一致，不一致则警告
- `branch_naming.exempt` 中的分支不应同时被 `allowed_patterns` 覆盖（冗余）

**正则校验：**（对每个 pattern 执行，返回 2 = 非法）
```bash
echo "" | grep -E "<pattern>" > /dev/null 2>&1; echo $?
```

审核通过打印 `✅ 配置审核通过`，审核失败列出所有问题并停止。

---

### Step 4 — 分析当前状态（仅当 `.githooks/` 已存在时）

**首次安装时跳过此步骤，直接进入 Step 5。**

目标：写入任何文件之前，全面收集需要用户决策的冲突，在 Step 5 一次性呈现。实现细节见 `references/conflict-analysis.md`。

#### 4a. Lock 文件 diff
读取 `.githooks/.workflow-config.lock.yml`（不存在则视为全量新增，跳过）。对比上次配置与当前配置，生成 +/~/- 变更摘要。**提取 YAML 分支名时必须用 python3 精确解析，不得用 `grep "name:"`**（见 reference 中的脚本）。

#### 4b. MANAGED 块 hash 校验
读取每个 hook 的 `BEGIN MANAGED`/`END MANAGED` 块，重新计算 hash，与块头标记对比。不一致 → 用户手改，记录为类型 C 冲突（附 diff）。

#### 4c. 外部代码扫描
提取每个 hook 中 MANAGED 块外的用户手写代码，识别其中引用的分支名、提交类型、pattern、外部脚本调用。

#### 4d. 冲突检测
综合 4a/4b/4c，识别四种冲突类型（A 条件重叠、B 引用断裂、C 手改冲突、D 新增重叠）。类型定义与选项见 `references/conflict-analysis.md`。

---

### Step 5 — 冲突解决（一次性汇总，用户逐条决策）

将 Step 4 发现的所有冲突**一次性呈现**，每条附带类型标签和选项，用户逐条决策后进入 Step 6。无冲突则直接进入 Step 6。

呈现格式（以类型 C 手改冲突为例）：

```
发现 N 处需要决策的冲突，请逐条确认：

─────────────────────────────────────────────────────────
[1/N] 手改冲突（类型 C）
文件: .githooks/pre-commit，块: branches.protected/main
用户对生成代码做了如下修改：
  - echo "❌ 禁止直接在 main 上提交。"
  + echo "❌ [POLICY] 禁止直接在 main 上提交，违规请联系 @team-lead。"
选项：
  A) 保留用户修改（此块不重新生成）
  B) 用新配置覆盖（丢弃用户修改）
─────────────────────────────────────────────────────────
```

各冲突类型的完整选项定义见 `references/conflict-analysis.md`。

---

### Step 6 — 差量生成并部署 hooks

```bash
mkdir -p .githooks
```

#### 生成原则

根据 Step 5 的决策结果，对每个 hook 文件按以下规则处理：

1. **MANAGED 块**：根据当前配置重新生成内容，更新块内容及 hash
   - 若 Step 5 中用户选择"保留用户修改"→ 跳过此块，保持现有内容和 hash 不变
   - 若配置中某节 `enforce: false` 且对应 MANAGED 块存在 → 删除该块（保留块外用户代码）

2. **用户代码区（MANAGED 块外）**：永远不覆盖，原样保留

3. **差量写入**：生成全文后与磁盘文件对比——内容相同标记 `UNCHANGED`，不同标记 `UPDATED`，新建标记 `NEW`

各 hook 的触发条件、固定头部代码、MANAGED 块结构、块 ID 规范、hash 计算方式及多行内容写入技巧，见 `references/hook-templates.md`。

#### 设置权限和 hooksPath

```bash
chmod +x .githooks/*
git config core.hooksPath .githooks
git config merge.ff false
```

`merge.ff false` 禁止 fast-forward 合并，确保每次合并都产生 merge commit，pre-commit 钩子才能检查合并来源分支。

---

### Step 6.5 — 验收测试（可选）

完成 hooks 部署后，询问用户：

```
✅ Hooks 已部署完毕。是否运行验收测试？（在当前 repo 中验证 hooks 实际拦截行为）[y/N]
```

- 用户选 **N** → 直接进入 Step 7。
- 用户选 **Y** → 读取 `references/acceptance-test.md`，按其中说明逐 hook 执行验收场景，展示结果表格。全通过则继续 Step 7；有失败则展示详情并询问用户是否仍继续。

---

### Step 7 — 从配置渲染并写入工作流文档（差量）

每次运行都根据当前 `workflow-config.yml` 的最终状态重新渲染文档，确保文档与配置始终一致。

#### 7a. 渲染文档

```bash
python3 <skill-path>/references/render_docs.py \
  workflow-config.yml \
  <skill-path>/references/git-workflow-template.md \
  docs/reference/git-workflow.md
# 输出 NEW / UPDATED / UNCHANGED
```

脚本自动处理所有占位符（`{{BRANCH_TOPOLOGY_ASCII}}`、`{{BRANCH_TABLE}}`、`{{PROTECTION_RULES}}`、`{{NAMING_TABLE}}`、`{{COMMIT_FORMAT_SECTION}}`、`{{NAMING_EXEMPT}}`、`{{FAQ_SECTION}}` 等）——无需逐一处理，渲染逻辑详见 `references/render_docs.py`。

#### 7b. 差量写入

1. 若 `docs/reference/` 不存在则创建
2. 将渲染后的内容与现有 `docs/reference/git-workflow.md` 对比
   - 内容相同 → 跳过，标记 `UNCHANGED`
   - 内容不同或文件不存在 → 写入，标记 `UPDATED` 或 `NEW`
3. 若 `docs/INDEX.md` 存在，追加索引行（已存在则跳过）

---

### Step 8 — 更新 AI 配置文件（可选）

若文件中已包含 `docs/reference/git-workflow.md` 链接，跳过。

否则询问用户是否在已存在的 `CLAUDE.md`、`AGENTS.md`、`GEMINI.md` 中追加：

```markdown
## Git 工作流

分支命名规范、保护规则与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。
```

---

### Step 9 — 更新 lock 文件并汇报

#### 更新 lock 文件

将本次生效配置的关键字段写入 `.githooks/.workflow-config.lock.yml`，格式见 `references/lock-file-format.md`。

#### 汇报结果

用表格展示每个操作的状态：

```
文件                                状态
─────────────────────────────────────────────────────
workflow-config.yml                已读取
.githooks/.workflow-config.lock    UPDATED（记录新配置快照）
.githooks/pre-commit               UPDATED（main 块 hash 更新；develop 块新增）
.githooks/commit-msg               UNCHANGED
.githooks/pre-push                 UNCHANGED
.githooks/post-checkout            NEW
core.hooksPath                     = .githooks
docs/reference/git-workflow.md     UPDATED
CLAUDE.md                          已有引用，跳过
─────────────────────────────────────────────────────
冲突决策摘要：
  [1/3] branches.protected/main 手改块 → 用户选择保留修改
  [2/3] develop 分支条件重叠 → 用户选择使用新配置
  [3/3] wip 类型引用断裂 → 用户选择保留用户代码
```

若有保留的无法映射规则，附注提示。

---

## 参考文件

| 文件 | 说明 | 读取时机 |
|------|------|---------|
| `references/workflow-config.yml` | 配置文件模板 | Step 2：用户无配置时复制 |
| `references/conflict-analysis.md` | 4a–4d 实现脚本、冲突类型 A/B/C/D 完整定义与选项、Step 5 呈现格式 | Step 4/5：执行分析前读取 |
| `references/hook-templates.md` | 4 个 hook 的代码模板、块 ID 规范、hash 计算、多行写入技巧 | Step 6：生成 hooks 前 |
| `references/acceptance-test.md` | 验收场景 bash 脚本、期望结果、结果表格格式 | Step 6.5：用户选 Y 时读取 |
| `references/lock-file-format.md` | lock 文件 YAML 格式 | Step 9：写入 lock 文件前 |
| `references/git-workflow-template.md` | 工作流文档模板（含占位符） | Step 7：由 render_docs.py 读取 |
| `references/render_docs.py` | 文档渲染脚本 | Step 7：直接执行 |
