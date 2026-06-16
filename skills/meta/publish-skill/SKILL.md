---
name: publish-skill
description: "Validate and publish a skill to the harveyz-skill repository. Checks SKILL.md format compliance (frontmatter fields, semver version, name-directory match, verb-noun naming convention) and registration in skills-index.json. Rules defined in docs/reference/skill-spec.md. Triggers: publish skill, register skill, validate skill format, check skill, add skill to index, is skill ready to publish."
user_invocable: true
version: "1.2.1"
---

# skill-publish

检查 `skills/` 目录下的 skill 是否满足项目格式要求，并已注册到发布配置（`skills-index.json`）。

---

## 执行步骤

### Step 1 — 确定检查范围

**从对话上下文推断要检查的 skill：**

1. 若用户指定了具体 skill 名称或路径 → 只检查该 skill
2. 若用户说"所有 skill"或未指定 → 检查全部
3. 若用户说"新的"或"未注册的" → 先执行 Step 2 找出未注册的，仅检查那些

### Step 2 — 扫描未注册 skill（按需）

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)

# 找出所有 SKILL.md 对应的目录（相对 skills/ 的路径）
find "${REPO_ROOT}/skills" -name "SKILL.md" | while read f; do
  dir=$(dirname "$f")
  echo "${dir#${REPO_ROOT}/skills/}"
done | sort > /tmp/sv-on-disk.txt

# 从 skills-index.json 提取已注册路径
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path));
" | sort > /tmp/sv-registered.txt

# 未注册（在磁盘但不在 index）
comm -23 /tmp/sv-on-disk.txt /tmp/sv-registered.txt > /tmp/sv-unregistered.txt
cat /tmp/sv-unregistered.txt
```

如果找到未注册 skill，列出后询问用户：
- 是否一并做格式检查
- 是否要把它们注册到 `skills-index.json`（若是，按 Step 6 执行）

### Step 3 — 格式检查

对每个待检查的 skill，读取其 `SKILL.md` 并逐项核验：

| 编号 | 检查项 | 规范 |
|------|--------|------|
| F1 | frontmatter 存在 | 文件以 `---` 开头，有第二个 `---` 作为结束 |
| F2 | `name` 字段 | 非空，且值 == 目录名（`path` 的最后一段） |
| F3 | `description` 字段 | 非空，长度 ≥ 10 字符，**必须为英文** |
| F4 | `version` 字段 | 非空，格式为 `X.Y.Z`（semver） |
| F5 | `user_invocable` 字段 | 显式声明 `true` 或 `false` |
| F6 | 正文语言 | frontmatter 结束后的正文内容应为中文（含中文字符即视为合规） |
| F7 | 目录命名规范 | skill 目录名须为 `<动词>-<名词>` 格式（2 词，连字符分隔，全小写），且动词必须在规范词表中；`archived/` 下的 skill 跳过此检查 |
| F8 | 内容 hash | 若 `skills-index.json` 中有 `contentHash` 记录：hash 不同且 version 未变 → 报错；hash 不同且 version 已递增 → 通过，Step 7 更新；无记录 → 首次初始化，Step 7 写入 |

**F3 英文检测方法：** 提取 `description` 字段值，检查是否包含中文字符（`一-鿿` 范围）。有则报错。

**F6 中文检测方法：** 提取 frontmatter 结束后的正文，检查是否包含至少一个中文字符。若正文全为英文或为空则报错。（纯英文 skill 如从其他项目贡献的可跳过此项，需用户确认。）

**F7 命名规范检测方法：**

1. 取目录名（`path` 最后一段）
2. 按连字符分割，检查是否恰好 2 段
3. 检查第一段（动词）是否在规范词表中：

```
extract  learn    forge    draw     manage   migrate  scout
build    sync     publish  archive  contribute  analyze  clean
release  validate init     dispatch close    setup    capture
runby    probe    dedup
```

特殊模式：若目录名以 `runby-` 开头，直接视为合规（无需检查名词部分）。

违规示例：`skill-analyzer`（动词不在词表）、`diagram`（单词，非 2 段）、`youtube-learner`（动词不在词表）

**F8 hash 计算方法：**

读取 `SKILL.md` 全文，将 `version:` 行替换为固定占位符后计算 SHA-256，取前 16 位：

```bash
compute_content_hash() {
  sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' "$1" \
    | sha256sum | cut -c1-16
}
```

从 `skills-index.json` 中读取 `contentHash`（存储 hash）和 `contentVersion`（存储 hash 时的版本号），与当前值对比：

| `current_hash` vs `stored_hash` | `current_version` vs `contentVersion` | 结论 |
|---------------------------------|---------------------------------------|------|
| 相同 | 任意 | 内容未变，✓ |
| 不同 | 相同 | 内容变更但版本未 bump → **F8 违规** |
| 不同 | 不同 | 内容变更且版本已递增 → ✓，Step 7 更新 |
| `contentHash` 字段不存在 | — | 首次初始化 → ✓，Step 7 写入 |

**读取 frontmatter 字段的方法：**

```bash
_fm() {
  local file="$1" field="$2"
  awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' "$file" \
    | grep "^${field}:" | head -1 \
    | sed "s/^${field}:[[:space:]]*//" | tr -d '"'"'"
}
```

### Step 4 — 注册检查

对每个待检查的 skill，核验 `skills-index.json` 中的状态：

| 编号 | 检查项 | 规范 |
|------|--------|------|
| R1 | `skills[]` 中有对应条目 | `path` 值 == `category/name` |
| R2 | 对应条目有 `bundle` 字段且非空 | 必须指定归属 bundle |
| R3 | `bundle` 值存在于 `bundleMeta` | bundle key 必须已声明 |

### Step 5 — 输出报告

按以下结构输出，所有问题集中展示：

```
skill-publish 检查结果
========================

[检查范围：N 个 skill]

格式问题
--------
  skills/meta/my-skill
    F2  name 字段值 'my_skill' != 目录名 'my-skill'
    F5  user_invocable 字段缺失
    F8  内容自 v1.0.0 起已变更，version 仍为 1.0.0，请 bump 后重新运行

注册问题
--------
  skills/meta/my-skill
    R1  未在 skills-index.json 中注册

全部通过
--------
  skills/meta/contribute-skill  ✓
  skills/meta/publish-skill     ✓
  ...

========================
共发现 3 个问题（2 个格式，1 个注册）
```

若全部通过：

```
skill-publish 检查结果
========================
所有 N 个 skill 格式与注册均符合规范。✓
```

### Step 6 — 修复引导（按需）

若发现问题，询问用户是否要逐项修复：

**格式问题** — 展示 diff，用户确认后直接编辑 `SKILL.md`：
```
修复 F2（name 字段）：
  - name: my_skill
  + name: my-skill
应用此修复？(y/n)
```

**格式问题（F7）** — 命名不符合规范时，先建议新名：
```
修复 F7（目录命名规范）：
  当前名称：skill-analyzer
  建议改为：analyze-skill（动词 analyze 在词表中，名词 skill）
  需要重命名目录并更新 skills-index.json 的 path 字段。
  是否继续？(y/n)
```
确认后执行 `git mv` 重命名目录，并更新 `skills-index.json` 中对应的 `path` 值，最后运行 `node scripts/generate-npmignore.js`。

**格式问题（F8）** — 询问 bump 类型后自动更新版本号，随即执行 Step 7：
```
修复 F8（内容 hash 不匹配）：
  skill 内容自 v1.0.0 起已变更，但 version 仍为 1.0.0。
  请选择升级类型：
    [1] patch → 1.0.1（bugfix / 措辞调整）
    [2] minor → 1.1.0（新增步骤 / 行为变更）
    [3] major → 2.0.0（Breaking Change）
```
用户选择后，用 Edit 工具将 SKILL.md frontmatter 中的 `version:` 行更新为新版本号，然后直接进入 Step 7（hash 不同 + version 已递增，满足更新条件）。

**注册问题（R1）** — 交互引导补注册：
```
'meta/my-skill' 未注册。
现有 bundle：
  1. analysis — ...
  2. meta     — ...
  N. [新建 bundle]
选择目标 bundle：
```

选定后，在 `skills[]` 末尾追加：
```json
{ "path": "meta/my-skill", "bundle": "meta" }
```

若新建 bundle，在 `bundleMeta` 中同步添加。

完成注册后运行：
```bash
cd "${REPO_ROOT}" && node scripts/generate-npmignore.js
```

### Step 7 — 更新 contentHash

在以下两种情况下执行，其余情况跳过：
- **首次初始化**：index 中无 `contentHash` 字段
- **F8 通过路径**：hash 不同 + version 已递增

**操作方式：直接读写 `skills-index.json`，不使用 shell 脚本。**

用 Read 工具读取 `skills-index.json`，找到目标 skill 条目，将 `contentHash` 和 `contentVersion` 字段更新为当前值，再用 Edit 工具写回。字段格式：

```json
{
  "path": "meta/publish-skill",
  "bundle": "meta",
  "contentHash": "a3f9c2b14d8e1f07",
  "contentVersion": "1.1.0"
}
```

写回后用 `git add skills-index.json` 将变更纳入暂存区，并输出：

```
✓ contentHash 已更新（v<version>）
  skills-index.json 已暂存，请在本次 commit 中一并提交。
```

---

## 不在范围内

- 修复 skill 内容（只检查结构和注册，不评审 skill 内容质量）
- 自动 push 或创建 PR
- 检查 hooks 注册（hooks 有独立字段，不走 skills[] 路径）
