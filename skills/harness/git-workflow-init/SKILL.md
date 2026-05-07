---
name: git-workflow-init
description: 初始化或更新 git 分支管理规范：读取项目的 workflow-config.yml，审核配置合法性，动态生成并部署 git hooks（pre-commit、commit-msg、pre-push、post-checkout），生成工作流文档，可选写入 AI 配置文件引用。支持差量更新（只重写有变化的 hook）和外部规则发现（识别现有 hooks 中不属于 workflow-config.yml 的规则并引导导入）。触发时机：初始化新 git 仓库、新项目首次配置 git、用户要求设置/更新分支保护或分支规范、安装或重新部署 git hooks、skill 或模板更新后需要同步、或问到分支命名规范。只要项目需要配置或更新 git 工作流，就应使用此 skill。
user_invocable: true
version: "3.0.0"
---

# Git 工作流初始化

读取项目根目录的 `workflow-config.yml`，审核配置，动态生成对应 git hooks 并差量部署。
重新运行时自动识别现有 hooks 中的外部规则，引导导入到 `workflow-config.yml`。

## 此 Skill 做的事

1. **扫描现有 hooks** — 若 `.githooks/` 已存在，识别不属于当前配置的外部规则并提供导入
2. **审核配置** — 检查 `workflow-config.yml` 的结构、逻辑和正则合法性
3. **差量部署 hooks** — 只重写内容有变化的 hook，跳过相同的
4. **生成工作流文档** — 将配置内容渲染为 `docs/reference/git-workflow.md`
5. **更新 AI 配置文件（可选）** — 在 `CLAUDE.md`、`AGENTS.md`、`GEMINI.md` 中追加索引引用

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
- 是否使用默认配置（从此 skill 的 `references/workflow-config.yml` 复制到项目根目录）
- 还是中止并自行创建配置后再运行

找到配置文件后，读取并解析 YAML 内容。

---

### Step 2b — 扫描现有 hooks，发现外部规则

**仅当 `.githooks/` 目录已存在时执行此步骤。**

目标：找出现有 hooks 中不属于当前 `workflow-config.yml` 覆盖范围的规则，让用户决定是否将其纳入配置。这样能保证配置文件成为唯一的事实来源，避免手动规则在重新生成时被覆盖。

#### 扫描方法

逐一读取 `.githooks/` 中存在的 hook 文件，与当前配置"应当生成的内容"进行比对，提取超出配置范围的部分：

**pre-commit 中的外部规则：**
- 保护分支列表之外的额外分支 if 块（分支名不在 `branches.protected` 中）
- `allow_direct_commit: true` 但 hook 中使用了 `exit 1`（配置与实现不一致）
- 调用外部脚本或命令（如 `npm run lint`、`./scripts/check.sh`）
- 其他任何不符合此 skill 模板结构的代码块

**commit-msg 中的外部规则：**
- 类型列表与 `commit_message.conventional.types` 不一致（多出或少了类型）
- 使用了与配置不同的正则 pattern
- 额外的检查逻辑（如禁止特定词、强制 issue 编号）

**pre-push 中的外部规则：**
- tag 格式 pattern 与 `tags.allowed_patterns` 不一致
- force push 保护分支与 `push_rules.block_force_push` 不一致
- 额外的推送拦截逻辑

**post-checkout 中的外部规则：**
- 分支命名 pattern 与 `branch_naming.allowed_patterns` 不一致
- 豁免分支与 `branch_naming.exempt` 不一致

**完全未被配置覆盖的 hook 文件（如 `pre-rebase`、`prepare-commit-msg`）：**
- 完整展示文件内容，标记为"配置无对应项"

#### 报告与导入流程

将发现的外部规则汇总后一次性展示给用户，格式如下：

```
发现以下规则不在 workflow-config.yml 中：

[pre-commit] 额外保护分支: develop
  当前规则: 禁止直接提交，仅允许来自 feature/* 的合并
  → 建议添加到 branches.protected

[commit-msg] 额外提交类型: wip, hotfix
  当前类型列表: feat|fix|chore|docs|refactor|test|style|perf
  → 建议添加到 commit_message.conventional.types

[pre-commit] 外部脚本调用: npm run lint
  原始代码: npm run lint || exit 1
  → 无法自动映射，需手动决策
```

询问用户：**"是否将这些规则导入 workflow-config.yml？"**

- **可自动映射的规则**（额外分支名、额外类型、额外 pattern）：直接修改 `workflow-config.yml` 对应字段
- **无法自动映射的规则**（外部脚本、复杂逻辑）：告知用户需手动处理，并在后续 Step 4 中**保留**这部分代码不覆盖（见差量更新说明）

用户选择"否"时跳过导入，继续执行后续步骤。

---

### Step 3 — 审核配置

对配置内容逐项检查，发现问题时**列出所有问题后一次性报告**，不要逐条中止。

**结构校验：**
- `meta.preset` 若存在，必须是 `gitflow`、`github-flow`、`trunk-based`、`custom` 之一
- `commit_message.format` 必须是 `conventional`、`regex`、`none` 之一
- 若 `format: regex`，必须同时存在 `pattern` 字段

**逻辑校验：**
- `branches.protected` 中，任何分支的 `merge_from` 不得包含自身名称（循环依赖）
- `push_rules.block_force_push` 中的分支名建议与 `branches.protected` 保持一致，若不一致则警告（不阻断）
- `branch_naming.exempt` 中的分支不应同时出现在 `allowed_patterns` 覆盖范围内（提示冗余）

**正则校验：**
- `branch_naming.allowed_patterns` 中每个条目必须是合法的 POSIX ERE 正则
- `tags.allowed_patterns` 中每个条目必须是合法的 POSIX ERE 正则
- 若 `format: regex`，`pattern` 字段必须是合法的 POSIX ERE 正则

验证方式（对每个 pattern 执行，检查 grep 是否报错）：
```bash
echo "" | grep -E "<pattern>" > /dev/null 2>&1; echo $?
```
返回 0 或 1 均可（0=匹配，1=不匹配），返回 2 = 正则非法。

**审核通过：** 打印 `✅ 配置审核通过` 并列出将安装的 hooks 摘要，继续执行。  
**审核失败：** 列出所有问题，停止执行，请用户修复后重新运行。

---

### Step 4 — 差量生成并部署 hooks

```bash
mkdir -p .githooks
```

#### 差量更新原则

在写入任何 hook 文件之前，先将"根据当前配置应生成的内容"与"磁盘上现有文件的内容"进行比对：

- **内容相同** → 跳过，标记为 `UNCHANGED`
- **内容不同** → 覆盖写入，标记为 `UPDATED`
- **文件不存在** → 新建，标记为 `NEW`
- **配置中已禁用（enforce: false）但文件存在** → 询问用户是否删除，标记为 `DISABLED`

**保留外部规则：** 若 Step 2b 中发现了无法映射的外部规则（外部脚本、自定义逻辑），在重新生成对应 hook 时，将这些代码块原样追加到生成内容之后，而非直接覆盖。这样自定义逻辑不会在重新运行时丢失。

在 Step 7 汇报时，用表格展示每个 hook 的状态：

```
hook 文件          状态
pre-commit        UPDATED   （分支保护规则有变化）
commit-msg        UNCHANGED
pre-push          UNCHANGED
post-checkout     NEW
```

根据配置中各节的 `enforce` 值决定是否生成对应 hook。**直接写入文件，不运行安装脚本。**

#### 4a. pre-commit（当 `branches.protected` 存在时）

生成规则：遍历 `branches.protected`，为每个条目生成一个 if 块。

```sh
#!/bin/sh
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BRANCH" ] && exit 0
IS_MERGE=0
[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && IS_MERGE=1

merge_source_branch() {
    msg_file="$(git rev-parse --git-dir)/MERGE_MSG"
    [ -f "$msg_file" ] || { printf ''; return; }
    head -1 "$msg_file" | sed "s/Merge branch '//;s/'.*//"
}

# [为每个 protected branch 生成对应块，示例如下]

if [ "$BRANCH" = "main" ]; then
    if [ "$IS_MERGE" -eq 0 ]; then
        # allow_direct_commit: false → exit 1；true → 仅警告
        echo "❌ 禁止直接在 main 上提交。请在 staging 或 release/* 分支开发后合并。"
        exit 1
    fi
    SRC=$(merge_source_branch)
    case "$SRC" in
        # merge_from 列表转为 shell case pattern，以 | 分隔
        staging|release/*) exit 0 ;;
        *) echo "❌ main 只接受来自 staging 或 release/* 的合并，当前来源：'${SRC:-unknown}'"; exit 1 ;;
    esac
fi

exit 0
```

`merge_from` 列表转 case pattern 规则：
- `staging` → `staging`
- `"release/*"` → `release/*`
- 多个条目以 `|` 连接：`staging|release/*`

#### 4b. commit-msg（当 `commit_message.enforce: true` 时）

```sh
#!/bin/sh
MSG=$(cat "$1")
SUBJECT=$(printf '%s\n' "$MSG" | head -1)
SUBJECT=$(printf '%s\n' "$SUBJECT" | sed '/^#/d' | sed 's/^[[:space:]]*//')
[ -z "$SUBJECT" ] && exit 0
```

- `format: conventional`：从 `types` 列表拼接正则 `^(feat|fix|...) `；`require_scope: false` 时 scope 为可选 `(\(.+\))?`
- `format: regex`：直接使用 `pattern` 字段
- 添加 `max_subject_length` 字符数检查

conventional 检查片段：
```sh
if ! printf '%s\n' "$SUBJECT" | grep -qE "^(feat|fix|chore|docs|refactor|test|style|perf)(\(.+\))?: .+"; then
    echo "❌ 提交信息不符合 Conventional Commits 规范"
    echo "   格式：<类型>(<范围>): <描述>"
    echo "   有效类型：feat | fix | chore | docs | refactor | test | style | perf"
    exit 1
fi

LEN=$(printf '%s' "$SUBJECT" | wc -c | tr -d ' ')
if [ "$LEN" -gt 80 ]; then
    echo "❌ 提交信息首行超过 80 个字符（当前 ${LEN} 个字符）"
    exit 1
fi
```

#### 4c. pre-push（当 `tags.enforce: true` 或 `push_rules.enforce: true` 时）

两个功能合并到同一个 `pre-push` 文件中，通过 ref 前缀区分：

```sh
#!/bin/sh
while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do

    case "$remote_ref" in
        refs/tags/*)
            # [仅当 tags.enforce: true 时生成此段]
            tag_name="${remote_ref#refs/tags/}"
            VALID=0
            # [为每个 allowed_pattern 生成一行 grep 检查]
            printf '%s\n' "$tag_name" | grep -qE "^v[0-9]+\.[0-9]+\.[0-9]+$" && VALID=1
            printf '%s\n' "$tag_name" | grep -qE "^v[0-9]+\.[0-9]+\.[0-9]+-.+$" && VALID=1
            if [ "$VALID" -eq 0 ]; then
                echo "❌ Tag 名称不符合命名规范：'$tag_name'"
                echo "   允许格式：v1.2.3 或 v1.2.3-rc.1"
                exit 1
            fi
            # [仅当 require_annotated: true 时生成此段]
            if [ "$(git cat-file -t "$local_sha" 2>/dev/null)" != "tag" ]; then
                echo "❌ 请使用 annotated tag：git tag -a $tag_name -m '<描述>'"
                exit 1
            fi
            ;;

        refs/heads/*)
            # [仅当 push_rules.enforce: true 时生成此段]
            branch="${remote_ref#refs/heads/}"
            # [为 block_force_push 列表中每个分支生成检查]
            case "$branch" in
                main|staging)
                    if [ "$remote_sha" != "0000000000000000000000000000000000000000" ]; then
                        if ! git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
                            echo "❌ 禁止强制推送到 $branch"
                            exit 1
                        fi
                    fi
                    ;;
            esac
            ;;
    esac
done
exit 0
```

#### 4d. post-checkout（当 `branch_naming.enforce: true` 时）

```sh
#!/bin/sh
[ "$3" = "1" ] || exit 0      # 仅在分支切换时触发，不在文件 checkout 时触发
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BRANCH" ] && exit 0

# [从 exempt 列表生成 case 块]
case "$BRANCH" in
    main|staging) exit 0 ;;
esac

# [为每个 allowed_pattern 生成一行 grep，任意匹配则通过]
VALID=0
printf '%s\n' "$BRANCH" | grep -qE "^feature/.+" && VALID=1
printf '%s\n' "$BRANCH" | grep -qE "^fix/.+" && VALID=1
printf '%s\n' "$BRANCH" | grep -qE "^chore/.+" && VALID=1
printf '%s\n' "$BRANCH" | grep -qE "^doc/.+" && VALID=1
printf '%s\n' "$BRANCH" | grep -qE "^release/[0-9]+\.[0-9]+\.[0-9]+(-.+)?$" && VALID=1

if [ "$VALID" -eq 0 ]; then
    echo "⚠️  分支名 '$BRANCH' 不符合命名规范"
    echo "   建议格式：feature/<名称>、fix/<名称>、chore/<名称>、doc/<名称>、release/<版本>"
fi
exit 0    # advisory 模式：只警告，不阻断
```

#### 4e. 设置权限和 hooksPath

写入所有 hook 文件后：

```bash
chmod +x .githooks/*
git config core.hooksPath .githooks
```

---

### Step 5 — 写入工作流文档（差量）

1. 若 `docs/reference/` 不存在则创建
2. 读取此 skill 的 `references/git-workflow-template.md`
3. 将配置中的实际分支规则、命名规范、提交格式填入文档
4. 与现有 `docs/reference/git-workflow.md` 内容比对：内容相同则跳过，不同则覆盖写入
5. 若 `docs/INDEX.md` 已存在，在对应分类追加一行索引（已存在该行则跳过）

---

### Step 6 — 更新 AI 配置文件（可选）

若此前已有引用（文件中已包含 `docs/reference/git-workflow.md` 的链接），跳过此步骤，不重复追加。

否则询问用户："是否在 AI 配置文件（CLAUDE.md、AGENTS.md、GEMINI.md）中添加对 git 工作流文档的引用？"

若同意，对**已存在**的文件追加（不存在的文件不主动创建）：

```markdown
## Git 工作流

分支命名规范、保护规则与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。
```

---

### Step 7 — 汇报结果

用表格展示每个操作的状态：

```
文件                              状态
workflow-config.yml              已读取（导入了 N 条外部规则）
.githooks/pre-commit             UPDATED
.githooks/commit-msg             UNCHANGED
.githooks/pre-push               UNCHANGED
.githooks/post-checkout          NEW
core.hooksPath                   = .githooks
docs/reference/git-workflow.md   UPDATED
CLAUDE.md                        已有引用，跳过
```

若有无法自动映射的外部规则被保留，在表格后附注：

```
⚠️  以下外部规则已保留在 hook 文件末尾，未纳入 workflow-config.yml 管理：
- .githooks/pre-commit: npm run lint（外部脚本调用）
  如需统一管理，请手动编辑 workflow-config.yml 并重新运行。
```

---

## 参考文件

| 文件 | 说明 |
|------|------|
| `references/workflow-config.yml` | 配置文件模板，用户复制到项目根目录后编辑 |
| `references/install-git-hooks.sh` | 独立安装脚本（重新激活已有配置用，无需重跑完整 skill） |
| `references/git-workflow-template.md` | 工作流文档模板 |
