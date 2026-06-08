# hskill config 设计原理

解释 `hskill config` 子命令的背景动机和核心设计决策。

---

## 背景

hskill 目前没有持久化用户偏好的机制，每次调用都需要显式传 `--target` 和 `--scope`。新增 `hskill config` 子命令，允许用户设置默认值，减少重复输入。

---

## 为什么用本地配置文件而非环境变量

选择将配置持久化到 `~/.config/hskill/config.json` 而非环境变量，原因：

- 环境变量在不同 shell session 之间不持久，需要用户在 `.zshrc` 中手动维护
- 配置文件可被版本控制工具检测到并提醒用户，降低遗忘风险
- 多个项目可以有不同的 project-level 配置（`<cwd>/.hskillrc`），环境变量无法做到分层

这一决策的代价是引入了配置文件查找的优先级逻辑：project-level 覆盖 user-level，user-level 覆盖命令行默认值。

---

## 不在范围内

- 配置迁移工具
- 配置加密（配置文件只含偏好，无敏感信息）
