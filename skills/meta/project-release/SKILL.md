---
name: project-release
description: "跨项目通用版本发布 skill。当用户说「发布」「release」「发版」「bump version」「切版本」「上线新版本」时必须使用。分两个阶段：Init（首次使用，扫描项目分支结构和版本文件，生成 .claude/release-profile.md）；Execute（日常使用，读取 profile 走完整发布流程）。适用于 npm、Python、Rust、或任何有版本号的项目。"
user_invocable: true
version: "1.0.0"
---

# project-release

通用项目发布 skill，两个阶段：

- **Init** — 扫描项目，生成 `.claude/release-profile.md`（每个项目一次）
- **Execute** — 读取 profile，走完整发布流程

---

## 入口判断

首先检查 `.hskill/release-profile.md` 是否存在：

```bash
ls .hskill/release-profile.md 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

- **NOT_FOUND** → 执行 [Init 阶段](#init-阶段)
- **EXISTS** → 跳到 [Execute 阶段](#execute-阶段)
- 用户明确说「重新初始化」→ 执行 Init 阶段（会覆盖旧 profile）

---

## Init 阶段

目标：搞清楚这个项目的发布规则，保存成 profile，之后每次发版直接用。

### Step I-1 — 扫描分支拓扑

依次尝试以下来源（找到即止）：

1. 读 `workflow-config.yml`（如果存在）
2. 读 `CLAUDE.md` / `AGENTS.md`（搜索 git flow / branch 相关段落）
3. 分析 git 历史推断：

```bash
# 常见分支
git branch -a | grep -E '(main|master|staging|develop|release)'

# 看最近的 merge commit 来推断合并流向
git log --merges --oneline -20
```

根据以上信息判断分支模型：

| 模型 | 特征 | 典型流向 |
|------|------|---------|
| GitHub Flow | 只有 main + feature | feature → main |
| Git Flow | main + develop + feature/release | feature → develop → release → main |
| 三层（此项目） | main + staging + feature | feature → staging → main |
| Trunk | 只有 main/trunk | 直接提交 main |

不确定时询问用户。

### Step I-2 — 扫描版本文件

在项目根目录逐一检测以下文件，记录所有匹配项：

```bash
# 以下文件按优先级扫描
files_to_check=(
  "package.json"           # Node: "version": "x.y.z"
  "package-lock.json"      # Node lock: "version": "x.y.z"
  "pyproject.toml"         # Python: version = "x.y.z"
  "Cargo.toml"             # Rust: version = "x.y.z"
  "setup.py"               # Python old: version='x.y.z'
  "setup.cfg"              # Python old: version = x.y.z
  "build.gradle"           # Java/Kotlin: version = 'x.y.z'
  "build.gradle.kts"       # Kotlin: version = "x.y.z"
  "pom.xml"                # Maven: <version>x.y.z</version>
  "pubspec.yaml"           # Dart/Flutter: version: x.y.z
  "VERSION"                # 纯文本版本文件
  "version.txt"            # 纯文本版本文件
  "CHANGELOG.md"           # 几乎所有项目都有
  "CHANGELOG.rst"          # Python 项目常见
)
```

对每个存在的文件，识别版本号所在的具体位置（字段名/行模式），方便 Execute 阶段精准更新。

也检查有无自定义版本文件：

```bash
# 搜索含版本号模式的其他文件（排除 node_modules / .git）
grep -rl '"version":\|^version\s*=\|^version:\s' \
  --include="*.json" --include="*.toml" --include="*.yaml" --include="*.yml" \
  --exclude-dir=node_modules --exclude-dir=.git . 2>/dev/null | head -20
```

找到不在列表里的文件时，询问用户是否纳入 profile。

### Step I-3 — 检测发布方式

询问或检测项目的分发方式：

```bash
# 检测常见发布工具
[ -f "package.json" ] && cat package.json | grep '"private"' && echo "private npm"
[ -f "package.json" ] && echo "npm publish"
[ -f "pyproject.toml" ] && grep -q 'build-backend' pyproject.toml && echo "python build"
[ -f "Cargo.toml" ] && echo "cargo publish"
[ -f ".github/workflows" ] && ls .github/workflows/  # CI/CD 自动发布？
```

发布方式影响 Execute 阶段最后给出的指令清单。

### Step I-4 — 生成 release-profile.md

确认所有信息后，读取 `references/release-profile-template.md` 作为模板，将 `{占位符}` 替换为实际扫描结果，写入项目的 `.hskill/release-profile.md`：

```bash
mkdir -p .hskill
# 基于模板生成，替换所有 {占位符} 字段
```

**模板文件**：`references/release-profile-template.md`（随 skill 一起安装）

以模板为骨架，把 Init 扫描和询问到的信息填进去。模板只规定了四个顶级节，每节怎么写完全由项目决定——简短几行或详细表格都行，不需要对齐固定格式。`{YYYY-MM-DD}` 替换为今天日期，没有特殊规则就删掉那节。

生成后告诉用户：「已创建 `.hskill/release-profile.md`，可以手动调整。下次说『发版』时直接读这个文件执行。」

---

## Execute 阶段

读取 `.hskill/release-profile.md`，按其中的分支模型和版本文件清单执行。

### Step E-0 — 前置检查

```bash
# 读取发版起点分支（通常是 staging）
RELEASE_BASE=$(grep "发版起点" .hskill/release-profile.md | head -1)

# 1. 确认在正确的起点分支
git branch --show-current

# 2. 无未提交改动
git status --porcelain

# 3. 与远端同步
git fetch origin
git rev-list --count HEAD..origin/$(git branch --show-current)  # 应为 0
```

有问题立即停下告知用户，等用户处理后再继续。

### Step E-1 — 确定新版本号

展示当前版本和 `[Unreleased]` 变更摘要：

```bash
# 当前版本（从 profile 中第一个版本文件读取）
# 例如 package.json:
node -e "console.log(require('./package.json').version)" 2>/dev/null \
  || grep '^version' pyproject.toml | head -1 \
  || grep '^version' Cargo.toml | head -1 \
  || cat VERSION 2>/dev/null

# CHANGELOG [Unreleased] 内容
awk '/^## \[Unreleased\]/{f=1;next} /^## \[/{f=0} f{print}' CHANGELOG.md 2>/dev/null | head -30
```

根据变更内容建议升级类型并询问用户确认：

| 类型 | 适用情况 |
|------|---------|
| patch (x.y.**Z**) | 只有 bugfix / docs / chore |
| minor (x.**Y**.0) | 新功能，向后兼容 |
| major (**X**.0.0) | Breaking Change |

等用户确认后确定 NEW_VERSION。

### Step E-2 — 更新 CHANGELOG

将 `## [Unreleased]` 节重命名为 `## [NEW_VERSION] - DATE`，并在它上方保留空的 Unreleased 节：

```bash
TODAY=$(date +%Y-%m-%d)
```

```markdown
<!-- 改动前 -->
## [Unreleased]

### Added
- 新功能

## [0.9.0] - 2026-05-01

<!-- 改动后 -->
## [Unreleased]

## [NEW_VERSION] - TODAY

### Added
- 新功能

## [0.9.0] - 2026-05-01
```

### Step E-3 — 更新所有版本文件

按 `.claude/release-profile.md` 中的清单逐一更新，每个文件用对应的方式：

**package.json**（npm 项目）:
```bash
npm version NEW_VERSION --no-git-tag-version
# package.json 和 package-lock.json 同时更新
```

**pyproject.toml**:
```bash
# 用 sed 精确替换 version 行
sed -i '' 's/^version = ".*"/version = "NEW_VERSION"/' pyproject.toml
```

**Cargo.toml**:
```bash
sed -i '' 's/^version = ".*"/version = "NEW_VERSION"/' Cargo.toml
```

**VERSION / version.txt**:
```bash
echo "NEW_VERSION" > VERSION
```

执行 profile 中的任何「特殊规则」步骤（例如 `node scripts/generate-npmignore.js`）。

### Step E-4 — 创建 release 分支并提交

```bash
# 从发版起点切出 release 分支
git checkout -b release/NEW_VERSION

# 提交所有版本文件
git add <profile 中列出的所有版本文件>
git commit -m "chore(release): bump version to NEW_VERSION"
```

### Step E-5 — 按分支模型执行本地合并

根据 profile 中的分支流向，逐步本地合并：

**三层模型**（staging → main）:
```bash
git checkout staging && git merge release/NEW_VERSION
git checkout main && git merge staging
git tag -a vNEW_VERSION -m "vNEW_VERSION"
```

**GitHub Flow**（直接 main）:
```bash
git checkout main && git merge release/NEW_VERSION
git tag -a vNEW_VERSION -m "vNEW_VERSION"
```

**Git Flow**（develop → main）:
```bash
git checkout develop && git merge release/NEW_VERSION
git checkout main && git merge develop
git tag -a vNEW_VERSION -m "vNEW_VERSION"
```

所有合并只在本地做，不推送。

### Step E-6 — 输出待执行清单

```
== 本地已完成，待用户手动执行 ==

# 推送分支
git push origin staging    # 如适用
git push origin main
git push origin vNEW_VERSION

# 发布（按项目类型）
{npm publish / cargo publish / python -m build && twine upload / 其他}
```

### Step E-7 — 发布后收尾

用户确认推送成功后输出摘要：

```
✓ vNEW_VERSION 已发布

  版本文件   OLD_VERSION → NEW_VERSION
  CHANGELOG  [Unreleased] → [NEW_VERSION] - DATE
  Git tag    vNEW_VERSION（已推送）
  分支       {按模型列出已推送分支}
```

可选：询问是否清理 release 分支：
```bash
git branch -d release/NEW_VERSION
git push origin --delete release/NEW_VERSION  # 如已推送
```

---

## 常见问题

**profile 信息有误** — 直接编辑 `.hskill/release-profile.md` 后告诉 Claude「已更新 profile」重新开始。

**`git push` 被 hook 拒绝** — 检查 tag 是否为 annotated tag（`-a`），以及 tag 格式是否符合项目规范。

**版本文件漏更新** — 执行 E-3 后用 `git diff` 检查，确认所有文件均已更新再提交。

**[Unreleased] 为空** — 没有新内容也能发版（通常是 patch），询问用户确认后继续。
