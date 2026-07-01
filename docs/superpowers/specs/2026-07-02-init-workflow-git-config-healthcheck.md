---
migrated: 2026-07-02
implemented_in:
  - skills/coding/init-workflow/SKILL.md  # Step 4e git config 健康检查、Step 9 汇报表新增两行、v4.1.1
---

# init-workflow skill — git config 健康检查 设计规格

**日期：** 2026-07-02  
**背景：** M3 开发期间，`.githooks/` 已正确部署但 `core.hooksPath` 未配置，导致 staging 分支保护全程失效，十余次直接提交均未被拦截。

---

## 问题根因

`core.hooksPath` 和 `merge.ff` 是**本地 git config**（写入 `.git/config`，不进版本库）。

```
skill 首次运行 → 设置 core.hooksPath = .githooks ✅
git clone / .git 目录重建 → 配置丢失 ❌
skill 重新运行 → Step 4 只对比 lock vs workflow-config，不检测 git config 是否仍然有效
                → 看起来"一切正常"，实则保护已失效
```

**M3 的具体情况：** skill 只运行了一次，此后 `core.hooksPath` 在开发过程中悄悄丢失，用户未再运行 skill，因此 Step 4 的盲区从未触发——config 丢失从头到尾都没有被检测到。

两道防线分别对应两个场景：

| 场景 | 防线 |
|------|------|
| skill 运行一次后 config 丢失，不再重新运行 | CLAUDE.md 克隆提示（手动执行两条命令） |
| skill 重新运行时 config 已丢失 | Step 4e 健康检查（本 spec 的修复目标） |

---

## 变更范围

涉及 skill 的三个文件：

| 文件 | 变更类型 |
|------|---------|
| `SKILL.md` | Step 4 新增 4e 小节；Step 9 汇报表新增两行 |
| `references/conflict-analysis.md` | 新增类型 E（git config 漂移）定义 |
| `references/lock-file-format.md` | lock 文件新增 `git_config` 节 |

---

## 一、SKILL.md 变更

### Step 4 新增 4e — git config 健康检查

在现有 4a–4d 之后追加：

```
#### 4e. git config 健康检查

检查以下两项本地 git config：

```bash
git config --local core.hooksPath   # 期望：.githooks
git config --local merge.ff         # 期望：false
```

判定规则：
- 值正确 → 无问题
- 值存在但不正确 → 类型 E 冲突（配置漂移）
- 值缺失 → 类型 E 冲突（配置丢失）

类型 E 冲突在 Step 5 列出（附期望值 vs 实际值），默认选项为"自动修复"。
Step 6 写入 hooks 后立即执行修复命令，无需用户手动操作。
```

### Step 9 汇报表：更新 core.hooksPath 行 + 追加 merge.ff 行

现有汇报表中已有 `core.hooksPath = .githooks` 一行（无状态指示符）。
本次变更将该行替换为带 ✅/❌ 的健康检查结果，并在其后追加 `merge.ff` 行：

```
core.hooksPath               = .githooks   ✅（或 ❌ 已修复）
merge.ff                     = false        ✅（或 ❌ 已修复）
```

---

## 二、references/conflict-analysis.md 变更

在现有四种冲突类型（A/B/C/D）之后新增：

### 类型 E — git config 漂移

**触发条件：** `core.hooksPath` 或 `merge.ff` 与期望值不符，或缺失。

**严重程度：** 高（hooks 已部署但完全失效）

**Step 5 呈现格式：**

```
─────────────────────────────────────────────────────────
[N/M] git config 漂移（类型 E）
问题：core.hooksPath 未配置，.githooks/ 中的 hooks 不会被 git 加载
期望：core.hooksPath = .githooks
实际：（未设置）
影响：所有分支保护、提交信息校验、push 限制均失效

选项：
  A) 自动修复（推荐）：运行 git config core.hooksPath .githooks
  B) 跳过（保持当前状态，hooks 继续失效）
─────────────────────────────────────────────────────────
```

**默认选项：A（自动修复）**，无需用户额外操作。

---

## 三、references/lock-file-format.md 变更

lock 文件新增 `git_config` 节，记录上次 skill 运行后的配置状态，供 4e 对比：

```yaml
# 在现有字段末尾追加：
git_config:
  core_hooks_path: ".githooks"   # 上次运行时设置的值
  merge_ff: "false"              # 上次运行时设置的值
```

4e 健康检查逻辑：
1. 读 lock 文件中的 `git_config` 节（不存在则视为首次含此节的运行，跳过对比，直接检测当前值）
2. 执行 `git config --local` 读取实际值
3. 实际值 ≠ lock 中记录值，或实际值缺失 → 类型 E 冲突

---

## 验收标准

| 场景 | 期望行为 |
|------|---------|
| skill 首次运行 | 设置 `core.hooksPath`，lock 文件记录 `git_config` 节 |
| skill 重新运行，config 正常 | 4e 检查通过，Step 9 显示 ✅ |
| skill 重新运行，config 丢失 | Step 5 呈现类型 E 冲突，用户选 A → 自动修复，Step 9 显示 ❌ 已修复 |
| 用户选 B（跳过） | Step 9 显示 ❌ 未修复，附警告"hooks 当前不生效" |
| `merge.ff` 缺失（单独） | 同上，独立作为一条类型 E 列出 |

---

## 不在本次范围

- 自动在 `CLAUDE.md` 追加克隆提示（现由 Step 8 可选处理，不强制）
- 检测 `.git/hooks/` 中是否存在同名 hook 造成的覆盖（极少见，留后续）
