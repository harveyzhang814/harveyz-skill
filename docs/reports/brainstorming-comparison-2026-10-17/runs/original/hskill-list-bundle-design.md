# `hskill list --bundle` 设计

日期：2026-10-17

状态：待用户审查；仅为设计，不授权实现

## 意图

用户通常已知道 bundle ID，但现有 `hskill list` 会列出全部技能和 shell tools。用户需要在命令行一次查看一个 bundle 的技能，也需要在 `--json` 输出中得到相同的筛选结果，省去手动查找或二次处理。没有筛选参数时，现有行为和格式必须保持。

## 用户已明确的行为

- 新入口为 `hskill list --bundle <id>`，可与 `--json` 同用。`<id>` 按 `skills-index.json` 中的 `bundleMeta` 键精确匹配。一次只查看一个 bundle。
- 筛选对象仅为技能。筛选后的文字输出不显示 shell tools 区块。筛选后的 JSON 保留现有顶层 `skills`、`tools` 字段，其中 `tools` 为 `[]`；技能项保留现有字段。
- 不带 `--bundle` 时，文字和 JSON 的内容、结构、排序、格式与现有 `hskill list` 保持一致，包括 shell tools。
- bundle ID 未定义或 `--bundle` 缺少值时，给出清楚错误并以非零状态退出。配合 `--json` 时，错误只写 stderr，stdout 为空。
- bundle ID 已定义但无技能时，成功返回空技能列表；JSON 为 `{"skills":[],"tools":[]}`。

## 当前项目事实

- `bin/cli.js` 的 `list` 分支读取 `skills-index.json` 的 `skills` 和 `tools`。技能先按 bundle、再按路径末段的技能名排序；文字输出为 `NAME` / `BUNDLE` 表格，随后是 `SHELL TOOLS` 区块。JSON 输出是 `{skills: [{name,path,bundle,global}], tools: [name]}`。
- `skills-index.json` 的 `bundleMeta` 定义 bundle ID，`skills[].bundle` 表示技能所属 bundle；当前有 `research` 等 ID。
- `--help` 同时有文字版和 JSON 命令元数据。CLI 输出形状及退出码测试放在 `tests/agent-cli.bats`；运行 `npm test` 检查整个仓库。
- 现有部分 JSON 错误使用 stderr 上的 `{ "error": true, "message": "..." }` 对象。

## 建议的命令契约

```text
hskill list [--bundle <id>] [--json]
```

参数顺序可互换。`--bundle` 只接收一个 ID，不把逗号视为多选语法。筛选时仅保留 `skill.bundle === id` 的条目，再沿用当前排序、技能项映射和表格样式。例如 `hskill list --bundle research --json`：

```json
{
  "skills": [
    {
      "name": "clip-url",
      "path": "research/clip-url",
      "bundle": "research",
      "global": false
    }
  ],
  "tools": []
}
```

示例只展示一个技能项；实际结果包含该 bundle 的全部技能。筛选后的文字输出继续显示 `NAME` / `BUNDLE` 表头和技能行，不显示 `SHELL TOOLS`。已定义的空 bundle 继续显示表头，但不显示技能行或 shell tools。

## 错误与参数细节

- 使用 `bundleMeta` 而非是否存在对应技能行来验证 ID，这样空 bundle 可得到成功的空列表。
- `--bundle` 后没有 token，或紧随其后的是另一个选项（如 `--json`），都算缺少值。空字符串同样算缺少值。
- 未知 ID 报出该 ID；文字模式把错误写到 stderr。JSON 模式沿用 `{ "error": true, "message": "..." }` 形状写到 stderr，不在 stdout 打印任何内容。错误退出码可用 1，无需引入新的错误码体系。
- 重复 `--bundle` 或逗号分隔的多个 ID 报错，提示一次只接受一个 ID。此项是设计者的默认取舍，理由是用户明确表示一次只看一个 bundle；若用户希望复用 `install --bundle` 的多选语法，可在审查时调整。

## 实现建议与留给开发者的选择

设计者建议仅修改 `bin/cli.js` 的 `list` 分支，在读取索引后验证 ID、筛选技能，并让无筛选路径继续走现有渲染逻辑。更新文字 `--help` 和 JSON 帮助中的 `list` 参数说明，必要时同步当前 CLI 使用文档。用户已确认行为，但未选择或批准这一具体代码组织方式；开发者可采用同等兼容的实现。

开发者可决定辅助函数命名、错误消息措辞，以及是否抽取共用的列表渲染函数，但应保持上述输出与错误契约。无需改动 `skills-index.json` 的结构、bundle 安装逻辑或 shell tool 数据。

## 验收与测试要点

- 对当前 `research`：文字输出只含其技能与既有表格结构；JSON 技能项全属于 `research`，保留现有字段及排序，`tools` 严格为空数组。`--json` 和 `--bundle` 两种顺序都能工作。
- 对无筛选调用：文字输出和 JSON 与修改前的代表性输出一致，尤其是 shell tools、字段及排序。
- 对未知、缺失、空值以及重复/多 ID：非零退出；JSON 错误只在 stderr 且 stdout 为空。
- 用一个已定义但没有技能的测试索引验证成功的空列表，尤其避免空数组导致文字列宽计算异常。
- 帮助文本与 JSON 帮助包含 `--bundle <id>`；最终运行 `npm test`。

## 范围外

不更改 `install --bundle`、`status`、`outdated`、`info` 或其他命令；不增加多 bundle 筛选、模糊匹配、shell tool 筛选或产品代码实现。
