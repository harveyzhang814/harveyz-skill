# 如何使用 init-goal：为 /loop 生成结构化目标

`init-goal` 通过对话收集你的目标、步骤和退出条件，生成一个 `prompt.md` 文件，供 `/loop` 命令驱动。

---

## 什么时候用

当你想用 `/loop` 持续完成某个目标，但不确定怎么写 prompt，或需要结构化的进度追踪时。典型触发：

- "帮我初始化一个 loop 目标"
- "我要用 loop 持续修 bug 直到测试全通过"
- "设定一个 loop，让 Claude 反复搜索直到找到足够信息"

---

## 快速开始

```
/init-goal
```

skill 会展示内置模版菜单（见下方），选一个或从零开始。完成后输出：

```
/loop <你选择的间隔> $(cat ~/.hskill/init-goal/<goal-slug>/prompt.md)
```

复制运行即可启动 loop。

---

## 内置模版

| # | 模版 | 适用场景 |
|---|------|---------|
| 1 | **Fix Until Green** | 持续修 bug 直到测试全通过 |
| 2 | **Research Loop** | 反复搜索直到信息足够 |
| 3 | **Refine Until Satisfied** | 迭代优化某个输出 |
| 4 | **Monitor & React** | 持续监控状态并响应变化 |
| 5 | **Explore & Map** | 系统性探索未知领域/代码库 |

选择模版后只需补充空缺字段；不选模版则逐步填写全部字段。

---

## 生成的文件

```
~/.hskill/init-goal/<goal-slug>/
├── prompt.md     # 初始 prompt（静态，手动编辑才变）
├── log.md        # loop 运行日志（每轮自动追加）
└── summary.md    # 总结（loop 退出时生成）
```

`goal-slug` 由 skill 从目标文本自动生成（如 `fix-auth-tests`）。

### prompt.md 结构

```markdown
## GOal
<目标描述，含成功标准>

## 每轮执行
<每轮具体步骤列表>

## 评估（每轮末尾）
<判断进展的方式>

## 约束
<不能做什么，或"无">

## 退出条件
- 明确条件：<停止状态>
- 兜底逻辑：<无法判断时的行为>
```

### 修改目标

直接编辑 `prompt.md` 后重启 loop 即可，无需重新运行 init-goal。

---

## 不在此 skill 范围内

- `log.md` 和 `summary.md` 的写入——由 loop 运行时的 Claude 负责
- loop 间隔选择——用户自决（`/loop 5m`、`/loop 30s` 等）
- loop 运行中的监控或中断——属于 `/loop` 内置行为
