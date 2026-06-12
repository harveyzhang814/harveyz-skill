---
name: npm-release
description: "Complete npm publish workflow for harveyz-skill: bump version, update CHANGELOG, create release branch, merge to staging then main, tag, and publish to npm. Use this skill whenever the user wants to release, publish, cut a version, bump version, ship to npm, or deploy a new package version."
user_invocable: true
version: "1.2.0"
---

# npm-release

harveyz-skill 发布到 npm 的完整流程：版本号升级 → CHANGELOG 更新 → 分支提交 → 本地合并到 staging 和 main → 打 tag → 给出推送 + 发布指令供用户执行。

**说明**：所有 `git push` 和 `npm publish` 操作由用户自行执行，Claude 只做本地操作，最后统一给出指令清单。

---

## 前置条件

在开始之前先做以下检查，发现问题立即停下来告知用户：

```bash
# 1. 确认在 staging 分支（发版从 staging 开始）
git branch --show-current

# 2. 确认没有未提交的改动
git status --porcelain

# 3. 确认本地 staging 和远端同步
git fetch origin staging
git rev-list --count HEAD..origin/staging   # 应为 0

# 4. 确认测试通过
npm test
```

如果有未提交改动 → 告知用户先处理；如果测试失败 → 停止，展示失败信息。

---

## Step 1 — 确定版本号

先展示当前版本和 [Unreleased] 改动摘要：

```bash
node -e "console.log(require('./package.json').version)"
# 摘取 CHANGELOG.md 中 ## [Unreleased] 下的内容
awk '/^## \[Unreleased\]/{f=1;next} /^## \[/{f=0} f{print}' CHANGELOG.md | head -30
```

根据 [Unreleased] 内容建议升级类型，然后**询问用户**确认：

| 类型 | 适用情况 |
|------|---------|
| patch | 只有 bugfix / docs / chore |
| minor | 新增功能，向后兼容 |
| major | 有 Breaking Change |

等用户确认后，计算新版本号（当前版本 + 升级类型）。

---

## Step 2 — 更新 CHANGELOG

编辑 `CHANGELOG.md`，将 `## [Unreleased]` 节改为新版本节，同时在它上方保留空的 Unreleased 节：

**改动前（示例）：**
```markdown
## [Unreleased]

### Added
- 新功能 X

## [0.9.0] - 2026-05-29
```

**改动后（示例，假设新版为 0.10.0，今天为 2026-06-08）：**
```markdown
## [Unreleased]

## [0.10.0] - 2026-06-08

### Added
- 新功能 X

## [0.9.0] - 2026-05-29
```

日期用 `date +%Y-%m-%d` 获取当前日期。

---

## Step 3 — 更新 package.json

直接用 `npm version` 修改版本号（不打 tag，tag 在 Step 6 手动打）：

```bash
npm version <new-version> --no-git-tag-version
```

确认 `package.json` 中 `"version"` 已更新为新版本号。

---

## Step 3.5 — 同步 .npmignore 和 package.json files 字段

运行生成脚本，确保 `.npmignore` 和 `package.json` 中的 `files` 字段与当前 `skills-index.json` 保持一致：

```bash
node scripts/generate-npmignore.js
```

检查输出有无报错。此步骤必须在提交前完成，否则新增或重命名的 skill 路径不会被正确包含/排除。

---

## Step 4 — 创建 release 分支并提交

```bash
# 从当前 staging 切出 release 分支
git checkout -b release/<new-version>

# 提交 CHANGELOG、package.json、package-lock.json 和 .npmignore
git add CHANGELOG.md package.json package-lock.json .npmignore
git commit -m "chore(release): bump version to <new-version>"
```

---

## Step 5 — 本地合并到 staging（不推送）

```bash
git checkout staging
git merge release/<new-version>
```

只做本地合并，不执行 push。

---

## Step 6 — 本地合并到 main 并打 tag（不推送）

```bash
git checkout main
git pull origin main          # 只拉取，确保本地 main 是最新的
git merge staging
git tag -a v<new-version> -m "v<new-version>"
```

tag 使用 annotated tag（`-a`），符合项目 workflow-config.yml 的 `require_annotated: true` 规则。

**不执行任何 push**，推送操作统一在最后由用户执行。

---

## Step 7 — 给出最终执行清单

本地准备工作已完成。向用户展示以下指令，请用户依次确认并手动执行：

---

```
== 待执行：推送 + 发布 ==

# 1. 推送 staging
git push origin staging

# 2. 推送 main 和 tag
git push origin main
git push origin v<new-version>

# 3. 发布到 npm（需要已登录：npm login）
npm publish
```

---

说明：
- 如果 `npm login` 状态已过期，先运行 `npm login` 再执行 `npm publish`
- 如果 `git push origin main` 被 pre-push hook 拒绝，检查 tag 格式是否为 `v<X>.<Y>.<Z>`，以及是否是 annotated tag
- 以上命令需在项目根目录执行

用户执行完毕后，告知 Claude，Claude 会输出最终摘要。

---

## Step 8 — 收尾（用户执行完毕后）

用户确认推送和发布成功后输出摘要：

```
✓ 版本 v<new-version> 已发布

  package.json  <old-version> → <new-version>
  CHANGELOG     [Unreleased] → [<new-version>] - <date>
  Git tag       v<new-version>（已推送）
  npm           https://www.npmjs.com/package/harveyz-skill/v/<new-version>
  分支          staging ✓  main ✓
```

可选：询问用户是否删除 release 分支（本地 + 远端）：

```bash
git branch -d release/<new-version>
git push origin --delete release/<new-version>  # 若已推送
```

---

## 常见问题

**`npm publish` 提示 403**：token 过期，运行 `npm login` 后重试。

**`git push` 被 pre-push hook 拒绝**：检查 tag 格式是否符合 `v<X>.<Y>.<Z>`，annotated tag 是必须的。

**[Unreleased] 为空**：没有新内容也能发版（通常是 patch），告知用户确认后继续。
