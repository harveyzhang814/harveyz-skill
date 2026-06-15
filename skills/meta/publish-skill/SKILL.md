---
name: publish-skill
description: "Validate and publish a skill to the harveyz-skill repository. Checks SKILL.md format compliance (frontmatter fields, semver version, name-directory match) and registration in skills-index.json. Triggers: publish skill, register skill, validate skill format, check skill, add skill to index, is skill ready to publish."
user_invocable: true
version: "1.0.0"
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
  # 转为相对于 skills/ 的路径（格式：category/name）
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
- 是否要把它们注册到 `skills-index.json`（若是，按 Step 5 执行）

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

**F3 英文检测方法：** 提取 `description` 字段值，检查是否包含中文字符（`一-鿿` 范围）。有则报错。

**F6 中文检测方法：** 提取 frontmatter 结束后的正文，检查是否包含至少一个中文字符。若正文全为英文或为空则报错。（纯英文 skill 如从其他项目贡献的可跳过此项，需用户确认。）

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

注册问题
--------
  skills/meta/my-skill
    R1  未在 skills-index.json 中注册

  skills/analysis/another-skill
    R3  bundle 'analytics' 未在 bundleMeta 中声明

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

---

## 不在范围内

- 修复 skill 内容（只检查结构和注册，不评审 skill 内容质量）
- 自动 push 或创建 PR
- 检查 hooks 注册（hooks 有独立字段，不走 skills[] 路径）
