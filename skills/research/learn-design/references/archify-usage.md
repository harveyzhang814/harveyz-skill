# archify 在 learn-design 中的用法

提炼自 archify 3.0.1（tt-a1i/archify）的 `references/authoring-defaults.md`、`authoring-contract.md` 与实测校验失败。只覆盖本 skill 用到的部分；schema 与示例仍从 `ARCHIFY` 读，它们是校验器的依据。archify 升级后若校验失败明显增多，重读上述原文并更新本文件。

## 选类型

| 章节要讲的 | 类型 | schema（另加 `schemas/common.schema.json`） | 示例 |
|---|---|---|---|
| 部件、信任与边界 | `architecture` | `schemas/architecture.schema.json` | `examples/web-app.architecture.json` |
| 多方之间谁先谁后、谁等谁 | `sequence` | `schemas/sequence.schema.json` | `examples/cache-miss-request.sequence.json` |
| 单方的步骤、分支、闸门 | `workflow` | `schemas/workflow.schema.json` | `examples/agent-tool-call.workflow.json` |
| 状态与迁移、终态、回退 | `lifecycle` | `schemas/lifecycle.schema.json` | `examples/deployment-release.lifecycle.json` |
| 数据或产物的来去与归属 | `dataflow` | `schemas/dataflow.schema.json` | `examples/product-analytics.dataflow.json` |

## 固定约定

- `meta.locale: "zh-CN"`，`meta.quality_profile: "showcase"`，`meta.output: "diagrams/<id>.html"`，`meta.title` 写图契约里那个问题。
- 不写 `cards`、`meta.subtitle`、`meta.visual_preset`、`meta.animation`；`meta.legend` 省略即自动。示例里都带 `cards`，不要照抄。
- `workflow` 与 `lifecycle` 用 schema v2；`architecture` 与 `lifecycle` 省略 `meta.viewBox`，由渲染器量高度。
- 示例只示范字段形状，不示范取值与事实。

## 写坐标之前

**architecture**——先按关系定位置，再给坐标；路由器不会挪框：

- 主路径上的相邻步骤相邻摆放，可跨行推进，不要压成一条浅横带。
- 分支或存储放在拥有它的节点正上方或正下方并居中，让连线是一段直线；同一行的分支放同一侧。
- 回到前面节点的连线，起点放在主路径没有分支的那一侧。
- 一侧有 k 条连线时，这一侧至少需要 `32 + 14 × (k − 1)` px；挤不下就分到两三侧，或把节点放大。
- 主路径上带标签的连线，两端空隙至少 `6.5 × 字符单位 + 21` px，副标签宽度按 `5.4 × 字符单位 + 8` px；汉字算 2 个单位。
- 先用自动走线；`via`、`channelX`、`channelY` 只用来修校验报出的问题。

**sequence**——参与者按对话角色排序；消息按 `y` 定先后。共享水平区间的两条消息 `y` 至少相差 28 px；`y` 要落在校验报告给出的时间轴范围内。先用固定列，标签放不下时设 `meta.column_fit: "spread"`。

**lifecycle（v2）**——每个 lane 一行，`main` 在最上、`terminal` 在最下；`col` 取 0–4，所有行共用一套列。中断或退出放在它离开的那个状态的同一列，迁移就是竖直直线。所有迁移都要写出来（包括主路径）；标签要短；可恢复的失败要有一条真实的回到活动状态的迁移。

**dataflow**——阶段表示加工或保管权的变化，行表示并行的数据流；只给数据契约、分类或跨边界移动加标签。

**可读性**——画布按 1440 px 宽的桌面视口缩放，投影后的字小于 6 px 即失败（宜在 7.5 px 以上）。图太宽或太高时，先删节点或拆图，不要缩字。

## 常见校验失败与修法

| 代码 | 含义 | 修法 |
|---|---|---|
| `layout/constraint`（sequence） | 两条消息相距不足 28 px，或 `y` 超出可读时间轴 | 拉开 `y`；按报告给的范围收拢；仍放不下就加大 `meta.viewBox` 高度 |
| `composition/viewport-height` | 画布宽高比不够宽，渲染后超出 900 px 视口 | 压缩纵向间距，让高度不超过报告给的数；或加宽到报告给的宽度；architecture 直接省略 `viewBox` |
| `composition/desktop-readability` | 画布太宽，缩放后字小于 6 px | 减少列数或节点，必要时拆图；不缩字 |
| `composition/micro-segment` / `composition/short-interior-segment` | 折线中有短于 8 px 的段或短于 16 px 的内段 | 挪节点让两端对齐成直线；或用 `via`／`channelX`／`channelY`（architecture 只有 `via`）让转弯走在空走廊里 |
| `composition/label-route-clearance` | 标签贴到了别的连线 | 调 `labelAt`／`labelDx`／`labelDy`／`labelSegment`；否则改另一条线的走线 |
| `clean-flow/endpoint-side-direction` | 末段没有垂直进入 `toSide` 指定的那条边 | 去掉显式 `fromSide`／`toSide` 用自动走线；或加 `via` 让首末段垂直穿过节点边 |

表里没有的失败，先按 finalize 输出中的 `supportedFixes` 修；仍不够，再读 `ARCHIFY/references/authoring-contract.md` 的对应小节。
