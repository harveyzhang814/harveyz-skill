# `check` 报告格式

`/init-project check` 跑完 SKILL.md 的 `## 探测` 三项后输出本格式，**不写任何文件、
不装任何 skill、不调任何 init 相位、不问任何问题**——包括 `ask_first`，
它只报告「这条相位有 `ask_first`，执行时会先问你」。

## 输出

开头一行说明用了哪套模板和查的哪个目录：

```
模板 code，检查 /Users/x/Projects/foo
```

然后三张表。每张表**只列有差距的行**；整张表无差距则整表略去，在结尾汇总里说明。

### 骨架

| 文件 / 目录 | 状态 |
|---|---|
| `TODO.md` | 缺失 |
| `.gitignore` | 存在，缺 2 行：`.hskill/*/state.json`、`.hskill/sync-design/html/` |

### skill

| skill | 状态 |
|---|---|
| `handoff` | 两级都没装 |
| `capture-vocab` | 两级都没装 |

已在全局的不列进表，在表下用一行汇总：`已在全局、跳过：init-workflow、clean-git、…`。
其中处于 `update` 状态的（全局装了旧版）额外点名，并附一句
`需要时跑 hskill outdated 自行决定是否升级`——本 skill 不升级任何已装 skill。

### 初始化相位

| 相位 | 状态 |
|---|---|
| `init-workflow` | 无 probe，执行时总会跑一遍（它自己有差量检测） |
| `release-project` | 未跑过；执行时会先问「这个项目要发版吗？」 |

## 结尾

一行汇总 + 下一步命令：

```
骨架缺 1 项，skill 缺 2 个，初始化相位待跑 2 条。
执行：/init-project <路径>
```

三项全无差距时，只输出一行：

```
模板 code，检查 /Users/x/Projects/foo —— 无差距。
```
