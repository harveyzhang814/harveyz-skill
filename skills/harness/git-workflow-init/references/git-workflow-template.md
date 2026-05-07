# Git 工作流规范

本文档定义此项目的分支管理规则与开发协作约定。

> 本文档由 `git-workflow-init` 根据 `workflow-config.yml` 自动生成，请勿手动编辑。
> 如需修改规则，请更新 `workflow-config.yml` 后重新运行 `/git-workflow-init`。

---

## 分支模型

```
{{BRANCH_TOPOLOGY_ASCII}}
```

{{BRANCH_TABLE}}

---

## 分支保护规则

以下规则由 `.githooks/pre-commit` 自动强制执行：

{{PROTECTION_RULES}}

提交被拒绝时，请检查当前所在分支，改用正确的合并流程操作。

---

## 标准开发流程

### 开始新工作

```bash
# 始终从集成分支拉取
{{WORKFLOW_CHECKOUT_EXAMPLE}}
git pull
git checkout -b feature/my-feature
```

### 合并到集成分支

```bash
{{WORKFLOW_MERGE_EXAMPLE}}
git push
```

### 发布到主分支

```bash
{{WORKFLOW_RELEASE_EXAMPLE}}
```

---

## 分支命名规范

{{NAMING_TABLE}}

使用 kebab-case，名称简短且有描述性。豁免分支（{{NAMING_EXEMPT}}）不受命名规范约束。

---

## 提交信息格式

{{COMMIT_FORMAT_SECTION}}

---

## Hooks 安装说明

git hooks 通过 `.githooks/` 目录管理（已纳入版本控制），并设置 `core.hooksPath = .githooks`。

新克隆仓库后需手动激活：

```bash
git config core.hooksPath .githooks
```

或通过 Claude Code 重新运行安装 skill：

```
/git-workflow-init
```

---

## 常见问题

{{FAQ_SECTION}}

**Q：能绕过 hooks 吗？**
A：可以用 `git commit --no-verify`，但请记录原因并告知团队。hooks 存在有其意义，请谨慎绕过。
