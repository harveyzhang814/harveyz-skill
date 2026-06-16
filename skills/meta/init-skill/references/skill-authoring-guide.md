# Skill Authoring Guide

本文档是编写高质量 skill 的参考标准，供 `init-skill` 在生成新 skill 时检查并应用。分两类：
- **显性规范**：来自 `docs/reference/skill-spec.md` 的硬性规则
- **隐性模式**：从现有优质 skill 提炼的最佳实践

---

## 显性规范（F1–F7，来自 skill-spec.md）

### 命名规范（F7）

格式：`<verb>-<noun>`，恰好 2 词，连字符分隔，全小写。

**规范动词词表：**

| 动词 | 含义 |
|------|------|
| `extract` | 从来源提取结构化数据 |
| `learn` | 处理教学/视频内容 |
| `forge` | 生成文档产物 |
| `draw` | 创建可视化图表 |
| `manage` | 组织文件或目录 |
| `migrate` | 跨格式或位置转换数据 |
| `scout` | 调查外部来源 |
| `build` | 构建配置或制品 |
| `sync` | 保持两端同步 |
| `publish` | 推送到外部注册表 |
| `archive` | 移至归档或退役 |
| `contribute` | 将外部内容引入本仓库 |
| `analyze` | 深度检查或分析 |
| `clean` | 清理废弃项 |
| `release` | 创建版本发布 |
| `validate` | 验证或校验 |
| `init` | 初始化新配置 |
| `dispatch` | 派发任务 |
| `close` | 收尾完成任务 |
| `setup` | 准备环境 |
| `capture` | 记录想法或洞察 |
| `dedup` | 检测消除重复内容 |
| `runby` | 委托给指定外部工具（特殊前缀，后接工具名） |

**违规示例：** `skill-analyzer`（动词不在词表）、`diagram`（单词）、`doc-forge`（应为 `forge-doc`）

### frontmatter 字段（F1–F5）

每个 SKILL.md 必须包含：

```yaml
---
name: <与目录名完全一致>（目录名本身须遵循 F7 命名规范：`<verb>-<noun>` 格式，动词在词表中）
description: "<英文，≥ 10 字符，含触发短语>"
user_invocable: true   # 或 false
version: "1.0.0"       # semver，新 skill 从 1.0.0 开始
---
```

> description 格式详见下方「隐性模式 → description 写法」节：必须以动词短语开头，后接 `Triggers: '<场景1>', '<场景2>'...`。

`user_invocable` 取值规则：
- `true`：用户可通过 `/skill-name` 直接触发的 skill
- `false`：仅供其他 skill 内部引用、不直接对用户暴露的辅助 skill

### 语言规范（F3、F6）

- `description` 字段：**必须为英文**，不含中文字符
- 正文内容：**必须含至少一个中文字符**

### 状态管理

**`.hskill/<skill-name>/` 配置缓存**

跨会话需要持久化的配置/状态，统一存放在项目本地 `.hskill/<skill-name>/` 目录下。Step 1 优先读此目录；不存在则用默认值或询问用户后写入。

参考实现：
```
.hskill/clean-git/branch-cleanup.md
.hskill/init-workflow/workflow-config.yml
.hskill/release-project/release-profile.md
```

不要把状态散落在 `~/` 任意位置或临时文件中，统一目录便于审计和清理。

**批量操作模式（仅适用于幂等批量 skill）**

若 skill 是"批量更新 / 同步 / 校验"类（典型如 init-workflow、sync-design、publish-skill），应满足两点：

1. **Lock / snapshot 文件做变更检测**
   维护 `.lock` 或 manifest 快照记录"上次运行的状态"，实现 delta 操作而非整体重写：
   ```
   init-workflow → .githooks/.workflow-config.lock.yml
   sync-design   → manifest.json 含 lastSyncCommit
   publish-skill → skills-index.json 中的 contentHash
   ```

2. **delta 报告：UPDATED / NEW / UNCHANGED**
   批量操作完成后，每个条目都标注状态，让用户能跳过未变项：
   ```
   | 文件 | 状态 |
   |------|------|
   | .githooks/pre-commit | UPDATED |
   | .githooks/commit-msg | UNCHANGED |
   | .githooks/pre-push   | NEW |
   ```

非批量 skill 不必引入此模式。

---

## 隐性模式（从现有优质 skill 提炼）

### 正文结构惯例

推荐节顺序：
1. **触发条件**（覆盖"触发"和"不触发"两种情况）
2. **执行步骤**（Step 0 / Step 1 / Step N，每步一个原子操作）
3. **不在范围内**（明确边界，防止误用扩大）

### description 写法

**格式模板：**
```
"<动词短语描述功能>. Triggers: '<场景1>', '<场景2>', '<场景3>'."
```

**要点：**
- 触发词宁宽勿窄，但避免与现有 skill 重叠
- 举例比泛描述精确：用 `'create new skill', 'scaffold skill'` 而不是 `"when user wants to create skills"`
- 检查是否覆盖了中文触发方式（如 `'新建 skill'`、`'从 spec 创建'`）

检查现有 skill 的 description 是否有重叠：
```bash
grep -r "^description:" skills/*/*/SKILL.md
```

### 边界说明（不在范围内）

- **必须有**"不在范围内"节，列出 2-4 个常见误用场景
- 防止 skill 在对话中被过度扩展
- 推荐格式：
  ```
  ## 不在范围内
  - <误用场景>（应使用 <替代 skill>）
  ```

### 边界情况表格

复杂多分支步骤的末尾，用表格列出所有边界条件和处理方式（路径已存在、配置缺失、检测到多个候选等）。让 skill 自带边界检查清单，一眼看全所有分支：

```
| 情况 | 处理 |
|------|------|
| 目标路径已存在同名 skill | 询问覆盖 / 重命名 / 中止 |
| 源 SKILL.md 格式损坏     | 停止，报告问题 |
| 脚本执行失败              | 报告错误，不 commit，保留文件 |
```

无表格的 skill 容易在对话中漏处理边界情况。

### references/ 子目录

**基础使用时机：**
- Skill 需要携带查找表、模板、禁忌清单
- 参考材料超过 20 行，内联会影响 SKILL.md 可读性

**不使用时机：**
- 小规模内容（< 20 行）直接内联在 SKILL.md

**进阶用法 — 平台/技术栈特定文档：**

让 SKILL.md 顶层逻辑保持技术中立，平台/格式/技术栈特定内容放进 `references/` 下，运行时按检测结果动态读取。扩展通过加文件而非改 SKILL.md。

参考实现：
```
setup-debug  → references/tech-stacks/<stack>.md
extract-url  → platforms/SKILL.<platform>.md
sync-design  → references/stack-<name>.md
```

### Step 粒度

- 每步对应一个可验证的结果
- 步骤名用"动词 + 名词"：`Step 1 — 定位设计文档`
- 有用户交互（等待确认）的步骤，明确写"等用户确认后才进入 Step N+1"

### 交互设计：批量收集，统一决策

出现冲突或多选项状态时，先收集**所有**冲突再分组展示，让用户一次性逐条决策；不要边发现边问。

反模式：
```
（边扫描边问）
找到 main 分支待删除，是否删除？(y/n)
找到 feature/abc 已合并，是否删除？(y/n)
...
```

推荐模式：
```
（一次性汇总）
━━ 组 A：明显可删（已合并 + 远端无引用）━━
  - feature/abc
  - fix/xyz
━━ 组 B：可能可删（远端已删）━━
  - hotfix/123
━━ 组 C：保留 ━━
  - feature/wip
请逐条标注 [删 / 留]：
```

参考：init-workflow 冲突汇总、clean-git 分支分组、sync-design ⑤-A 分支处理。

### 输出格式：Emoji 与状态标记规范

确认提示和报告统一使用以下视觉符号：

| 符号 | 含义 |
|------|------|
| `✓` / `✅` | 通过 / 完成 |
| `⚠️` | 注意 / 需关注 |
| `❌` | 失败 / 拒绝 |
| `━━━` | 分组分隔（如 `━━ 组 A ━━`） |

状态标签统一用大写英文：`UPDATED` / `UNCHANGED` / `NEW` / `OK` / `FAIL`。

示例：
```
✓ contentHash 已更新（v1.0.0）
⚠️ 检测到未提交修改
❌ generate-npmignore.js 执行失败
━━ 组 A：明显可删 ━━
```

避免使用花哨或语义不明的符号（如 ❀ ✨ 🎉）。

### 触发条件与其他 skill 的区分

若功能与现有 skill 有重叠，在触发条件节明确区分：
```
不触发（其他 skill 负责）：
- 从其他项目导入已有 skill → contribute-skill
- 校验格式或注册 index → publish-skill
```

### Skill 间协作："下一步"交棒提示

Skill 完成后不直接结束，而是给出下一步建议：调用下一个相关 skill、或问用户是否深入某部分。这让 skill 生态可组合，而不是孤立运行。

示例：
```
init-skill   → "下一步：运行 /publish-skill 完成注册"
scout-brand  → "确认后可运行 /build-style 生成样式"
learn-skill  → "还有哪个部分想深入了解？"
```

最终输出位置：在 skill 的执行总结之后，作为独立的提示行。

### 安全与健壮性：Bash 字符串拼接禁忌

Skill 中嵌入 bash 或 python 时，禁止用 shell 字符串拼接传值，应使用：

- Python：`subprocess.run([...])` 列表参数形式
- Bash：把变量作为命令参数传递，命令内通过 `$1`、`process.argv[N]` 接收
- URL / 路径 / 用户输入：先做净化（正则替换、白名单校验），再使用

反模式：
```bash
node -e "const r='${USER_INPUT}'; ..."   # ${USER_INPUT} 可注入恶意代码
```

推荐模式：
```bash
node -e "const r=process.argv[1]; ..." "$USER_INPUT"
```

参考：extract-url URL 净化规则、setup-debug subprocess 列表参数、sync-design 命令注入防护。

### 活文档原则

本 guide 是活文档。发现新的好/坏模式后，更新本文件而不是修改 init-skill 的 SKILL.md。init-skill 运行时读取最新版本，自动生效。

### 注册到 skills-index.json

SKILL.md 创建后必须在 `skills-index.json` 中注册，否则该 skill 不会被纳入 npm 发布，也不会被测试套件校验。注册由 `publish-skill` 处理 — `init-skill` 生成骨架后，提示用户运行 `/publish-skill` 完成注册。
