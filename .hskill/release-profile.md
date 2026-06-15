# Release Profile
<!-- 由 project-release skill Init 阶段生成，可随时手动编辑 -->
<!-- 生成时间：2026-06-15 -->

## 分支模型

发版起点：`staging` 分支（必须与远端同步）

合并流向：
```
staging → release/<version> → staging → main
```

1. 从 `staging` 切出 `release/<version>` 分支，提交版本文件改动
2. 本地合并回 `staging`
3. 本地合并到 `main`，在 `main` 上打 tag
4. 所有推送由用户手动执行

保护分支：`main`、`staging`（不能直接提交）

## 版本文件

按以下顺序更新：

1. **CHANGELOG.md** — 手动编辑：将 `## [Unreleased]` 节改为 `## [<version>] - <date>`，在其上方保留空的 `## [Unreleased]` 节
2. **package.json + package-lock.json** — 运行命令（不打 tag）：
   ```bash
   npm version <version> --no-git-tag-version
   ```
3. **.npmignore** — 运行生成脚本（同步 skills-index.json 的最新状态）：
   ```bash
   node scripts/generate-npmignore.js
   ```

提交时包含以上全部文件：
```bash
git add CHANGELOG.md package.json package-lock.json .npmignore
git commit -m "chore(release): bump version to <version>"
```

**主版本声明文件**：`package.json`（`version` 字段）——这是读取当前版本号的唯一来源。

## 发布方式

由用户手动执行，Claude 只做本地操作：

```bash
# 推送分支和 tag
git push origin staging
git push origin main
git push origin v<version>

# 发布到 npm（需已登录）
npm publish
```

如 `npm login` 状态过期，先执行 `npm login` 再发布。

## 特殊规则

- **前置检查**：必须在 `staging` 分支、无未提交改动、与远端同步、`npm test` 通过
- **合并到 main 前先拉取**：`git pull origin main`，确保本地 main 是最新的，再执行 `git merge staging`
- **Tag 格式**：`v<X.Y.Z>`，必须为 annotated tag（`git tag -a`），由 `workflow-config.yml` 的 `require_annotated: true` 要求
- **commit message 格式**：`chore(release): bump version to <version>`
- **release 分支命名**：`release/<version>`（如 `release/1.3.0`）
