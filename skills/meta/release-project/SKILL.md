---
name: release-project
description: "Universal project release skill. Triggers on: release, bump version, publish, new version, cut release. Two phases: Init (first run — scans project and generates .hskill/release-profile.md); Execute (daily use — reads profile and runs full release flow). Works with npm, Python, Rust, Java, or any versioned project."
user_invocable: true
version: "1.1.0"
---

# project-release

通用项目发布 skill，两个阶段：

- **Init** — 扫描项目，和用户确认，生成 `.hskill/release-profile.md`（每个项目做一次）
- **Execute** — 读取 profile，完全按照它走发布流程

---

## 入口判断

检查 `.hskill/release-profile.md` 是否存在：

```bash
ls .hskill/release-profile.md 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

- **NOT_FOUND** → 执行 Init 阶段
- **EXISTS** → 执行 Execute 阶段
- 用户明确说「重新初始化」→ 执行 Init 阶段（覆盖旧 profile）

---

## Init 阶段

目标：把这个项目的发布规则搞清楚，写进 profile，之后每次发版直接读。**宁可问多几个问题，也不要猜错。**

### Step I-1 — 扫描分支拓扑

依次从以下来源收集信息：

1. 项目配置文件：`workflow-config.yml`、`CLAUDE.md`、`AGENTS.md`、`CONTRIBUTING.md`
2. git 历史和现有分支：

```bash
git branch -a
git log --merges --oneline -20
```

整理出：**发版起点分支**（从哪个分支开始操作）、**合并流向**（依次合并到哪些分支）、**保护分支**（不能直接提交的分支）。

不确定时直接问用户，用自然语言描述即可，不需要套用固定模型名。

### Step I-2 — 扫描版本文件

```bash
# 扫描常见版本文件
for f in package.json pyproject.toml Cargo.toml setup.cfg setup.py \
          build.gradle build.gradle.kts pom.xml pubspec.yaml \
          VERSION version.txt CHANGELOG.md CHANGELOG.rst; do
  [ -f "$f" ] && echo "FOUND: $f"
done

# 补充搜索其他可能含版本号的文件
grep -rl '"version":\|^version\s*[=:]\|<version>' \
  --include="*.json" --include="*.toml" --include="*.yaml" \
  --include="*.yml" --include="*.xml" \
  --exclude-dir=node_modules --exclude-dir=.git \
  --exclude-dir=target --exclude-dir=dist . 2>/dev/null | head -20
```

对找到的每个文件，确认：
- 这个文件需要在发版时更新吗？（有些是 lockfile，由工具自动更新）
- 怎么更新？（工具命令 vs 直接编辑）

有不确定的就问用户。最终形成一个**有序清单**：哪些文件、按什么顺序、用什么方式更新。

### Step I-3 — 检测发布方式

```bash
# CI/CD 配置
ls .github/workflows/ .gitlab-ci.yml .circleci/ 2>/dev/null

# 包管理器信息
[ -f package.json ] && cat package.json | grep -E '"private"|"publishConfig"'
```

询问用户：
- 产物发往哪里（npm / PyPI / crates.io / 内部仓库 / 只打 tag / CI 自动处理）？
- 发布命令是什么？
- 谁来执行（用户手动 / CI 触发）？

### Step I-4 — 询问其他项目惯例

了解这个项目是否有：
- release 分支命名规范（`release/x.y.z` / `release-x.y.z` / 其他）
- commit message 格式要求
- tag 格式（`vX.Y.Z` / `X.Y.Z` / 其他）、是否要求 annotated tag
- 发版前必须通过的检查（测试、lint、构建）
- CHANGELOG 有无、格式如何（Keep a Changelog / 自定义 / 无）

### Step I-5 — 生成 profile

读取 `references/release-profile-template.md` 作为骨架，把 I-1 到 I-4 收集到的信息填进去。

```bash
mkdir -p .hskill
```

模板只提供四个顶级节（分支模型、版本文件、发布方式、特殊规则），每节的具体内容完全由项目决定，用最能清楚表达意图的方式写——几行文字、表格、命令示例均可。没有特殊规则就删掉那节。

写完后给用户看，确认无误再保存。告诉用户：**`.hskill/release-profile.md` 可以随时手动编辑**，是下次发版的唯一依据。

---

## Execute 阶段

**读取 `.hskill/release-profile.md`，完全按照它执行。** profile 是唯一依据，不在 profile 里的事不要自己发明。

### Step E-0 — 读取 profile + 前置检查

先完整读取 profile，理解：发版起点分支是什么、版本文件清单是什么、合并流向是什么、发布命令是什么。

然后按 profile 要求做前置检查，通常包括：

```bash
# 当前分支是否是发版起点
git branch --show-current

# 是否有未提交的改动
git status --porcelain

# 是否与远端同步
git fetch origin
git rev-list --count HEAD..origin/$(git branch --show-current)
```

profile 中有「发版前检查」（如跑测试）就一并执行。有问题立即停下告知用户。

### Step E-1 — 确定新版本号

从 profile 的版本文件清单中第一个「主版本声明文件」读取当前版本。

如果项目有 CHANGELOG，展示其中 Unreleased 部分的内容；没有则询问用户本次改动摘要。

根据改动建议 semver 升级类型，等用户确认后确定 NEW_VERSION：

| 类型 | 适用情况 |
|------|---------|
| patch | 只有 bugfix / docs / chore |
| minor | 新功能，向后兼容 |
| major | Breaking Change |

### Step E-2 — 更新 CHANGELOG（如适用）

如果 profile 中记录了 CHANGELOG 文件，按该文件的**现有格式**更新——把本次版本从 Unreleased 区域移动到有版本号的区段，保留一个空的 Unreleased 区域供下次使用。

不同项目格式不同，关键是保持和现有格式一致，不要改变风格。

```bash
TODAY=$(date +%Y-%m-%d)
```

### Step E-3 — 更新版本文件

按 profile 中版本文件清单的顺序，用 profile 里说明的方式逐一更新每个文件。

更新完后用 `git diff` 确认所有文件已正确改动，没有遗漏或多余修改。

### Step E-4 — 执行 profile 中的发版前脚本（如有）

profile「特殊规则」里列出的、需要在提交前执行的脚本或命令，在这里执行。

### Step E-5 — 创建 release 分支并提交

按 profile 中的分支命名规范创建 release 分支，提交所有版本文件改动：

```bash
git checkout -b <profile 中的 release 分支格式，如 release/NEW_VERSION>
git add <profile 中列出的所有版本文件>
git commit -m "<profile 中的 commit message 格式>"
```

### Step E-6 — 按合并流向执行本地合并 + 打 tag

读取 profile 中的合并流向，逐步执行本地合并。在最终目标分支（通常是 main/master）上打 tag：

```bash
git tag <profile 中的 tag 格式，如 vNEW_VERSION 或 NEW_VERSION> -m "<tag message>"
# 若 profile 要求 annotated tag，加 -a 参数
```

所有操作只在本地做，不推送。

### Step E-7 — 输出待执行清单

本地操作完成后，整理出推送和发布指令供用户手动执行：

```
== 本地已完成，待执行 ==

# 推送（按 profile 中的合并流向列出所有需要推送的分支）
git push origin <branch1>
git push origin <branch2>
git push origin <tag>

# 发布
<profile 中的发布命令>
```

### Step E-8 — 收尾

用户确认成功后输出摘要，列出：版本变更（旧 → 新）、CHANGELOG 更新情况、tag、已推送分支、发布目标。

可选：询问是否清理 release 分支（本地 + 远端）。

---

## 常见问题

**profile 信息有误** — 直接编辑 `.hskill/release-profile.md` 后重新触发 Execute。

**发版前检查失败** — 按失败信息修复后，重新从 E-0 开始。

**版本文件漏更新** — E-3 后用 `git diff` 检查，发现遗漏立即补上。

**CHANGELOG 为空或不存在** — 询问用户本次改动内容，或确认跳过 CHANGELOG 更新。
