---
migrated: 2026-05-29
docs:
  - reference/testing-guide.md  # 验收测试模式（通用模式）
implemented_in: skills/harness/git-workflow-init/references/acceptance-test.md  # Step 6.5
---

# git-workflow-init 验收测试设计

> 设计日期：2026-05-25
> 目标 skill：`skills/harness/git-workflow-init`（v4.0.0）
> 状态：已实现（Step 6.5）

---

## 背景与问题

当前 `git-workflow-init` skill 在 Step 6 完成 hooks 部署后即进入文档渲染，没有任何机制验证 hooks 是否真正按预期拦截提交/推送行为。部署完成不等于运行正确——`core.hooksPath` 配置错误、脚本语法问题、权限缺失等问题均无法被发现。

## 目标

在 Step 6 之后、Step 7 之前新增 **Step 6.5 — 验收测试**，通过在真实项目 repo 中直接调用 hook 脚本，验证 hooks 的实际拦截行为，不通过则不继续后续步骤。

## 核心设计原则

**测试必须在真实 repo 中就地运行。** 在临时 repo 里测试只能证明脚本本身能运行，无法证明当前项目的 `core.hooksPath` 配置是否生效。所有测试在当前项目 repo 的 git context 中直接调用 hook 脚本，`git symbolic-ref`、`git rev-parse` 等命令返回真实值。

## Step 6.5 详细设计

### 触发条件

Step 6 hooks 部署完成后，向用户询问：

```
✅ Hooks 已部署完毕。是否运行验收测试？（在当前 repo 中验证 hooks 实际拦截行为）[y/N]
```

- 用户选 **N**：跳过，直接进入 Step 7。
- 用户选 **Y**：执行以下验收流程。

### 验收场景

对每个实际安装的 hook，运行对应负向（应拒绝）场景。测试通过 = hook 以预期方式拒绝了不合规操作。

#### pre-commit 验收

**前提：** `branches.protected` 非空时生成了 pre-commit hook。

**场景：直接提交到受保护分支应被拦截。**

```bash
# 1. 记录当前分支
ORIGINAL_BRANCH=$(git symbolic-ref --short HEAD)

# 2. 若当前不在受保护分支，临时切换（取配置中第一个保护分支）
PROTECTED_BRANCH=<first protected branch from config>
if [ "$ORIGINAL_BRANCH" != "$PROTECTED_BRANCH" ]; then
  git checkout "$PROTECTED_BRANCH" 2>/dev/null || git checkout -b "$PROTECTED_BRANCH" 2>/dev/null
fi

# 3. 直接调用 hook 脚本（不产生实际 commit）
output=$(sh .githooks/pre-commit 2>&1)
exit_code=$?

# 4. 还原分支
[ "$ORIGINAL_BRANCH" != "$PROTECTED_BRANCH" ] && git checkout "$ORIGINAL_BRANCH"

# 5. 判断：期望 exit_code = 1
```

#### commit-msg 验收

**前提：** `commit_message.enforce: true` 时生成了 commit-msg hook。

**场景：格式违规的提交信息应被拦截。**

```bash
# 构造违规消息（根据 format 类型：conventional 用 "bad commit"，regex 用不匹配 pattern 的字符串）
echo "bad commit" > /tmp/gwi-test-msg-$$.txt
output=$(sh .githooks/commit-msg /tmp/gwi-test-msg-$$.txt 2>&1)
exit_code=$?
rm -f /tmp/gwi-test-msg-$$.txt

# 期望 exit_code = 1
```

#### pre-push 验收

**前提：** `push_rules.enforce: true` 时生成了 pre-push hook 的 force-push 块。

**场景：force push（本地 sha 全零）到受保护分支应被拦截。**

```bash
PROTECTED_BRANCH=<first branch from push_rules.block_force_push>
output=$(echo "refs/heads/${PROTECTED_BRANCH} abc1234 refs/heads/${PROTECTED_BRANCH} 0000000000000000000000000000000000000000" \
  | sh .githooks/pre-push 2>&1)
exit_code=$?

# 期望 exit_code = 1
```

**前提：** `tags.enforce: true` 时生成了 pre-push hook 的 tags 块。

**场景：不符合规范的 tag 推送应被拦截。**

```bash
output=$(echo "refs/tags/invalid-tag-format abc1234 refs/tags/invalid-tag-format 0000000000000000000000000000000000000000" \
  | sh .githooks/pre-push 2>&1)
exit_code=$?

# 期望 exit_code = 1
```

#### post-checkout 验收

**前提：** `branch_naming.enforce: true` 时生成了 post-checkout hook。

**场景：切换到不合规分支名应触发警告。**

```bash
TS=$(date +%s)
TEST_BRANCH="gwi-test-INVALID-NAME-${TS}"

# 创建临时非规范分支
git checkout -b "$TEST_BRANCH" 2>/dev/null

# 直接调用 hook（参数：prev_sha new_sha is_branch_checkout=1）
output=$(sh .githooks/post-checkout HEAD HEAD 1 2>&1)

# 还原并删除临时分支
git checkout "$ORIGINAL_BRANCH"
git branch -D "$TEST_BRANCH"

# 期望：output 包含 ⚠️
```

### 结果展示

```
验收测试结果：
──────────────────────────────────────────────────────
pre-commit   直接提交到 main（应拒绝）                PASS ✅
commit-msg   格式违规消息（应拒绝）                    PASS ✅
pre-push     force push 到 main（应拒绝）              PASS ✅
post-checkout 不合规分支名（应有 ⚠️ 警告）             PASS ✅
──────────────────────────────────────────────────────
✅ 全部通过（4/4）。继续 Step 7...
```

失败时：

```
──────────────────────────────────────────────────────
pre-commit   直接提交到 main（应拒绝）                FAIL ❌
  期望 exit 1，实际 exit 0
  输出：（空）
──────────────────────────────────────────────────────
❌ 验收未通过（1/4 失败）。
   可能原因：core.hooksPath 未正确配置，或 hook 脚本语法错误。
   是否继续执行后续步骤（Step 7 文档渲染）？[y/N]
```

### 清理保证

无论测试通过与否：
- 临时文件（`/tmp/gwi-test-msg-$$.txt`）执行后立即删除
- 临时分支（`gwi-test-INVALID-NAME-*`）切换回原分支后立即 `git branch -D`
- 不产生任何 commit，不修改任何 git 历史

## 实现位置

修改 `skills/harness/git-workflow-init/SKILL.md`：在 Step 6 与 Step 7 之间插入 Step 6.5。

新内容约 80-100 行，插入位置：Step 6 结尾（`git config merge.ff false` 之后）与 Step 7 开头之间。

## 不在此次范围内

- Positive 场景（合规操作放行）测试：当前只做 negative，保持实现简洁
- 自动修复 hooks：验收失败时只报告，不自动重新部署
- evals.json 新增验收用例：可后续补充

## 成功标准

1. Step 6 完成后出现验收询问
2. 用户选 Y 后，hook 脚本在真实 repo 中被调用并按预期拦截
3. 结果表格清晰展示每个 hook 的通过状态
4. 测试结束后无任何残留（临时文件、临时分支均已清理）
5. 全通过时正常进入 Step 7；有失败时询问用户是否继续
