# 如何将外部 skill 贡献进 harveyz-skill

将你在其他项目中开发的 skill，通过 `contribute-skill` 元技能一键迁移进 harveyz-skill 仓库，自动完成格式规范化、注册登记和双向同步。

---

## 前提条件

- 当前在**源项目**的 Claude 会话中（即 skill 所在的项目）
- 源 skill 目录存在且包含 `SKILL.md`
- 本地有 harveyz-skill 仓库的克隆（首次运行时 skill 会自动查找或询问路径）

---

## 触发方式

在源项目中对 Claude 说：

```
把这个 skill 贡献到 harveyz-skill
把 .claude/skills/my-deploy 导入到 harveyz-skill
将这个 skill 注册进 harveyz-skill 仓库
```

---

## 执行流程（用户视角）

1. **确认源 skill** — skill 从对话上下文推断，或列出候选供选择
2. **定位 harveyz-skill** — 自动查找本地仓库路径；首次使用时询问并缓存
3. **确认目标名称** — 从 `SKILL.md` 的 `name:` 读取，可修改
4. **选择 bundle** — 从现有 bundle 中选择，或新建
5. **预览摘要** — 展示所有操作（复制路径、注册条目、同步方向），**等待确认**
6. **格式规范化** — 自动修复 `version`、`user_invocable` 等字段；`description` 若需重写会展示 diff 确认
7. **复制 + 注册** — 将 skill 复制到 harveyz-skill，更新 `skills-index.json`，运行生成脚本
8. **同步回源** — 将格式化后的内容同步回源项目（无变化则跳过）
9. **创建分支 + commit** — 在 harveyz-skill 自动创建 `feature/contribute-<name>` 分支并提交

---

## 首次运行后

harveyz-skill 路径缓存在 `~/.claude/skills/contribute-skill/.config`，后续调用无需再次输入。路径失效时会自动清除并重新查找。

---

## 完成后的下一步

```bash
cd <harveyz-skill 路径>
git push origin feature/contribute-<skill-name>
# 然后在 GitHub 创建 PR → staging
```

---

## 不在此范围内

- 批量贡献多个 skill（每次只处理一个）
- 自动 push 或创建 PR
- 删除或更新已贡献的 skill
