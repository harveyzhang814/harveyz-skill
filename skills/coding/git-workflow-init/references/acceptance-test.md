# 验收测试场景

Step 6.5 用户选 Y 后读取此文件，按顺序执行各 hook 的验收场景。

---

## 初始化

```bash
ORIGINAL_BRANCH=$(git symbolic-ref --short HEAD)
TIMESTAMP=$(date +%s)
```

---

## 各 hook 验收场景

仅对 Step 6 实际生成的 hook 执行对应场景；未生成的跳过，不报告。

### pre-commit（仅当 `branches.protected` 非空）

取配置 `branches.protected` 第一个 `name` 字段作为 `PROTECTED_BRANCH`。

```bash
SWITCHED=0
if [ "$(git symbolic-ref --short HEAD 2>/dev/null)" != "$PROTECTED_BRANCH" ]; then
    git checkout "$PROTECTED_BRANCH" 2>/dev/null \
        || git checkout -b "$PROTECTED_BRANCH" 2>/dev/null
    SWITCHED=1
fi

output=$(sh .githooks/pre-commit 2>&1)
exit_code=$?

[ "$SWITCHED" = "1" ] && git checkout "$ORIGINAL_BRANCH" 2>/dev/null
```

**期望：** `exit_code = 1`，output 含拒绝提示。

---

### commit-msg（仅当 `commit_message.enforce: true`）

违规消息构造规则：
- `format: conventional` → `"bad commit"`
- `format: regex` → `"NOMATCH: this should fail"`

```bash
echo "bad commit" > /tmp/gwi-test-msg-${TIMESTAMP}.txt
output=$(sh .githooks/commit-msg /tmp/gwi-test-msg-${TIMESTAMP}.txt 2>&1)
exit_code=$?
rm -f /tmp/gwi-test-msg-${TIMESTAMP}.txt
```

**期望：** `exit_code = 1`。

---

### pre-push — force push（仅当 `push_rules.enforce: true`）

取 `push_rules.block_force_push` 第一个分支名作为 `PROTECTED_PUSH_BRANCH`。

```bash
output=$(printf "refs/heads/%s abc1234 refs/heads/%s 0000000000000000000000000000000000000000\n" \
    "$PROTECTED_PUSH_BRANCH" "$PROTECTED_PUSH_BRANCH" \
    | sh .githooks/pre-push 2>&1)
exit_code=$?
```

**期望：** `exit_code = 1`。

---

### pre-push — tag（仅当 `tags.enforce: true`）

```bash
output=$(printf "refs/tags/invalid-tag-format abc1234 refs/tags/invalid-tag-format 0000000000000000000000000000000000000000\n" \
    | sh .githooks/pre-push 2>&1)
exit_code=$?
```

**期望：** `exit_code = 1`。

---

### post-checkout（仅当 `branch_naming.enforce: true`）

前缀 `gwi-test-INVALID-NAME-` 不匹配任何常见命名规范。

```bash
TEST_BRANCH="gwi-test-INVALID-NAME-${TIMESTAMP}"
git checkout -b "$TEST_BRANCH" 2>/dev/null

output=$(sh .githooks/post-checkout HEAD HEAD 1 2>&1)

git checkout "$ORIGINAL_BRANCH" 2>/dev/null
git branch -D "$TEST_BRANCH" 2>/dev/null
```

**期望：** output 含 `⚠️` 警告（此 hook 不阻断，exit 0 正常）。

---

## 结果展示

收集所有场景结果后用表格输出：

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

用户选 **N** → 提示重新检查配置后重跑 `/git-workflow-init`，停止。
用户选 **Y** → 继续 Step 7。
