# git-workflow-init 验收测试 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `git-workflow-init` skill 的 Step 6 之后插入 Step 6.5——先询问用户是否运行验收测试，若同意则在真实 repo 中直接调用已安装的 hook 脚本，验证其拦截行为，完成后清理所有临时痕迹。

**Architecture:** 纯 SKILL.md 内容修改（面向 LLM 执行的自然语言 + bash 片段），无独立代码文件。TDD 体现为先在 evals.json 中写明期望行为（eval 用例），再实现 Step 6.5，最后对照 eval 用例验证实现正确性。

**Tech Stack:** Shell (sh/bash)、git 命令、SKILL.md 自然语言指令

---

## 文件变更

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/harness/git-workflow-init/evals/evals.json` | 修改 | 新增 3 条 eval 用例（先写，TDD） |
| `skills/harness/git-workflow-init/SKILL.md` | 修改 | 在 Step 6 结尾与 Step 7 开头之间插入 Step 6.5 |

---

## Task 1：在 evals.json 中新增验收测试行为的 eval 用例

> TDD 第一步：先定义期望行为，再实现。

**Files:**
- Modify: `skills/harness/git-workflow-init/evals/evals.json`

- [ ] **Step 1.1：读取 evals.json 当前内容，找到 `v4_evals` 数组末尾**

打开 `skills/harness/git-workflow-init/evals/evals.json`，定位到 `v4_evals` 数组最后一个元素（id: 9）的闭合 `}`。

- [ ] **Step 1.2：在 `v4_evals` 数组末尾追加 3 条 eval 用例**

将 `v4_evals` 数组替换为包含以下新增条目的版本（在 id: 9 之后追加）：

```json
    {
      "id": 10,
      "name": "acceptance-test-skip",
      "prompt": "我的项目在 /tmp/gwi-acc-skip，已 git init，有默认 workflow-config.yml（branches.protected 包含 main 和 staging，commit_message.enforce: true）。请运行 git-workflow-init，hooks 部署完成后，当 skill 询问是否运行验收测试时，我选择跳过（N）。",
      "expected_output": "Step 6 完成后 skill 询问是否运行验收测试，用户回答 N 后 skill 跳过验收直接继续 Step 7 文档渲染，最终正常完成整个流程。",
      "assertions": [
        "Step 6 完成后出现验收询问提示",
        "用户选 N 后 skill 不执行任何 hook 调用测试",
        "skill 继续执行 Step 7 及后续步骤，正常完成"
      ]
    },
    {
      "id": 11,
      "name": "acceptance-test-pass",
      "prompt": "我的项目在当前目录，已有 .githooks/（含 pre-commit、commit-msg），git config core.hooksPath 已设置为 .githooks，pre-commit 会拒绝直接提交到 main，commit-msg 强制 Conventional Commits 格式。hooks 刚部署完，我选择运行验收测试（Y）。",
      "expected_output": "skill 在真实 repo 中直接调用 .githooks/pre-commit（在受保护分支上，期望 exit 1）和 .githooks/commit-msg（传入违规消息，期望 exit 1），两项均通过，展示 PASS 表格，继续 Step 7。无残留临时文件或临时分支。",
      "assertions": [
        "skill 询问用户是否运行验收测试，用户选 Y 后执行",
        "pre-commit 验收：在受保护分支（main 或 staging）调用 .githooks/pre-commit，期望 exit 1，实际得到 exit 1 → PASS",
        "commit-msg 验收：以违规消息调用 .githooks/commit-msg，期望 exit 1，实际得到 exit 1 → PASS",
        "展示包含 PASS 标记的结果表格",
        "验收完成后无 /tmp/gwi-test-* 临时文件残留",
        "验收完成后无 gwi-test-INVALID-NAME-* 临时分支残留",
        "skill 继续执行 Step 7"
      ]
    },
    {
      "id": 12,
      "name": "acceptance-test-fail",
      "prompt": "我的项目 .githooks/pre-commit 已安装，但 git config core.hooksPath 没有设置（hooks 实际不会被触发）。部署完成后我选择运行验收测试（Y）。",
      "expected_output": "skill 调用 .githooks/pre-commit 时，因为脚本本身读取 git symbolic-ref 正常但实际 core.hooksPath 未配置不影响直接调用测试，但若 pre-commit 返回 exit 0（未拦截），skill 报告 FAIL，展示失败详情（期望 exit 1，实际 exit 0），询问用户是否仍继续 Step 7。",
      "assertions": [
        "验收结果表格中对应 hook 标记为 FAIL ❌",
        "失败详情包含：期望 exit code、实际 exit code、hook 输出内容",
        "skill 询问用户是否仍继续后续步骤，而非直接中止或直接继续",
        "用户选 N 后 skill 优雅停止"
      ]
    }
```

- [ ] **Step 1.3：验证 JSON 格式合法**

```bash
python3 -c "import json; json.load(open('skills/harness/git-workflow-init/evals/evals.json')); print('JSON valid')"
```

期望输出：`JSON valid`

- [ ] **Step 1.4：提交**

```bash
git add skills/harness/git-workflow-init/evals/evals.json
git commit -m "test: add acceptance testing eval cases (ids 10-11-12) for git-workflow-init"
```

---

## Task 2：在 SKILL.md 中实现 Step 6.5

**Files:**
- Modify: `skills/harness/git-workflow-init/SKILL.md`

插入位置：Step 6 末尾（`merge.ff false` 说明段落与 `---` 分隔线之后）和 Step 7 标题之前。

- [ ] **Step 2.1：定位精确插入点**

在 `SKILL.md` 中找到以下字符串（这是 Step 6 结尾的 `---` 分隔线，紧接着是 Step 7 标题）：

```
`merge.ff false` 禁止 fast-forward 合并，确保每次合并都产生 merge commit，pre-commit 钩子才能检查合并来源分支。

---

### Step 7 — 从配置渲染并写入工作流文档（差量）
```

- [ ] **Step 2.2：在上述位置之间插入 Step 6.5 完整内容**

将上面定位到的文本替换为：

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

取 `push_rules.block_force_push` 中第一个分支：

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
```

- [ ] **Step 2.3：检查插入后 SKILL.md 没有重复的 Step 7 标题，整体结构完整**

```bash
grep -n "^### Step" skills/harness/git-workflow-init/SKILL.md
```

期望输出（每个 Step 只出现一次，Step 6.5 在 Step 6 和 Step 7 之间）：

```
<行号>:### Step 1 — 确认 git 仓库
<行号>:### Step 2 — 读取配置
<行号>:### Step 3 — 审核配置
<行号>:### Step 4 — 分析当前状态（仅当 `.githooks/` 已存在时）
<行号>:### Step 5 — 冲突解决（一次性汇总，用户逐条决策）
<行号>:### Step 6 — 差量生成并部署 hooks
<行号>:### Step 6.5 — 验收测试（可选）
<行号>:### Step 7 — 从配置渲染并写入工作流文档（差量）
<行号>:### Step 8 — 更新 AI 配置文件（可选）
<行号>:### Step 9 — 更新 lock 文件并汇报
```

- [ ] **Step 2.4：提交**

```bash
git add skills/harness/git-workflow-init/SKILL.md
git commit -m "feat: add Step 6.5 acceptance testing to git-workflow-init

在 Step 6（hooks 部署）之后、Step 7（文档渲染）之前插入验收测试步骤。
先询问用户是否运行，若同意则在真实 repo 中调用已安装的 hook 脚本，
验证 pre-commit/commit-msg/pre-push/post-checkout 的实际拦截行为，
结束后清理所有临时文件和临时分支。"
```

---

## Task 3：真实跑一遍验收场景（end-to-end 验证）

> 在当前项目（`harveyz-skill` repo）本身跑一遍，验证 Step 6.5 的行为与 eval 用例 11 一致。

**Files:**（无文件变更，仅验证行为）

- [ ] **Step 3.1：确认当前 repo 的 hooks 已部署**

```bash
ls .githooks/
git config core.hooksPath
```

期望 `.githooks/` 下存在 `pre-commit`、`commit-msg` 等文件，`core.hooksPath` 返回 `.githooks`。

- [ ] **Step 3.2：手动执行 pre-commit 验收场景**

（模拟 Step 6.5 的 pre-commit 测试——当前在 `feature/git-workflow-init-acceptance` 分支，切换到 staging 触发保护规则）

```bash
git checkout staging 2>/dev/null
output=$(sh .githooks/pre-commit 2>&1); echo "exit: $?"; echo "output: $output"
git checkout feature/git-workflow-init-acceptance
```

期望：`exit: 1`，output 包含 `❌ 禁止直接在 staging 上提交`

- [ ] **Step 3.3：手动执行 commit-msg 验收场景**

```bash
TS=$(date +%s)
echo "bad commit" > /tmp/gwi-test-msg-${TS}.txt
sh .githooks/commit-msg /tmp/gwi-test-msg-${TS}.txt 2>&1; echo "exit: $?"
rm -f /tmp/gwi-test-msg-${TS}.txt
```

期望：`exit: 1`，输出包含提交格式错误提示

- [ ] **Step 3.4：确认无临时残留**

```bash
ls /tmp/gwi-test-msg-* 2>&1
git branch | grep gwi-test-INVALID-NAME
```

期望：两条命令均无匹配输出（无残留）

- [ ] **Step 3.5：提交验证记录**

```bash
git add -A
git commit -m "docs: verify acceptance testing end-to-end in harveyz-skill repo" --allow-empty
```

> 注意：若无文件变动，用 `--allow-empty` 记录验证通过的节点；或跳过此步骤直接进入 Task 4。

---

## Task 4：清理验证痕迹并合并

- [ ] **Step 4.1：删除 end-to-end 验证产生的空 commit（若存在）**

若 Task 3 Step 3.5 产生了空 commit，用以下命令撤销：

```bash
git log --oneline -3
# 若最新 commit 是空的验证记录 commit，执行：
git reset --soft HEAD~1
```

- [ ] **Step 4.2：确认分支干净**

```bash
git status
git log --oneline -5
```

期望：工作区干净，提交历史包含 eval 用例提交和 Step 6.5 实现提交。

- [ ] **Step 4.3：运行项目测试，确保 SKILL.md 格式校验通过**

```bash
npm test
```

期望：测试全部通过（包括 SKILL.md 格式校验）。

- [ ] **Step 4.4：最终提交并推送**

```bash
git push origin feature/git-workflow-init-acceptance
```
