# Git 工作流规范

本文档定义此项目的分支管理规则与开发协作约定。

> 本文档由 `init-workflow` 根据 `workflow-config.yml` 自动生成，自填区以外请勿手动编辑。
> 如需修改规则，请更新 `workflow-config.yml` 后重新运行 `/init-workflow`；项目自己的补充写在文末的项目自填区内，重新生成时原样保留。

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

{{WORKFLOW_START_SECTION}}

### 合并到集成分支

{{WORKFLOW_MERGE_SECTION}}

### 发布到主分支

{{WORKFLOW_RELEASE_SECTION}}

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
git config merge.ff false   # 禁止 fast-forward，确保 merge commit 可被钩子审查
```

或通过 Claude Code 重新运行安装 skill：

```
/init-workflow
```

---

## 常见问题

{{FAQ_SECTION}}

**Q：能绕过 hooks 吗？**
A：可以用 `git commit --no-verify`，但请记录原因并告知团队。hooks 存在有其意义，请谨慎绕过。

---

## 项目自填区

下方标记之间由项目自行维护，重新生成本文档时原样保留。

<!-- BEGIN PROJECT NOTES -->
<!-- END PROJECT NOTES -->
