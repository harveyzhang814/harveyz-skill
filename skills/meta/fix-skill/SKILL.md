---
name: fix-skill
version: "2.0.0"
description: "Diagnose and fix errors in any skill file autonomously. Called automatically by other skills on failure. Attempts up to 3 rounds of AI-driven diagnosis and repair, accumulating context across rounds. Writes a fix session document in real time. On success, notifies caller to auto-retry. On all-round failure, restores the original file and preserves the full diagnosis record."
user_invocable: false
---

# fix-skill

## 输入上下文

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill` | 是 | 调用方 skill 名称 |
| `skill_dir` | 是 | 调用方 skill 绝对路径 |
| `file` | 是 | 出错文件绝对路径（任意类型） |
| `error` | 是 | stderr 原文 + returncode |
| `call_args` | 否 | 验证时重跑脚本所需参数；无则做内容自洽检查 |

---

## 数据目录

```
~/.hskill/fix-skill/
└── <skill>/
    ├── backups/    # 暂存，session 结束自动清空
    └── *.md        # fix session 文档（永久保留）
```

---

## Step 1：备份 + 创建 fix session 文档

通过 `date +%Y%m%dT%H%M%S` 获取当前时间戳，记为 `ts`（后续所有路径均使用此值，不再重新获取）。

从 `skill_dir/SKILL.md` frontmatter 读取调用方 skill 的当前版本号，记为 `skill_version`。

将 `file` 备份到 `~/.hskill/fix-skill/<skill>/backups/<文件名>.<ts>.bak`，记录为 `backup_path`。

读取 `references/fix-record-template.md`，创建 fix session 文档：

路径：`~/.hskill/fix-skill/<skill>/<ts>--<文件名>.md`

写入 header 部分（frontmatter 含 `skill_version` + 原始错误），`file` 字段写入 `file` 的绝对路径，`status` 初始为 `in_progress`。

---

## Step 2：尝试修复（最多 3 轮）

**每轮开始前：** 读取 fix session 文档，了解前几轮的假设与失败原因。

**每轮执行：**

**① 诊断**
提出新假设（必须与前几轮不同，明确说明为何）。
若判定为 external（根因在 `file` 之外，修改文件无法解决）→ 立即跳至 Step 3b，不消耗轮次。

**② 修复**
对 `file` 做最小化改动，只修复已定位的根因。
禁止：用异常捕获吞掉错误、添加 fallback 绕过问题、修改与根因无关的代码。

**③ 验证**
有 `call_args` → 在真实环境中重跑脚本，returncode 为 0 则通过。
无 `call_args` → 检查改动内容是否语义完整、逻辑自洽。

**④ 立即 append 本轮结果到 fix session 文档**（无论成败，格式见 template）

成功 → Step 3a
失败 → 将 `file` 还原为 `backup_path`（回到干净基线），进入下一轮

3 轮全失败 → Step 3b

---

## Step 3a：成功

**最终状态校验：** 确认 `file` 可读、内容与本轮修复一致。
校验失败 → 降级至 Step 3b。

在 fix session 文档末尾 append：
- frontmatter `status` 更新为 `success`
- 「最终结果：成功（第 N 轮）」

删除 `backup_path`。

输出：
```
FIX_RESULT: AUTO_RETRY
SESSION_PATH: <fix session 文档绝对路径>
ATTEMPTS: <N>
```

---

## Step 3b：失败

将 `backup_path` 内容写回 `file`（还原）。

**最终状态校验：** 逐字节确认 `file` 与 `backup_path` 完全一致。
- 一致 → 删除 `backup_path`
- 不一致 → 保留 `backup_path`，在 session 文档标注「还原异常，backup 已保留」，输出 `FIX_RESULT: FAILURE+RESTORE_FAILED`

在 fix session 文档末尾 append：
- frontmatter `status` 更新为 `failure`
- 「最终结果：失败，已回滚」

输出：
```
FIX_RESULT: FAILURE
SESSION_PATH: <fix session 文档绝对路径>
ATTEMPTS: <N>
```

---

## 调用方响应约定

| FIX_RESULT | 行为 |
|------------|------|
| `AUTO_RETRY` | 重试原失败步骤（仅一次）；通知用户「已自动修复，共 N 轮，记录见 SESSION_PATH」 |
| `FAILURE` | 报告原始错误 + 「已尝试 3 轮均失败，已回滚，记录见 SESSION_PATH」 |
| `FAILURE+RESTORE_FAILED` | 立即告警：「修复失败且还原异常，file 状态不可知，backup 保留，请手动处理，记录见 SESSION_PATH」 |
