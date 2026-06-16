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

### references/ 子目录

**使用时机：**
- Skill 需要携带查找表、模板、禁忌清单
- 参考材料超过 20 行，内联会影响 SKILL.md 可读性

**不使用时机：**
- 小规模内容（< 20 行）直接内联在 SKILL.md

### Step 粒度

- 每步对应一个可验证的结果
- 步骤名用"动词 + 名词"：`Step 1 — 定位设计文档`
- 有用户交互（等待确认）的步骤，明确写"等用户确认后才进入 Step N+1"

### 触发条件与其他 skill 的区分

若功能与现有 skill 有重叠，在触发条件节明确区分：
```
不触发（其他 skill 负责）：
- 从其他项目导入已有 skill → contribute-skill
- 校验格式或注册 index → publish-skill
```

### 活文档原则

本 guide 是活文档。发现新的好/坏模式后，更新本文件而不是修改 init-skill 的 SKILL.md。init-skill 运行时读取最新版本，自动生效。

### 注册到 skills-index.json

SKILL.md 创建后必须在 `skills-index.json` 中注册，否则该 skill 不会被纳入 npm 发布，也不会被测试套件校验。注册由 `publish-skill` 处理 — `init-skill` 生成骨架后，提示用户运行 `/publish-skill` 完成注册。
