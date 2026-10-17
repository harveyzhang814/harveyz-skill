# `hskill list --bundle` 设计 Spec

- 当前批准版本：0.1
- 日期：2026-10-17
- 审查状态：已批准；用户已审查并明确批准 Spec 0.1 的完整设计及其中标明的次要实现决定
- 批准范围：`record.md` 的 D-001～D-009、D-011～D-014；D-010 已失效，不进入本 Spec
- 未决事项：无
- 实施状态：仅设计；未修改产品代码

## 意图和范围

用户已经知道一个技能 bundle 的 ID，希望直接查看其中的技能，避免翻阅完整 `hskill list` 或自行处理 `--json` 输出。[D-001、D-002、D-007] 新增 `hskill list --bundle <id>`，支持与 `--json` 组合；一次只筛选一个技能 bundle。[D-005] 筛选结果只包含技能，不展示 shell tools。[D-006]

无 `--bundle` 时，文本输出和 JSON 输出的内容、字段、顺序、格式及现有退出行为保持不变。[D-003] 本任务只交付设计；后续实现范围是 `list` 分支、相应帮助、使用说明和测试，不改变其他命令或 MCP 的现有行为。[D-004、D-012]

不可接受的结果：筛选时混入其他 bundle 的技能或 shell tools；把未知名称误当作空 bundle；把有效空 bundle 误当作错误；无筛选输出回归；JSON 错误污染 stdout。[D-003、D-006、D-008、D-009、D-013]

## 已核实的现状

- `bin/cli.js` 的 `list` 分支直接读取 `skills-index.json` 的 `skills`、`tools`；技能按 bundle ID、再按路径末段名称用 `localeCompare` 排序。文本显示 `NAME`、`BUNDLE` 两列与独立 `SHELL TOOLS` 区块；JSON 是 `{skills, tools}`，每项技能有 `name`、`path`、`bundle`、`global`（缺省为 `false`）。
- `skills-index.json` 用 `bundleMeta` 登记技能 bundle ID，用 `toolBundleMeta` 登记工具 bundle ID；技能归属由 `skills[].bundle` 指定。[D-013、D-014]
- 现有 `list` 不解析 `--bundle`，因此传入该参数目前仍返回完整列表。`lib/bundles.js` 的 `resolveSkills()` 面向安装、会读取版本，并在无技能的名称上报错，不适合直接复用为此查询。[D-012]
- `tests/agent-cli.bats` 已验证 `list --json` 可解析；`docs/reference/agent-cli-guide.md` 的 `list --json` 示例与当前 CLI 实际输出不一致。后续修改该文档的 `list` 小节时应按现有 `{skills, tools}` 契约修正示例。[D-012]

## 用户可见行为

| 调用或条件 | 结果 | 退出与输出位置 |
|---|---|---|
| `hskill list`、`hskill list --json` | 完全沿用当前未筛选输出，包括工具列表与现有顺序 | 与当前一致 [D-003] |
| `hskill list --bundle research` | 只显示 `research` 技能；沿用 `NAME / BUNDLE` 表头、分隔线和排序，不显示 `SHELL TOOLS` | 退出 0，文本写 stdout [D-001、D-006、D-011] |
| `hskill list --bundle research --json` | `{ "skills": [仅 research 的现有技能对象], "tools": [] }`；技能对象字段及排序沿用当前 `list --json` | 退出 0，单个 JSON 对象写 stdout [D-002、D-008、D-011] |
| ID 在 `bundleMeta` 中，但该 ID 当前无技能 | 文本只显示双列表头与分隔线，没有数据行或工具区块；JSON 为结构上的 `{"skills":[],"tools":[]}` | 退出 0 [D-011、D-013、D-014] |
| ID 不在 `bundleMeta` 中，包括 `all`、工具 bundle ID、大小写不符 | 说明未知技能 bundle；不输出技能或工具列表 | 非零退出；`--json` 时 stderr 有错误且 stdout 为空 [D-009、D-014] |
| `--bundle` 后缺值，包括紧接 `--json` | 说明缺少 bundle ID；不输出技能或工具列表 | 非零退出；`--json` 时 stderr 有错误且 stdout 为空 [D-009] |

筛选以 `bundleMeta` 自有键判定 ID 是否有效，再以 `skills[].bundle === id` 选成员。匹配区分大小写；不对 ID 做模糊匹配、别名展开或把 `all` 视为技能 bundle。[D-013、D-014] 一个 ID 即使没有当前成员，也依然有效。技能 JSON 对象保持当前字段、字段值和排序；`tools` 字段保留但为空数组。[D-008]

## 实现方案与约束

选定方案是在 `bin/cli.js` 的 `list` 分支内解析 `--bundle`，使用同一次读取的 `skills-index.json` 元数据做验证与过滤，然后进入现有排序和文本/JSON 渲染路径。[D-012] 对无筛选分支保持原来的数据和渲染路径，避免改动现有输出。[D-003] 筛选文本使用相同的列标题、分隔线和排序；当技能数组为空时，列宽至少能容纳 `NAME` 与 `BUNDLE`，不能因空数组算出无效宽度。[D-011、D-013]

CLI 文本帮助和 `--help --json` 的 `list` 旗标说明加入 `--bundle <id>`；`docs/reference/agent-cli-guide.md` 的 `list` 小节说明筛选、JSON 形态及错误边界，并修正该小节已有的过时示例。[D-012] 不把安装命令的逗号分隔或 `all` 语义搬到 `list`。[D-005、D-014]

次要实现决定：按仓库现有 `--json` 错误惯例，JSON 模式在 stderr 写可解析的 `{ "error": true, "message": "…" }`，stdout 为空；普通模式在 stderr 写可读错误。文案无需逐字固定，但必须区分缺值与未知 ID。多次提供 `--bundle`、或给逗号分隔值，应拒绝而不是悄悄只采用其中一个；这落实“一次只筛选一个”的约束。[D-005、D-009]

## 验收依据

1. 当前索引中选一个有技能的 ID（如 `research`）：文本只列其技能，`NAME / BUNDLE` 表格及顺序符合原 `list`；没有工具区块。[D-001、D-006、D-011]
2. 相同 ID 加 `--json`：stdout 只有一个可解析对象，键为 `skills` 与 `tools`，所有技能的 `bundle` 都等于该 ID，技能对象字段保持原契约，`tools` 严格等于 `[]`。[D-002、D-008、D-013]
3. 在隔离的合成索引中设置一个 `bundleMeta` 已登记而 `skills[]` 无成员的 ID：文本只有表头和分隔线，JSON 为两个空数组，退出 0；测试不得改写真实索引。[D-011、D-013]
4. 未知 ID、`all`、工具 bundle ID、大小写不符及 `--bundle` 缺值：均非零退出。带 `--json` 时 stdout 为空、错误在 stderr；普通模式有清楚错误。[D-009、D-014]
5. 对现有无筛选文本和 JSON 建立回归对照，确认字段、内容、顺序和格式不变；帮助文本及 `--help --json` 展示新旗标。[D-003、D-012]

CLI 输出与退出测试按仓库测试指南放在 `tests/agent-cli.bats` 或等效 CLI 测试中；实现完成后运行 `npm test`。空 bundle 的测试可以使用隔离 fixture 或等效机制，具体测试装置由实现者决定。[D-012]

## 构建者检查与未决事项

此需求局限于一个 CLI 命令，按简单任务由设计者自查。已核对正常筛选、空 bundle、无效输入、JSON 错误、帮助和无筛选回归路径；实施所需的关键需求与方案均在已批准决定中。暂无需要用户再决定的事项。`--bundle=<id>` 不是本 Spec 承诺的调用形式；要求的接口为 `--bundle <id>`。[D-001]
