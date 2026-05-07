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

不要用宽泛的 `grep "name:"` 提取分支名——YAML 文件中多个层级都可能含有 `name:` 字段，会导致误匹配。

正确方式：用 `python3` 精确解析 YAML，避免依赖缩进层级的文本匹配：

```bash
# 从 workflow-config.yml 提取 branches.protected 下的分支名
python3 -c "
import sys, re
content = open('workflow-config.yml').read()
# 提取 branches.protected 块内所有 '- name: <value>' 条目
in_protected = False
for line in content.splitlines():
    if 'protected:' in line:
        in_protected = True
        continue
    if in_protected:
        m = re.match(r'\s+- name:\s+(\S+)', line)
        if m:
            print(m.group(1))
        elif line.strip() and not line.startswith(' '):
            break
"
```

同理，从 lock 文件提取分支名：

```bash
python3 -c "
import re
content = open('.githooks/.workflow-config.lock.yml').read()
for line in content.splitlines():
    m = re.match(r'\s+- name:\s+(\S+)', line)
    if m:
        print(m.group(1))
"
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

3. **写入 MANAGED 块内容时，禁止用 awk `-v` 传多行 shell 脚本**。多行字符串含换行符时 awk 会报错。正确方式是先将块内容写入临时文件，再用 `python3` 或 `perl` 完成插入替换：

   ```bash
   # 将新 MANAGED 块内容写入临时文件
   TMPBLOCK=$(mktemp)
   cat > "$TMPBLOCK" << 'BLOCKEOF'
   # --- BEGIN MANAGED: branches.protected/develop (hash:PLACEHOLDER) ---
   if [ "$BRANCH" = "develop" ]; then
       ...
   fi
   # --- END MANAGED: branches.protected/develop ---
   BLOCKEOF

   # 用 python3 将临时文件内容插入目标位置（在 exit 0 之前）
   python3 - "$HOOKFILE" "$TMPBLOCK" << 'PYEOF'
   import sys
   hook = open(sys.argv[1]).read()
   block = open(sys.argv[2]).read()
   hook = hook.replace('\nexit 0\n', '\n' + block + '\nexit 0\n', 1)
   open(sys.argv[1], 'w').write(hook)
   PYEOF
   rm "$TMPBLOCK"
   ```

4. **差量写入**：生成全文后与磁盘文件对比
   - 内容相同 → 跳过，标记 `UNCHANGED`
   - 内容不同 → 覆盖写入，标记 `UPDATED`
   - 文件不存在 → 新建，标记 `NEW`

#### MANAGED 块 ID 规范

| hook 文件 | 块 ID |
|-----------|-------|
| pre-commit | `branches.protected/<branch-name>` |
| commit-msg | `commit-msg/format`、`commit-msg/length` |
| pre-push | `pre-push/tags`、`pre-push/force-push` |
| post-checkout | `post-checkout/branch-naming` |

#### Hook 文件结构

每个 hook 文件的整体结构：

```sh
#!/bin/sh
# Generated by git-workflow-init v4.0.0
# Manual edits outside MANAGED blocks are preserved across runs.

<shebang 和公共函数（无 MANAGED 标记，skill 自动识别为固定头部）>

# --- BEGIN MANAGED: branches.protected/main (hash:a3f9c2b1) ---
if [ "$BRANCH" = "main" ]; then
    ...
fi
# --- END MANAGED: branches.protected/main ---

# --- BEGIN MANAGED: branches.protected/staging (hash:b8d21e44) ---
if [ "$BRANCH" = "staging" ]; then
    ...
fi
# --- END MANAGED: branches.protected/staging ---

# 用户自定义区（此处代码不会被覆盖）
```

#### 4 个 hook 的生成内容

**pre-commit**（当 `branches.protected` 存在时）

固定头部（非 MANAGED）：
```sh
#!/bin/sh
# Generated by git-workflow-init v4.0.0
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BRANCH" ] && exit 0
IS_MERGE=0
[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && IS_MERGE=1

merge_source_branch() {
    msg_file="$(git rev-parse --git-dir)/MERGE_MSG"
    [ -f "$msg_file" ] || { printf ''; return; }
    head -1 "$msg_file" | sed "s/Merge branch '//;s/'.*//"
}
```

每个保护分支生成一个 MANAGED 块：
```sh
# --- BEGIN MANAGED: branches.protected/main (hash:<hash>) ---
if [ "$BRANCH" = "main" ]; then
    if [ "$IS_MERGE" -eq 0 ]; then
        echo "❌ 禁止直接在 main 上提交。请在 staging 或 release/* 分支开发后合并。"
        exit 1
    fi
    SRC=$(merge_source_branch)
    case "$SRC" in
        staging|release/*) exit 0 ;;
        *) echo "❌ main 只接受来自 staging 或 release/* 的合并，当前来源：'${SRC:-unknown}'"; exit 1 ;;
    esac
fi
# --- END MANAGED: branches.protected/main ---
```

固定尾部（非 MANAGED）：
```sh
exit 0
```

**commit-msg**（当 `commit_message.enforce: true` 时）

固定头部：
```sh
#!/bin/sh
# Generated by git-workflow-init v4.0.0
MSG=$(cat "$1")
SUBJECT=$(printf '%s\n' "$MSG" | head -1)
SUBJECT=$(printf '%s\n' "$SUBJECT" | sed '/^#/d' | sed 's/^[[:space:]]*//')
[ -z "$SUBJECT" ] && exit 0
```

格式检查 MANAGED 块（`commit-msg/format`）：
- `format: conventional`：拼接 types 列表为正则；`require_scope: false` 时 scope 可选
- `format: regex`：使用 `pattern` 字段

长度检查 MANAGED 块（`commit-msg/length`）：使用 `max_subject_length` 字段

固定尾部：`exit 0`

**pre-push**（当 `tags.enforce: true` 或 `push_rules.enforce: true` 时）

固定头部：
```sh
#!/bin/sh
# Generated by git-workflow-init v4.0.0
while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do
    case "$remote_ref" in
```

tag 检查 MANAGED 块（`pre-push/tags`，仅当 `tags.enforce: true`）
force push 检查 MANAGED 块（`pre-push/force-push`，仅当 `push_rules.enforce: true`）

固定尾部：
```sh
    esac
done
exit 0
```

**post-checkout**（当 `branch_naming.enforce: true` 时）

固定头部：
```sh
#!/bin/sh
# Generated by git-workflow-init v4.0.0
[ "$3" = "1" ] || exit 0
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BRANCH" ] && exit 0
```

命名检查 MANAGED 块（`post-checkout/branch-naming`）：包含 exempt case 块和 allowed_patterns grep 检查

固定尾部：`exit 0`

#### 设置权限和 hooksPath

```bash
chmod +x .githooks/*
git config core.hooksPath .githooks
git config merge.ff false
```

`merge.ff false` 禁止 fast-forward 合并，确保每次合并都产生 merge commit，pre-commit 钩子才能检查合并来源分支。

---

### Step 7 — 从配置渲染并写入工作流文档（差量）

每次运行都根据当前 `workflow-config.yml` 的最终状态重新渲染文档，确保文档与配置始终一致。

#### 7a. 读取模板并渲染各占位符

使用 `references/render_docs.py` 完成渲染：

```bash
python3 <skill-path>/references/render_docs.py \
  workflow-config.yml \
  <skill-path>/references/git-workflow-template.md \
  docs/reference/git-workflow.md
# 输出 NEW / UPDATED / UNCHANGED
```

脚本读取 `references/git-workflow-template.md`，将以下占位符替换为从配置生成的内容：

---

**`{{BRANCH_TOPOLOGY_ASCII}}`** — ASCII 分支拓扑树

从 `branches.protected` 生成，第一个受保护分支为根节点，其 `merge_from` 分支为子节点，以此类推。

示例（main ← staging ← feature/*）：
```
main
  <- staging
        <- feature/*
        <- fix/*
  <- release/*
```

---

**`{{BRANCH_TABLE}}`** — 分支说明 Markdown 表格

表头固定为 `| 分支 | 用途 | 合并目标 |`。

行生成规则：
- `branches.protected` 中的每个分支生成一行，用途根据分支名推断（main→生产就绪代码，staging→集成/预发布，develop→开发集成，release/*→发版准备）
- `branch_naming.allowed_patterns` 中的每个 pattern 额外生成一行，前缀从正则中提取（`^feature/.+` → `feature/<名称>`），用途同样按约定推断

---

**`{{PROTECTION_RULES}}`** — 分支保护规则列表

对 `branches.protected` 中每个分支生成一条 bullet：
```
- **`<name>`** — 禁止直接提交。只接受来自 `<merge_from[0]>` 或 `<merge_from[1]>` 的合并。
```
若 `allow_direct_commit: true` 则改为"直接提交时仅发出警告"。

---

**`{{WORKFLOW_CHECKOUT_EXAMPLE}}`** / **`{{WORKFLOW_MERGE_EXAMPLE}}`** / **`{{WORKFLOW_RELEASE_EXAMPLE}}`** — 开发流程示例命令

从 `branches.protected` 推断：
- 集成分支 = 非 main、非 release/* 且最多被 main 合并的分支（通常是 staging 或 develop）
- 主分支 = main（或 `merge_from` 中没有其他受保护分支的顶层分支）

生成对应的 `git checkout` / `git merge` / `git push` 示例命令。

---

**`{{NAMING_TABLE}}`** — 分支命名规范表格

表头：`| 前缀 | 适用场景 | 示例 |`

对 `branch_naming.allowed_patterns` 中每个 pattern 生成一行：
- 从正则提取前缀（`^feature/.+` → `feature/`）
- 用途按约定推断（feature→新功能，fix→Bug 修复，chore→非功能性变更，doc/docs→文档，release→发版切点）
- 示例生成两个具体名称（`feature/user-auth`、`feature/dark-mode`）

---

**`{{NAMING_EXEMPT}}`** — 豁免分支

将 `branch_naming.exempt` 列表拼接为 `` `main`、`staging` `` 格式。

---

**`{{COMMIT_FORMAT_SECTION}}`** — 提交信息格式说明

根据 `commit_message.format` 生成不同内容：

- `format: conventional`：
  ```
  遵循 Conventional Commits 规范：<类型>(<范围>): <描述>
  **类型：** `feat` | `fix` | `chore` | ...（从 types 列表生成）
  **首行长度限制：** <max_subject_length> 个字符
  ```

- `format: regex`：
  ```
  提交信息首行必须匹配正则：`<pattern>`
  **首行长度限制：** <max_subject_length> 个字符
  ```

- `format: none`：
  ```
  本项目无提交信息格式要求。
  ```

---

**`{{FAQ_SECTION}}`** — 常见问题动态部分

根据实际分支名生成对应 FAQ 条目：
- 若存在集成分支（如 staging）：生成"在 staging 上提交被拒绝怎么办"
- 若存在 release/* 分支规则：生成"紧急热修复怎么办"

---

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

将本次配置的关键字段写入 `.githooks/.workflow-config.lock.yml`：

```yaml
# Generated by git-workflow-init, do not edit manually
generated_at: "<ISO 8601 timestamp>"
skill_version: "4.0.0"
branches_protected:
  - name: main
    allow_direct_commit: false
    merge_from: [staging, "release/*"]
commit_message:
  format: conventional
  types: [feat, fix, chore, docs, refactor, test, style, perf]
  max_subject_length: 80
branch_naming:
  allowed_patterns: ["^feature/.+", "^fix/.+", ...]
  exempt: [main, staging]
tags:
  allowed_patterns: ["^v[0-9]+\\.[0-9]+\\.[0-9]+$", ...]
  require_annotated: true
push_rules:
  block_force_push: [main, staging]
```

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

| 文件 | 说明 |
|------|------|
| `references/workflow-config.yml` | 配置文件模板 |
| `references/install-git-hooks.sh` | 独立激活脚本（重新设置 hooksPath 用，无需重跑完整 skill） |
| `references/git-workflow-template.md` | 工作流文档模板 |
