# init-workflow git config 健康检查 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 init-workflow skill 重新运行时，检测 `core.hooksPath` 和 `merge.ff` 是否仍然有效，丢失时作为类型 E 冲突呈现并自动修复。

**Architecture:** 三文件串联修改——lock-file-format 新增 `git_config` 节（数据结构），conflict-analysis 新增类型 E 定义（检测逻辑），SKILL.md 新增 Step 4e（触发入口）并更新 Step 9（状态汇报）。三个文件互相引用，需按依赖顺序修改。

**Tech Stack:** Markdown（SKILL.md / references/*.md）；无可执行代码，验证方式为 `npm test`（格式校验）+ 规格对照检查。

## Global Constraints

- 文件路径前缀：`skills/coding/init-workflow/`
- 所有修改只追加/替换指定内容，不修改任何无关段落
- `npm test` 必须在每个 task 后通过

---

### Task 1: lock-file-format.md — 新增 git_config 节

**Files:**
- Modify: `skills/coding/init-workflow/references/lock-file-format.md`（在末尾追加 git_config 节）

**Interfaces:**
- Produces: lock 文件 YAML schema 中 `git_config` 节，供 Task 3 Step 4e 引用

- [ ] **Step 1: 阅读文件，确认当前末尾内容**

  当前末尾（第 30-34 行）：
  ```yaml
    block_force_push: [main, staging]
  ```
  最后一行为 `block_force_push`，文件末尾有一行注释说明"只记录影响 hook 生成的字段"。

- [ ] **Step 2: 在文件末尾追加 git_config 节**

  在 `skills/coding/init-workflow/references/lock-file-format.md` 的最后一行（"只记录影响 hook 生成的字段"注释）之后追加：

  ```markdown
  
  以及本次运行后的 git 本地配置状态：
  
  ```yaml
  git_config:
    core_hooks_path: ".githooks"   # 上次运行时设置的值
    merge_ff: "false"              # 上次运行时设置的值
  ```
  
  **4e 读取逻辑：** lock 文件缺少 `git_config` 节时视为首次含此节的运行，跳过与 lock 的对比，直接检测当前实际值；若实际值不符或缺失，仍报类型 E 冲突。
  ```

- [ ] **Step 3: 运行 npm test 验证格式**

  ```bash
  cd /Users/harveyzhang96/Projects/harveyz-skill && npm test
  ```
  预期：全部 pass，无 SKILL.md 格式错误。

- [ ] **Step 4: Commit**

  ```bash
  git add skills/coding/init-workflow/references/lock-file-format.md
  git commit -m "feat(init-workflow): lock 文件新增 git_config 节"
  ```

---

### Task 2: conflict-analysis.md — 新增类型 E 定义

**Files:**
- Modify: `skills/coding/init-workflow/references/conflict-analysis.md`（在类型 D 之后追加类型 E）

**Interfaces:**
- Consumes: lock-file-format.md 中 `git_config` 节（Task 1 Produces）
- Produces: 类型 E 完整定义（触发条件、呈现格式、默认选项），供 Task 3 SKILL.md 中 4d/4e/Step5 引用

- [ ] **Step 1: 确认当前末尾内容**

  conflict-analysis.md 末尾（第 124-127 行）：
  ```markdown
  其他冲突类型按同样格式呈现，选项见上方类型定义。
  ```

- [ ] **Step 2: 在文件末尾追加类型 E 定义**

  在 conflict-analysis.md 最后一行之后追加：

  ````markdown
  
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
  ````

- [ ] **Step 3: 运行 npm test**

  ```bash
  cd /Users/harveyzhang96/Projects/harveyz-skill && npm test
  ```
  预期：pass。

- [ ] **Step 4: Commit**

  ```bash
  git add skills/coding/init-workflow/references/conflict-analysis.md
  git commit -m "feat(init-workflow): conflict-analysis 新增类型 E（git config 漂移）"
  ```

---

### Task 3: SKILL.md — Step 4e + Step 9 + 参考文件表更新

**Files:**
- Modify: `skills/coding/init-workflow/SKILL.md`
  - 在 Step 4d 之后插入 4e 小节
  - 替换 Step 9 汇报表中 `core.hooksPath` 行，并追加 `merge.ff` 行
  - 更新参考文件表中 conflict-analysis.md 的说明列

**Interfaces:**
- Consumes:
  - `references/conflict-analysis.md` 类型 E 定义（Task 2 Produces）
  - `references/lock-file-format.md` `git_config` 节（Task 1 Produces）

- [ ] **Step 1: 在 Step 4d 之后插入 4e 小节**

  定位 SKILL.md 中的精确插入点（第 82-83 行）：
  ```
  #### 4d. 冲突检测
  综合 4a/4b/4c，识别四种冲突类型（A 条件重叠、B 引用断裂、C 手改冲突、D 新增重叠）。类型定义与选项见 `references/conflict-analysis.md`。
  ```

  在这段之后、`---`（Step 5 的分隔线）之前插入：

  ```markdown
  
  #### 4e. git config 健康检查
  
  检查以下两项本地 git config：
  
  ```bash
  git config --local core.hooksPath   # 期望：.githooks
  git config --local merge.ff         # 期望：false
  ```
  
  1. 读取 lock 文件的 `git_config` 节（不存在则跳过对比，直接检测实际值）
  2. 执行上述命令，获取实际值
  3. 实际值与期望不符，或实际值缺失 → 类型 E 冲突
  
  类型 E 冲突在 Step 5 列出（附期望值 vs 实际值），默认选项为"自动修复（A）"。Step 6 写入 hooks 后立即执行修复命令。类型 E 完整定义见 `references/conflict-analysis.md`。
  ```

- [ ] **Step 2: 替换 Step 9 汇报表中 core.hooksPath 行 + 追加 merge.ff 行**

  定位第 215 行：
  ```
  core.hooksPath                     = .githooks
  ```

  替换为（两行）：
  ```
  core.hooksPath               = .githooks   ✅（或 ❌ 已修复 / ❌ 未修复）
  merge.ff                     = false        ✅（或 ❌ 已修复 / ❌ 未修复）
  ```

- [ ] **Step 3: 更新参考文件表中 conflict-analysis.md 的说明**

  定位文件末尾参考文件表（约第 234 行）：
  ```
  | `references/conflict-analysis.md` | 4a–4d 实现脚本、冲突类型 A/B/C/D 完整定义与选项、Step 5 呈现格式 | Step 4/5：执行分析前读取 |
  ```

  替换为：
  ```
  | `references/conflict-analysis.md` | 4a–4e 实现脚本、冲突类型 A/B/C/D/E 完整定义与选项、Step 5 呈现格式 | Step 4/5：执行分析前读取 |
  ```

- [ ] **Step 4: 运行 npm test**

  ```bash
  cd /Users/harveyzhang96/Projects/harveyz-skill && npm test
  ```
  预期：pass。

- [ ] **Step 5: 规格验收对照**

  逐条对照 `docs/superpowers/specs/2026-07-02-init-workflow-git-config-healthcheck.md` 验收标准表：

  | 场景 | 检查方式 |
  |------|---------|
  | skill 首次运行 | Step 6 已有 `git config` 命令，lock 写入时含 git_config 节（确认 lock-file-format.md 已更新） |
  | skill 重新运行，config 正常 | 4e 检查通过：Step 9 显示 ✅（两行均已添加到表格中） |
  | skill 重新运行，config 丢失 | Step 5 类型 E：选 A → Step 9 显示 ❌ 已修复（conflict-analysis.md 已定义） |
  | 用户选 B（跳过） | Step 9 显示 ❌ 未修复（附注"hooks 当前不生效"，已在类型 E 定义中） |
  | merge.ff 缺失（单独） | 独立作为一条类型 E 列出（定义中说明"每项独立列出，最多两条"） |

  所有场景均有覆盖则视为通过。

- [ ] **Step 6: Commit**

  ```bash
  git add skills/coding/init-workflow/SKILL.md
  git commit -m "feat(init-workflow): Step 4e git config 健康检查 + Step 9 状态汇报"
  ```
