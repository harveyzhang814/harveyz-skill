# Skill Authoring Guide

init-skill 使用本文件作为生成新 skill 时的规范检查清单。内容分两类：**显性规范**（硬性要求，不符合则 publish-skill 报错）和**隐性模式**（从现有优质 skill 提炼的最佳实践）。

---

## 显性规范

### 命名

- 目录名格式：`<verb>-<noun>`（2 段，连字符分隔，全小写）
- 动词必须在词表中：

```
extract  learn    forge    draw     manage   migrate  scout
build    sync     publish  archive  contribute  analyze  clean
release  validate init     dispatch close    setup    capture
runby    dedup    survey
```

特殊：以 `runby-` 开头的目录直接视为合规。

### Frontmatter 必填字段

| 字段 | 要求 |
|------|------|
| `name` | 非空，值 == 目录名 |
| `description` | 英文，≥ 10 字符，不含中文字符 |
| `user_invocable` | 显式声明 `true` 或 `false` |
| `version` | semver 格式 `X.Y.Z`，初始值 `"1.0.0"` |

### description 格式

```
"<动词短语说明功能>. Triggers when <触发条件>. e.g. '<示例指令1>', '<示例指令2>'."
```

触发词宁宽勿窄，但要避免与现有 skill 触发场景重叠。举例比描述更精确。

### 正文语言

frontmatter 结束后的正文应为中文（含至少一个中文字符即合规）。

---

## 隐性模式

### 正文结构

推荐节顺序：**触发条件 → 执行步骤（Step N） → 边界说明（不在范围内）**

- 每个 Step 对应一个可验证的原子操作，不要把两个动作塞进同一步
- 边界说明必须有，明确列出 2-4 个常见误用场景，防止 skill 在对话中被过度扩展

### 状态与配置

**1. `.hskill/<skill-name>/` 配置缓存**（7 个 skill 使用此模式）

有状态的 skill 将配置持久化到 `$HOME/.hskill/<skill-name>/`，每次运行 Step 1 先读此目录，未找到时落到默认值或询问用户。

```
clean-git → ~/.hskill/clean-git/branch-cleanup.md
init-workflow → ~/.hskill/init-workflow/workflow-config.yml
```

**2. "读取配置"作为第一执行步骤**（6 个 skill 使用此模式）

有状态 skill 的第一个实质步骤总是：检测配置文件存在性 → 不存在则用默认或询问 → 解析校验 → 才进入业务步骤。

**3. Lock / snapshot 文件做变更检测**（3 个 skill 使用此模式）

维护 `.lock` 或 manifest 快照，记录"上次运行状态"，实现 delta 操作（只处理变化部分）。

```
init-workflow → .githooks/.workflow-config.lock.yml
sync-design → manifest.json 含 lastSyncCommit
publish-skill → skills-index.json 中的 contentHash
```

**4. 多源配置覆盖链**（3 个 skill 使用此模式）

多个配置源按固定顺序读取，后读优先级更高。明确注明"后读内容优先级更高"。

### 错误处理与边界

**5. "边界情况"表格放在步骤末尾**（5 个 skill 使用此模式）

复杂多分支步骤末尾用表格列出所有边界条件和处理方式，便于一眼看全所有路径。

```markdown
| 情况 | 处理 |
|------|------|
| 目标路径已存在 | 停止报错，不覆盖 |
| generate-npmignore.js 失败 | 报错，不执行 git 操作 |
```

**6. 冲突解决：批量收集，统一决策**（3 个 skill 使用此模式）

出现冲突时，先收集所有冲突再分组展示，让用户一次性逐条决策。不要边发现边问。

### 扩展与组合

**7. references/ 承载平台/技术栈特定文档**（5 个 skill 使用此模式）

Skill 顶层逻辑保持技术中立，平台/格式特定内容放进 `references/`，运行时按检测结果动态读取。扩展通过加文件而非改 SKILL.md。

```
setup-debug → references/tech-stacks/<stack>.md
extract-url → platforms/SKILL.<platform>.md
```

阈值：references/ 内单文件 > 20 行时才提取；小内容直接内联。

**8. Subagent 委派 + 变量注入**（2 个 skill 使用此模式）

Skill 委派 subagent 时用环境变量注入运行时值（不是字符串拼接），并加载平台特定 patch 文件。

### 输出格式

**9. Emoji 与状态标记规范化**（5 个 skill 使用此模式）

统一视觉符号：`✓` / `✅`（通过）、`⚠️`（注意）、`❌`（失败）、`━━━`（分组分隔）。状态标签：`UPDATED` / `UNCHANGED` / `NEW` / `OK` / `FAIL`。

**10. 时间戳化 delta 报告**（3 个 skill 使用此模式）

批量操作后每个条目标注状态（NEW / UPDATED / UNCHANGED），用户可跳过未变项。

```markdown
| 文件 | 状态 |
|------|------|
| .githooks/pre-commit | UPDATED |
| .githooks/commit-msg | UNCHANGED |
```

**11. "下一步"交棒提示**（4 个 skill 使用此模式）

Skill 完成后给出明确的下一步建议：调用下一个 skill，或询问用户是否深入某部分。

```
scout-brand: "确认后可运行 /build-style"
init-skill:  "下一步：运行 /publish-skill 完成注册"
```

### 安全与规范

**12. Bash 安全：禁止字符串拼接**（3 个 skill 使用此模式）

Skill 中嵌入 bash/Python 时，禁止用 shell 字符串拼接传值。使用 `subprocess` 列表参数或环境变量；URL 净化用正则替换。

**13. 版本字段在内容 hash 计算中视为占位**（2 个 skill 使用此模式）

计算 SKILL.md 内容 hash 时，将 `version:` 行替换为固定占位符再计算，避免单纯改版本号触发"内容变更"误报。

```bash
sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' SKILL.md | sha256sum | cut -c1-16
```
