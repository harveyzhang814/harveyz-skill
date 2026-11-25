# capture-feature 写操作细则

`add` / `update` / `remove` / `check` 的流程与对象格式。**只在真的要执行这些命令时才读**——查词用不到它。

脚本路径简写为 `feature.py`，完整命令：`python3 SKILL_DIR/scripts/feature.py <子命令> [参数]`。退出码：`0` 成功/命中，`1` 未命中或校验不通过，`2` 用法错误、找不到数据目录、JSON 无法解析。

## 只收什么

两类对象，用 `type` 区分（命名对齐 PRO 的 Feature 与 visual Interface）：

- `feature`：用户能做的事、能用的能力，例如「节点检索」「会话迁回」。
- `interface`：用户能在上面做动作的交互界面——页面、面板、编辑器，以及按钮、菜单项、快捷键等交互入口，例如「工作区」「顶栏」。

只承担定位、用户在上面没有自己动作的视觉元素，以及机制、数据结构、内部命名，属于 capture-vocab，不进地图。两类对象各成一棵树：**父节点必须与自己同类型**。「某功能在哪个界面上」写进功能的 `description`。

## 对象格式（`schema: 1`）

```json
{
  "schema": 1,
  "id": "workspace",
  "type": "interface",
  "name": "工作区",
  "aliases": ["右侧面板"],
  "avoid": [{"name": "抽屉", "note": null}, {"name": "Workspace", "note": "代码内部名，不向用户暴露"}],
  "description": "右侧可拖拽调宽的滑出区域，内部承载所有 Tab。",
  "parent": "app-window",
  "code": [{"path": "src/renderer/PanelArea.tsx", "symbol": "PanelArea"}],
  "versions": {"introduced": "0.3.0", "changed": [{"version": "0.5.0", "note": "支持多 Tab"}], "deprecated": null}
}
```

| 字段 | 规则 |
|---|---|
| `id` | 必填，`^[a-z0-9]+(-[a-z0-9]+)*$`，等于文件名，创建后不可改 |
| `type` | 必填，`feature` / `interface` |
| `name` | 必填，产品侧称谓；归一化后不得与其他对象重名 |
| `aliases` | 默认 `[]`；可以通用的别称，每项一个叫法，不写说明 |
| `avoid` | 默认 `[]`；应避免的叫法，`{name, note}`，`note` 写为什么避免、该用什么；`name` 也参与匹配 |
| `description` | 必填，一到两句话 |
| `parent` | 必填，父对象 id 或 `null`（根）；父对象须与自己同 `type`；沿父链不得成环 |
| `code` | 默认 `[]`；`{path, symbol?}`，路径相对项目根，**不记行号** |
| `versions` | `introduced` 必填，不知道写 `"unknown"`；`changed` 默认 `[]`；`deprecated` 默认 `null` |

别称、避免叫法与其他对象重叠只警告（`warn:`），不拒绝；名称重复拒绝。

## add `<term>`

1. `feature.py dupcheck "<term>" [--alias A …]`（非 0 即有结果）：
   - `exact | <id>` → 报「已存在」，建议改用 `update`
   - `vocab | <标题>` → 这个词还在术语表里，建议按 `references/migrate.md` 迁过来再从 vocab 删除，由用户决定
   - 只有 `fuzzy | <id>` → 逐个 `show <id>`，**必须显式判一个结论并说给用户**，三选一：同一实体另一个名字（并入别称，走 `update`）/ 父子关系 / 无关
2. 先判类型：用户能做的事 → `feature`；用户能在上面做动作的界面或交互入口 → `interface`；只承担定位、或是机制概念 → 不进地图，告诉用户改走 capture-vocab。再从对话上下文推断 `name`、`aliases`、`avoid`、`description`、`code`（只写路径与符号）
3. `feature.py suggest-parent --name "<名>" [--path P …]`，从候选（`id | name | reason`，reason 为 `same-file` / `dir-contains` / `name`）中**只选同类型的**作为父节点，或判定为根，说明理由；`no candidates` 时多半是根
4. `feature.py project-version` 取版本填 `versions.introduced`；输出 `unknown`（exit 1）或这是存量功能时填 `"unknown"`，并告诉用户
5. 展示完整拟写对象（JSON）、所选父节点、查重结论，等用户确认或修改
6. `echo '<JSON>' | feature.py put --new`；成功输出 `wrote features/<id>.json`。失败时把每条 `error:` 报给用户，修正后重新确认

## update `<term>`

`lookup` / `show` 确定对象，**命中的名称与 `<term>` 不等时停下问是哪一个**（`lookup` 是子串匹配，exit 0 不代表该名字存在）→ 推断修改 → 改了 `parent` 就重跑 `suggest-parent` → 产品行为有变化时在 `versions.changed` 追加当前版本 → 展示修改前后对比，等确认 → `put --replace`（stdin 给完整对象）。

功能被产品废弃时走 `update` 填 `versions.deprecated`，不删除。

## remove `<term>`

仅用于删除录错的数据。确定对象（同样先核对名称相等），确认提示里写出真实名称和 id，等用户确认再 `feature.py remove <id>`。输出 `has children: …` 时拒绝：先把子节点挂到别处或一起删，逐个确认。

## check

跑 `feature.py check --code`，原样呈现 `<类别> | <id> | <详情>`（类别：`invalid`、`id-mismatch`、`missing-parent`、`parent-type-mismatch`、`cycle`、`duplicate-name`、`code-missing`、`symbol-missing`），逐项建议处理；用户同意后走 `update` 或 `remove` 修复。`check` 只报告，不自动修改。干净时输出 `ok`。

## 退路

脚本不可用时不要手改 JSON 文件（绕过校验）；告诉用户功能地图暂时不可写。
