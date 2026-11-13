# 验收测试场景

Step 6.5 用户选 Y 后读取此文件，按顺序执行各 hook 的验收场景。

---

## 初始化

```bash
ORIGINAL_REF=$(git symbolic-ref -q HEAD)
TIMESTAMP=$(date +%s)

restore_head() {
    git symbolic-ref HEAD "$ORIGINAL_REF" || echo "❌ HEAD 未能恢复，请手动执行：git symbolic-ref HEAD $ORIGINAL_REF"
}
```

`ORIGINAL_REF` 为空（detached HEAD）时不运行验收，告诉用户先切到命名分支。

需要"站在某个分支上"的场景只用 `git symbolic-ref HEAD refs/heads/<分支>` 临时改 HEAD 指向，跑完立刻 `restore_head`：hooks 只读当前分支名，这样不切换文件、不新建分支，在还没有提交的仓库里也能用（切换分支在那里会失败）。恢复失败要报出来，不要用 `2>/dev/null` 吞掉。

---

## 各 hook 验收场景

仅对 Step 6 实际生成的 hook 执行对应场景；未生成的跳过，不报告。

### pre-commit（仅当 `branches.protected` 非空）

取配置 `branches.protected` 第一个 `name` 字段作为 `PROTECTED_BRANCH`。

```bash
git symbolic-ref HEAD "refs/heads/$PROTECTED_BRANCH"
output=$(sh .githooks/pre-commit 2>&1)
exit_code=$?
restore_head
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

`pre-push/force-push` 块用 `git merge-base --is-ancestor` 判断非 fast-forward，因此必须用真实存在于仓库历史中的两个 commit 来构造"远端不是本地祖先"的场景，不能用假造的 SHA 字符串（假 SHA 在真实仓库里既不是祖先也不是非祖先，`git merge-base` 会因对象不存在报错，不代表 force push 语义）。用当前 `HEAD` 作为 remote_sha、`HEAD~1` 作为 local_sha：remote（较新）不是 local（较旧）的祖先，等价于历史被回退重写。仓库只有一个提交（无 `HEAD~1`）时跳过此场景。

```bash
if git rev-parse -q --verify HEAD~1 >/dev/null 2>&1; then
    REMOTE_SHA=$(git rev-parse HEAD)
    LOCAL_SHA=$(git rev-parse HEAD~1)
    output=$(printf "refs/heads/%s %s refs/heads/%s %s\n" \
        "$PROTECTED_PUSH_BRANCH" "$LOCAL_SHA" "$PROTECTED_PUSH_BRANCH" "$REMOTE_SHA" \
        | sh .githooks/pre-push 2>&1)
    exit_code=$?
    SKIPPED=0
else
    SKIPPED=1
fi
```

**期望：** 仓库提交数 ≥ 2 时 `exit_code = 1`；仅有一个提交时标记为 SKIP，不计入 PASS/FAIL。

---

### pre-push — tag（仅当 `tags.enforce: true`）

```bash
output=$(printf "refs/tags/invalid-tag-format abc1234 refs/tags/invalid-tag-format 0000000000000000000000000000000000000000\n" \
    | sh .githooks/pre-push 2>&1)
exit_code=$?
```

**期望：** `exit_code = 1`（`tags.push_guard: false` 时为 0，output 含 `⚠️`）。

---

### pre-push — 轻量 tag（仅当 `tags.enforce: true` 且 `tags.require_annotated: true`）

`VALID_TAG` 取一个符合 `tags.allowed_patterns` 的名字（默认配置用 `v0.0.0`）。用当前提交冒充轻量 tag 推送（轻量 tag 推送时 `local_sha` 就是提交），不真正建 tag。仓库还没有提交时跳过此场景。

```bash
if git rev-parse -q --verify HEAD >/dev/null 2>&1; then
    output=$(printf "refs/tags/%s %s refs/tags/%s 0000000000000000000000000000000000000000\n" \
        "$VALID_TAG" "$(git rev-parse HEAD)" "$VALID_TAG" | sh .githooks/pre-push 2>&1)
    exit_code=$?
    SKIPPED=0
else
    SKIPPED=1
fi
```

**期望：** `exit_code = 1`，output 含 `git tag -a`（`tags.push_guard: false` 时为 0，output 含 `⚠️`）；没有提交时标记为 SKIP。

---

### post-checkout（仅当 `branch_naming.enforce: true`）

前缀 `gwi-test-INVALID-NAME-` 不匹配任何常见命名规范。

```bash
git symbolic-ref HEAD "refs/heads/gwi-test-INVALID-NAME-${TIMESTAMP}"
output=$(sh .githooks/post-checkout HEAD HEAD 1 2>&1)
restore_head
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
pre-push      轻量 tag 推送（应拒绝）                  PASS ✅
post-checkout 不合规分支名（应有 ⚠️ 警告）             PASS ✅
──────────────────────────────────────────────────────
✅ 全部通过（N/N，SKIP 不计入分母）。继续 Step 7...
```

若 force push 场景因仓库只有一个提交被跳过，对应行显示：

```
pre-push      force push 到 <branch>（应拒绝）         SKIP ⏭️（仓库提交数 < 2，无法构造历史）
```

轻量 tag 场景因仓库还没有提交被跳过时同样显示 `SKIP ⏭️（仓库还没有提交）`。

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

用户选 **N** → 提示重新检查配置后重跑 `/init-workflow`，停止。
用户选 **Y** → 继续 Step 7。
