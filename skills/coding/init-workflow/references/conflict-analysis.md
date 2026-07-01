# 冲突分析实现细节

Step 4（4a–4d）的具体实现方法，Step 5 冲突类型的完整定义。

---

## 4a. Lock 文件 diff — 配置变更摘要

对比 `.githooks/.workflow-config.lock.yml` 与当前 `workflow-config.yml`，生成如下格式的变更摘要：

```
配置变更摘要：
+ branches.protected 新增: develop（merge_from: feature/*）
~ commit_message.conventional.types 修改: 新增 wip，移除 perf
- tags.allowed_patterns 删除: ^v[0-9]+\.[0-9]+\.[0-9]+-rc\.[0-9]+$
```

### YAML 分支名提取（重要）

不要用宽泛的 `grep "name:"` 提取分支名——YAML 多个层级都可能含有 `name:` 字段，会导致误匹配。用 `python3` 精确解析：

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

---

## 4b. MANAGED 块 hash 校验

### MANAGED 块格式

```sh
# --- BEGIN MANAGED: <block-id> (hash:<8位hex>) ---
<generated content>
# --- END MANAGED: <block-id> ---
```

### Hash 计算

```bash
actual_hash=$(printf '%s' "<block_content>" | git hash-object --stdin | cut -c1-8)
```

`<block_content>` = BEGIN/END 标记之间的内容，去首尾空白。

若 `actual_hash` 与标记里记录的 hash 不一致 → 用户手改了此块，记录为类型 C 冲突：

```
[手改冲突] .githooks/pre-commit 的 MANAGED 块 branches.protected/main 被手动修改
  原始生成内容 hash: a3f9c2b1
  当前内容 hash:     d7e42f0c
  差异：（展示 diff）
```

---

## 4c. 外部代码扫描 — 用户手写区

提取每个 hook 文件中 MANAGED 块之外的所有代码，识别以下引用：

| 提取目标 | 扫描方式 |
|---------|---------|
| 分支名 | `"$BRANCH" = "name"`、`case "name"`、`branch = "name"` |
| 提交类型 | `grep -qE "...(type\|...)"`、字符串字面量 `wip`、`hotfix` |
| Tag/分支 pattern | `grep -qE "pattern"` |
| 外部脚本调用 | `./`、`bash `、`sh `、`npm run`、`make ` 开头的行 |

---

## 4d. 冲突类型定义

综合 4a/4b/4c 结果，识别以下四种冲突：

**类型 A：条件重叠**（阻断）
- 用户代码处理了分支/规则 X，新配置也将 X 加入受管范围
- 两段代码同时执行，可能产生矛盾行为
- 选项：A) 保留用户代码跳过生成 / B) 用新配置覆盖并删除重复代码 / C) 两者都保留

**类型 B：引用断裂**（阻断）
- 用户代码引用了配置中已删除的内容（如类型 `wip`）
- 用户代码逻辑失去对应的配置支撑
- 选项：A) 保留用户代码 / B) 删除用户代码中的对应引用

**类型 C：手改冲突**（阻断）
- MANAGED 块被手动修改，重新生成会覆盖用户修改
- 选项：A) 保留用户修改（跳过此块） / B) 用新配置覆盖

**类型 D：新增重叠**（信息提示，非阻断）
- 用户已手写了对新增内容的处理，新配置也打算生成同名 MANAGED 块
- 不一定冲突，但值得确认
- 展示后询问用户是否继续（无需强制决策）

---

## Step 5 冲突呈现格式

将所有冲突一次性列出，每条附带选项，用户逐条决策：

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

其他冲突类型按同样格式呈现，选项见上方类型定义。

---

## 类型 E — git config 漂移

**触发条件：** `core.hooksPath` 或 `merge.ff` 与期望值不符，或在本地 git config 中缺失。

**严重程度：** 高（hooks 已部署但完全失效）

**检测方式（Step 4e）：**

```bash
git config --local core.hooksPath   # 期望：.githooks
git config --local merge.ff         # 期望：false
```

判定规则：
- 值正确 → 无问题
- 值存在但不正确 → 类型 E 冲突（配置漂移）
- 值缺失（命令返回空 / exit 1） → 类型 E 冲突（配置丢失）

lock 文件含 `git_config` 节时，优先与 lock 中记录的值对比；lock 缺失该节时直接检测实际值。

**Step 5 呈现格式（每项独立列出，最多两条）：**

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

**默认选项：A（自动修复）。**

**Step 6 修复执行时机：** 写入 hooks 后，对用户选择 A 的每一条类型 E 冲突立即执行对应的 `git config` 命令，无需用户手动操作。

**用户选 B（跳过）时：** Step 9 对应行显示 `❌ 未修复`，并附注"hooks 当前不生效"。
