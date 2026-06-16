# Skill 共性模式候选清单

**日期：** 2026-06-16
**用途：** 从 harveyz-skill 仓库现有 skill 中提炼的共性模式，供评审决定是否纳入 `skill-authoring-guide.md`
**研究范围：** 10 个跨类别 skill（meta / coding / research / creative / design / experiment / writing）
**Baseline 已包含（不重复列出）：** 命名规范、frontmatter 字段、语言规范、正文结构、description Triggers 格式、references/ 阈值、Step 粒度、不在范围内节、skill 区分、skills-index.json 注册

---

## 候选清单（13 条）

---

### 第一组：状态与配置

#### 1. `.hskill/<skill-name>/` 配置缓存

**Found in：** publish-skill, clean-git, init-workflow, sync-design, release-project, setup-debug, extract-url
**描述：** Skill 把跨会话需要持久化的配置/状态存在项目本地 `.hskill/<skill-name>/` 目录下。每次运行 Step 1 先读此目录，未找到时落到默认值或询问用户。
**示例：**
```
clean-git → .hskill/clean-git/branch-cleanup.md
init-workflow → .hskill/init-workflow/workflow-config.yml
release-project → .hskill/release-project/release-profile.md
```
**建议位置：** 显性规范 → 状态管理

---

#### 2. "读取配置"作为第一执行步骤

**Found in：** publish-skill, clean-git, init-workflow, sync-design, release-project, setup-debug
**描述：** 有状态的 skill 第一个实质步骤（Step 1 或 Step 2）总是：检测配置文件存在性 → 不存在则用默认或询问用户 → 解析校验 → 才进入业务步骤。
**示例：**
```
sync-design → "步骤 ①：读取 Manifest"
init-workflow → "Step 2 — 读取配置"
```
**建议位置：** 隐性模式 → 执行流程惯例

---

#### 3. Lock / snapshot 文件做变更检测

**Found in：** init-workflow, sync-design, publish-skill
**描述：** Skill 维护 `.lock` 或 manifest 快照文件，记录"上次运行的状态"，实现 delta 操作（只更新变化的部分）。
**示例：**
```
init-workflow → .githooks/.workflow-config.lock.yml
sync-design → manifest.json 含 lastSyncCommit
publish-skill → skills-index.json 中的 contentHash
```
**建议位置：** 隐性模式 → 状态管理

---

#### 4. 多源配置覆盖链

**Found in：** sync-design, build-style, init-workflow
**描述：** 多个配置源按固定顺序读取，后读优先级更高，可覆盖前面通用指引。明确写出"后读的内容优先级更高"。
**示例：**
```
sync-design ⑤-A:
designSpec → designSystemFile → stackRef → styleStrategy → notes → 当前 HTML
（后读覆盖前读）
```
**建议位置：** 隐性模式 → 配置解析

---

### 第二组：错误处理与边界

#### 5. "边界情况"表格放在步骤末尾

**Found in：** clean-git, init-workflow, setup-debug, publish-skill, contribute-skill
**描述：** 复杂多分支步骤的末尾以表格列出所有边界条件和处理方式（路径已存在、配置缺失、检测到多个候选等）。便于一眼看全所有分支。
**示例：**
```
| 情况 | 处理 |
|------|------|
| 目标路径已存在同名 skill | 询问覆盖/重命名/中止 |
| 源 SKILL.md 格式损坏 | 停止，报告问题 |
| `generate-npmignore.js` 失败 | 报告错误，不 commit |
```
**建议位置：** 隐性模式 → Step 文档结构

---

#### 6. 冲突解决：批量收集，统一决策

**Found in：** init-workflow, clean-git, sync-design
**描述：** 出现冲突状态（用户手改与自动生成冲突、多个规则类别同时存在）时，先收集所有冲突再分组展示，让用户一次性逐条决策；不是边发现边问。
**示例：**
```
init-workflow Step 5: "一次性汇总，用户逐条决策"
clean-git Step 5: 把分支分成 A/B/C 三组分别展示
```
**建议位置：** 隐性模式 → 交互设计

---

### 第三组：扩展与组合

#### 7. references/ 子目录承载平台/技术栈特定文档

**Found in：** setup-debug, sync-design, extract-url, build-style, scout-brand
**描述：** Skill 顶层逻辑保持技术中立，平台/格式/技术栈特定内容放进 `references/` 下，运行时按检测结果动态读取。让 skill 主体保持简洁，扩展通过加文件而非改 SKILL.md。
**示例：**
```
setup-debug → references/tech-stacks/<stack>.md
extract-url → platforms/SKILL.<platform>.md
sync-design → references/stack-<name>.md
```
**建议位置：** 显性规范 → 目录结构（扩展原有 references/ 节）

---

#### 8. Subagent 委派 + 变量注入

**Found in：** extract-url, setup-debug
**描述：** Skill 把工作分派给 subagent 时，用环境变量注入运行时值（不是字符串拼接），并加载平台特定的 patch 文件来转译不同执行上下文的工具调用。
**示例：**
```
extract-url:
  VAULT_PATH, CHROME_PROFILE 通过环境变量传入
  按执行平台读取 platforms/SKILL.claude.md 或 SKILL.codex.md
```
**建议位置：** 隐性模式 → 多会话协作

---

### 第四组：输出与协作

#### 9. Emoji 与状态标记规范化

**Found in：** clean-git, init-workflow, setup-debug, release-project, publish-skill
**描述：** 确认提示和报告统一使用一套视觉符号：✓ / ✅（通过）、⚠️（注意）、❌（失败）、`━━━`（分组分隔），状态标签 `UPDATED` / `UNCHANGED` / `NEW` / `OK` / `FAIL`。
**示例：**
```
━━ 组 A：明显可删 ━━
✅ 配置审核通过
✓ contentHash 已更新
```
**建议位置：** 隐性模式 → 输出格式

---

#### 10. 时间戳化 delta 报告

**Found in：** init-workflow, sync-design, release-project
**描述：** 批量操作完成后，每个文件/条目都标注状态（NEW / UPDATED / UNCHANGED），让用户能跳过未变项。
**示例：**
```
init-workflow Step 9:
| 文件 | 状态 |
|------|------|
| .githooks/pre-commit | UPDATED |
| .githooks/commit-msg | UNCHANGED |
| .githooks/pre-push   | NEW |
```
**建议位置：** 隐性模式 → 输出结构

---

#### 11. "下一步"交棒提示

**Found in：** learn-skill, scout-brand, build-style, init-skill（本次新加）
**描述：** Skill 完成后不直接结束，而是给出下一步建议：调用下一个相关 skill、或问用户是否深入某部分。
**示例：**
```
scout-brand: "确认后可运行 /build-style"
learn-skill: "还有哪个部分想深入了解？"
init-skill: "下一步：运行 /publish-skill 完成注册"
```
**建议位置：** 隐性模式 → Skill 间协作

---

### 第五组：安全与规范

#### 12. Bash 安全：禁止字符串拼接

**Found in：** extract-url, setup-debug, sync-design
**描述：** Skill 中嵌入 bash/python 时，明确说明禁止用 shell 字符串拼接传值，应使用 `subprocess` 列表形式或环境变量。
**示例：**
```
extract-url: "禁止 bash 字符串拼接，避免 shell 注入"
              用 subprocess 列表参数代替
              URL 净化用正则替换而非字符串
```
**建议位置：** 隐性模式 → 安全与健壮性

---

#### 13. 版本字段在内容 hash 计算中视为占位

**Found in：** publish-skill, release-project
**描述：** 当 skill 计算 SKILL.md 内容 hash 用于变更检测时，将 `version:` 行替换为固定占位符再计算，避免单纯改 version 触发"内容变更"误报。
**示例：**
```
publish-skill F8:
  sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' SKILL.md \
    | sha256sum | cut -c1-16
```
**建议位置：** 隐性模式 → 版本规则

---

## 评审说明

每条候选请逐条标注：

- **✓ 纳入** — 直接写入 authoring guide
- **✗ 跳过** — 不纳入（理由可选）
- **△ 修改后纳入** — 提出调整意见

可以全部一次列出决定，也可以分组逐组讨论。
