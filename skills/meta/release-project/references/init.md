# Init 阶段

目标：把这个项目的发布规则搞清楚，写进 profile，之后每次发版直接读。**宁可问多几个问题，也不要猜错。**

### Step I-1 — 扫描分支拓扑

依次从以下来源收集信息：

1. 项目配置文件：`.hskill/init-workflow/workflow-config.yml`、`CLAUDE.md`、`AGENTS.md`、`CONTRIBUTING.md`
2. git 历史和现有分支：

```bash
git branch -a
git log --merges --oneline -20
```

整理出：**发版起点分支**（从哪个分支开始操作）、**合并流向**（依次合并到哪些分支）、**保护分支**（不能直接提交的分支）。

分支模型用自然语言描述，不必套固定模型名。

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

最终形成一个**有序清单**：哪些文件、按什么顺序、用什么方式更新。

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

读取 `references/release-profile-template.md` 作为骨架，把 I-1 到 I-4 收集到的信息填进去。I-4 的发版前检查写进「特殊规则」，注明在 E-0 执行。

每节内容和写法（文字、表格、命令）由项目决定；没有特殊规则就删掉该节。

写完后给用户看，确认无误再保存到 `.hskill/release-project/release-profile.md`。告诉用户：**这个文件可以随时手动编辑**，是下次发版的唯一依据。
