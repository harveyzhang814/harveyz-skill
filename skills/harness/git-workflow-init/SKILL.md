---
name: git-workflow-init
description: 初始化或更新 git 分支管理规范：读取项目的 workflow-config.yml，审核配置，差量生成并部署 git hooks（pre-commit、commit-msg、pre-push、post-checkout），生成工作流文档，可选写入 AI 配置文件引用。支持差量更新、MANAGED 块 hash 校验（检测用户手改）、lock 文件 diff（检测配置变更）、conflict scanner（检测用户代码与新配置的交叉冲突）。触发时机：初始化新 git 仓库、新项目首次配置 git、用户要求设置/更新分支保护或分支规范、安装或重新部署 git hooks、skill 或模板更新后需要同步、或问到分支命名规范。只要项目需要配置或更新 git 工作流，就应使用此 skill。
user_invocable: true
version: "4.0.0"
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

此步骤目标：在写入任何文件之前，全面了解当前状态，收集所有需要用户决策的冲突，在 Step 5 一次性呈现。

#### 4a. Lock 文件 diff — 配置发生了什么变化

读取 `.githooks/.workflow-config.lock.yml`（若不存在则视为全量新增，跳过 diff）。

将 lock 文件中记录的上一次配置与当前配置对比，生成变更摘要：

```
配置变更摘要：
+ branches.protected 新增: develop（merge_from: feature/*）
~ commit_message.conventional.types 修改: 新增 wip，移除 perf
- tags.allowed_patterns 删除: ^v[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$
```

**YAML 分支名提取规则（重要）：**

不要用宽泛的 `grep "name:"` 提取分支名——YAML 多个层级都可能含有 `name:` 字段，会导致误匹配。用 `python3` 精确解析，进入 `protected:` 块后再匹配 `- name:`，遇到非缩进行则停止：

```bash
# FILE 传入要解析的文件路径（workflow-config.yml 或 lock 文件均适用）
python3 -c "
import re, sys
content = open(sys.argv[1]).read()
in_protected = False
for line in content.splitlines():
    if 'protected:' in line:
        in_protected = True; continue
    if in_protected:
        m = re.match(r'\s+- name:\s+(\S+)', line)
        if m: print(m.group(1))
        elif line.strip() and not line.startswith(' '): break
" "$FILE"
```

这份摘要用于后续冲突检测的输入。

#### 4b. MANAGED 块 hash 校验 — 用户是否手改了生成的代码

读取每个 hook 文件，提取所有 `BEGIN MANAGED` / `END MANAGED` 块。

MANAGED 块格式：
```sh
# --- BEGIN MANAGED: <block-id> (hash:<8位hex>) ---
<generated content>
# --- END MANAGED: <block-id> ---
```

对每个块：重新计算块内容（两行标记之间的部分，去首尾空白）的 hash：
```bash
actual_hash=$(printf '%s' "<block_content>" | git hash-object --stdin | cut -c1-8)
```

若 `actual_hash` 与标记里记录的 hash 不一致 → 用户手改了此块，记录为冲突：

```
[手改冲突] .githooks/pre-commit 的 MANAGED 块 branches.protected/main 被手动修改
  原始生成内容 hash: a3f9c2b1
  当前内容 hash:     d7e42f0c
  差异：（展示 diff）
```

#### 4c. 外部代码扫描 — 用户在 MANAGED 块外添加了什么

提取每个 hook 文件中 MANAGED 块之外的所有代码（即用户手写区）。

从用户代码中提取可解析的引用：

| 提取目标 | 扫描方式 |
|---------|---------|
| 分支名 | `"$BRANCH" = "name"`、`case "name"`、`branch = "name"` |
| 提交类型 | `grep -qE "...(type\|...)"`、字符串字面量 `wip`、`hotfix` |
| Tag/分支 pattern | `grep -qE "pattern"` |
| 外部脚本调用 | `./`、`bash `、`sh `、`npm run`、`make ` 开头的行 |

#### 4d. 冲突检测 — 用户代码 × 新配置的交叉分析

综合 4a（配置变更）、4b（手改块）、4c（用户代码）的结果，识别以下冲突类型：

**冲突类型 A：用户代码覆盖了与新配置相同的条件**
- 用户代码处理了分支 X，新配置也将 X 加入 `branches.protected`
- 两段代码同时执行，可能产生矛盾行为

**冲突类型 B：用户代码引用了配置中已删除的内容**
- 用户代码里有对类型 `wip` 的处理，新配置删除了 `wip`
- 用户代码逻辑失去对应的配置支撑

**冲突类型 C：MANAGED 块被手动修改**
- 来自 4b 的结果
- 重新生成会覆盖用户修改

**冲突类型 D：用户代码引用了新配置新增的内容（信息提示，非阻断）**
- 用户已手写了对 `develop` 的处理，新配置也打算生成同名 MANAGED 块
- 不一定冲突，但值得用户确认

---

### Step 5 — 冲突解决（一次性汇总，用户逐条决策）

将 Step 4 发现的所有冲突汇总后**一次性呈现**，每条冲突附带建议选项。

示例输出：

```
发现 3 处需要决策的冲突，请逐条确认：

─────────────────────────────────────────────────────────
[1/3] 手改冲突（类型 C）
文件: .githooks/pre-commit，块: branches.protected/main
用户对生成代码做了如下修改：
  - echo "❌ 禁止直接在 main 上提交。"
  + echo "❌ [POLICY] 禁止直接在 main 上提交，违规请联系 @team-lead。"
选项：
  A) 保留用户修改（此块不重新生成）
  B) 用新配置覆盖（丢弃用户修改）
─────────────────────────────────────────────────────────
[2/3] 条件重叠（类型 A）
文件: .githooks/pre-commit，用户代码第 58 行
用户手写了 develop 分支的保护逻辑
新配置将 develop 加入 branches.protected，也会生成对应 MANAGED 块
选项：
  A) 保留用户代码，跳过生成 develop 的 MANAGED 块
  B) 用新配置生成 MANAGED 块，删除用户手写的重复代码
  C) 两者都保留（会重复执行，请确认逻辑不矛盾）
─────────────────────────────────────────────────────────
[3/3] 引用断裂（类型 B）
文件: .githooks/commit-msg，用户代码第 34 行
用户代码引用了 commit 类型 wip，但新配置已从类型列表中移除 wip
选项：
  A) 保留用户代码（wip 检查逻辑继续生效，但配置层不再管理）
  B) 删除用户代码中对 wip 的引用
─────────────────────────────────────────────────────────
```

用户全部决策完成后，带着决策结果进入 Step 6。
若无任何冲突，直接进入 Step 6。

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

若用户选 **N**，跳过此步骤，直接进入 Step 7。

若用户选 **Y**，执行以下步骤。

#### 初始化

记录当前分支与时间戳（用于临时分支命名和临时文件命名，避免冲突）：

```bash
ORIGINAL_BRANCH=$(git symbolic-ref --short HEAD)
TIMESTAMP=$(date +%s)
```

#### 逐 hook 运行验收场景

仅对 Step 6 中实际生成的 hook 运行对应场景。未生成的 hook 跳过，不报告。

**pre-commit 验收**（仅当 `branches.protected` 非空时生成了 pre-commit）

取配置中第一个保护分支名：

```bash
PROTECTED_BRANCH=<从 workflow-config.yml 的 branches.protected 取第一个 name 字段>

# 若当前不在该分支，切换过去；若分支不存在则新建
SWITCHED=0
if [ "$(git symbolic-ref --short HEAD 2>/dev/null)" != "$PROTECTED_BRANCH" ]; then
    git checkout "$PROTECTED_BRANCH" 2>/dev/null \
        || git checkout -b "$PROTECTED_BRANCH" 2>/dev/null
    SWITCHED=1
fi

# 直接调用 hook 脚本（不产生实际 commit）
output=$(sh .githooks/pre-commit 2>&1)
exit_code=$?

# 立即还原分支
[ "$SWITCHED" = "1" ] && git checkout "$ORIGINAL_BRANCH" 2>/dev/null

# 期望 exit_code = 1（hook 拦截了直接提交）
```

**commit-msg 验收**（仅当 `commit_message.enforce: true`）

构造格式违规消息：
- `format: conventional` → 使用 `"bad commit"`（不含类型前缀）
- `format: regex` → 使用一个确定不匹配 `pattern` 的字符串，如 `"NOMATCH: this should fail"`

```bash
echo "bad commit" > /tmp/gwi-test-msg-${TIMESTAMP}.txt
output=$(sh .githooks/commit-msg /tmp/gwi-test-msg-${TIMESTAMP}.txt 2>&1)
exit_code=$?
rm -f /tmp/gwi-test-msg-${TIMESTAMP}.txt

# 期望 exit_code = 1
```

**pre-push force-push 验收**（仅当 `push_rules.enforce: true`）

取 `push_rules.block_force_push` 中第一个分支名：

```bash
PROTECTED_PUSH_BRANCH=<从 push_rules.block_force_push 取第一个分支名>
output=$(printf "refs/heads/%s abc1234 refs/heads/%s 0000000000000000000000000000000000000000\n" \
    "$PROTECTED_PUSH_BRANCH" "$PROTECTED_PUSH_BRANCH" \
    | sh .githooks/pre-push 2>&1)
exit_code=$?

# 期望 exit_code = 1
```

**pre-push tag 验收**（仅当 `tags.enforce: true`）

```bash
output=$(printf "refs/tags/invalid-tag-format abc1234 refs/tags/invalid-tag-format 0000000000000000000000000000000000000000\n" \
    | sh .githooks/pre-push 2>&1)
exit_code=$?

# 期望 exit_code = 1
```

**post-checkout 验收**（仅当 `branch_naming.enforce: true`）

创建一个确定不符合 `allowed_patterns` 的临时分支名（固定前缀 `gwi-test-INVALID-NAME-` 不在任何常见命名规范中）：

```bash
TEST_BRANCH="gwi-test-INVALID-NAME-${TIMESTAMP}"
git checkout -b "$TEST_BRANCH" 2>/dev/null

output=$(sh .githooks/post-checkout HEAD HEAD 1 2>&1)

# 立即还原并删除临时分支
git checkout "$ORIGINAL_BRANCH" 2>/dev/null
git branch -D "$TEST_BRANCH" 2>/dev/null

# 期望：output 包含 ⚠️
```

#### 展示结果

收集所有场景的结果，用表格展示：

```
验收测试结果：
──────────────────────────────────────────────────────
pre-commit    直接提交到 <branch>（应拒绝）           PASS ✅
commit-msg    格式违规消息（应拒绝）                   PASS ✅
pre-push      force push 到 <branch>（应拒绝）         PASS ✅
pre-push      非法 tag 推送（应拒绝）                  PASS ✅
post-checkout 不合规分支名（应有 ⚠️ 警告）             PASS ✅
──────────────────────────────────────────────────────
✅ 全部通过（N/N）。继续 Step 7...
```

若有失败：

```
──────────────────────────────────────────────────────
pre-commit    直接提交到 main（应拒绝）                FAIL ❌
  期望 exit 1，实际 exit 0
  输出：（空）
  可能原因：core.hooksPath 配置错误或 hook 脚本有语法问题
──────────────────────────────────────────────────────
❌ 验收未通过（M/N 失败）。是否仍继续 Step 7？[y/N]
```

用户选 **N** → 提示 `请检查 .githooks/ 目录和 core.hooksPath 配置后重新运行 /git-workflow-init`，停止。
用户选 **Y** → 继续 Step 7。

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
| `references/hook-templates.md` | 4 个 hook 的代码模板、块 ID 规范、hash 计算、多行写入技巧 | Step 6：生成 hooks 前 |
| `references/lock-file-format.md` | lock 文件 YAML 格式 | Step 9：写入 lock 文件前 |
| `references/git-workflow-template.md` | 工作流文档模板（含占位符） | Step 7：由 render_docs.py 读取 |
| `references/render_docs.py` | 文档渲染脚本 | Step 7：直接执行 |
