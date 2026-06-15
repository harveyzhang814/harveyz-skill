# Skill 规格参考

本文档是 `skills/` 下所有 skill 的格式、命名、注册规则的单一来源。`publish-skill` 的检查项（F1–F7、R1–R3）均以此为依据。

---

## 目录结构

### Flat skill

```
skills/<category>/<skill-name>/
  SKILL.md
  references/        # 可选
```

### Skill group

```
skills/<group>/
  <skill-name>/
    SKILL.md
    references/      # 可选
```

`archived/` 是特殊分类，存放已废弃 skill，不参与发布，命名规范检查（F7）对其跳过。

---

## SKILL.md 格式

每个 skill 必须包含 `SKILL.md`，文件以 YAML frontmatter 开头：

```yaml
---
name: skill-name
description: "English description of what this skill does and when to trigger it."
user_invocable: true
version: "1.0.0"
---
```

### 字段规范（F1–F7）

| 编号 | 字段 / 检查项 | 规范 |
|------|--------------|------|
| F1 | frontmatter 存在 | 文件以 `---` 开头，有第二个 `---` 结束 |
| F2 | `name` | 非空，值 == 目录名（`path` 的最后一段） |
| F3 | `description` | 非空，长度 ≥ 10 字符，**必须为英文**（不含中文字符） |
| F4 | `version` | 非空，格式为 `X.Y.Z`（semver） |
| F5 | `user_invocable` | 显式声明 `true` 或 `false` |
| F6 | 正文语言 | frontmatter 结束后的正文应包含至少一个中文字符（纯英文贡献 skill 可豁免，需确认） |
| F7 | 目录命名规范 | 见下方「命名规范」；`archived/` 下跳过此检查 |

---

## 命名规范（F7）

### 基本格式

```
<动词>-<名词>
```

- 恰好 2 个单词，连字符分隔，全小写
- **必须以规范动词开头**
- 名词不得使用工具或平台专有名（youtube、npm、diataxis 等）

### 规范动词词表

新 skill 优先复用已有动词；确有必要时可扩展，须同步更新此表。

| 动词 | 含义 |
|------|------|
| `extract` | 从来源提取结构化数据 |
| `learn` | 处理教学 / 视频内容 |
| `forge` | 生成文档产物 |
| `draw` | 创建可视化图表 |
| `manage` | 在目录或系统内组织文件 |
| `migrate` | 跨格式或位置转换数据 |
| `scout` | 调查外部来源获取信息 |
| `build` | 构建配置或制品 |
| `sync` | 保持两端同步 |
| `publish` | 推送到外部注册表 |
| `archive` | 移至归档或退役状态 |
| `contribute` | 将外部内容引入本仓库 |
| `analyze` | 深度检查或分析 |
| `clean` | 清理废弃项 |
| `release` | 创建版本发布 |
| `validate` | 验证或校验 |
| `init` | 初始化新配置 |
| `dispatch` | 派发任务给其他 agent |
| `close` | 收尾或完成任务 |
| `setup` | 准备环境 |
| `capture` | 记录想法或洞察 |
| `runby` | 委托给指定外部工具执行（特殊前缀，后接工具名） |
| `dedup` | 检测并消除重复内容 |

### 特殊模式：`runby-<tool>`

当 skill 核心功能是"委托某个特定外部工具执行"时，使用 `runby-<tool>` 格式，`<tool>` 为外部工具名。这是唯一允许工具名入名的模式。

示例：`runby-opencode`

### 违规示例

| 目录名 | 违规原因 |
|--------|---------|
| `skill-analyzer` | 动词 `skill` 不在词表 |
| `diagram` | 单词，非 2 段 |
| `youtube-learner` | 动词 `youtube` 不在词表 |
| `doc-forge` | 动词 `doc` 不在词表（应为 `forge-doc`） |

---

## skills-index.json 注册规范（R1–R3）

每个 skill 必须在 `skills-index.json` 的 `skills[]` 数组中注册。

### 字段规范

| 编号 | 检查项 | 规范 |
|------|--------|------|
| R1 | `skills[]` 条目存在 | `path` 值 == `category/skill-name` |
| R2 | `bundle` 字段 | 非空，必须指定归属 bundle |
| R3 | bundle 已声明 | `bundle` 值必须存在于 `bundleMeta` |

### 条目格式

```json
{ "path": "meta/publish-skill", "bundle": "meta" }
```

### 注册后操作

注册或修改 `skills-index.json` 后，必须运行：

```bash
node scripts/generate-npmignore.js
```

---

## 迁移映射（renames）

`skills-index.json` 顶层 `renames[]` 字段记录旧名到新名的映射，供 `hskill update` 自动迁移已安装的旧名称 skill：

```json
{
  "renames": [
    { "from": "url-extract", "to": "extract-url" }
  ]
}
```

每次重命名 skill 目录时，须同步在 `renames[]` 中添加对应条目。
