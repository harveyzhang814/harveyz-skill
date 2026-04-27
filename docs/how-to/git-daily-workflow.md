# 如何使用 Git 分支工作流

> 分支规则和定义见 [reference/git-branch-rules.md](../reference/git-branch-rules.md)

---

## 安装分支保护 Hook

在项目根目录执行一次即可：

```bash
bash scripts/git/install-git-hooks.sh
```

Hook 安装后，`core.hooksPath` 会被设置为 `.githooks`，pre-commit 检查自动生效。

---

## 日常开发

```bash
# 1. 从 staging 切出工作分支
git checkout staging
git pull
git checkout -b feature/my-feature

# 2. 在工作分支上开发、提交
git add .
git commit -m "feat: add my feature"

# 3. 合并回 staging
git checkout staging
git merge feature/my-feature

# 4. 删除工作分支（可选）
git branch -d feature/my-feature
```

---

## 发布到 main

```bash
# 从 staging 合并到 main
git checkout main
git merge staging
```
