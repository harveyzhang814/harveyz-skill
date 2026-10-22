# 设计稿删除

触发方式见 SKILL.md「设计稿删除」。三个检查点按顺序执行，任一阻止即退出；全部通过且用户确认后才删除。

### 检查点 1：linkedEntryId 存在

查找目标 draft 的 `linkedEntryId`：
- 为 `null` → 输出「❌ 阻止：该页面完成稿尚未生成，无法验证。」退出。
- 非 null → 在 `manifest.entries[]` 中定位对应 entry，继续。

### 检查点 2：uiStates 全覆盖

对比 `draft.uiStates` 与 `entry.uiStates`：
- draft 中有、entry 中无的状态 → 输出「❌ 阻止：以下 UI 状态尚未反映到完成稿：<列表>。建议先运行 sync 补全。」退出。
- 全部覆盖 → 继续。

### 检查点 3：HTML 设计意图比对

读取 `draft.htmlFile` 和 `entry.htmlFile`，确认 draft 中的主要布局结构与组件区块在完成稿中有对应实现：
- 发现明显缺失（主要区块或关键组件未出现在完成稿中）→ 输出「❌ 阻止：以下设计元素未在完成稿中实现：<列表>。建议先运行 sync 补全。」退出。
- 通过 → 继续。

### 确认与删除

输出确认摘要：
> 「设计稿 `<draft.htmlFile>` 的所有设计意图已在完成稿中实现。确认删除设计稿？」

- **取消：** 保留设计稿，不做任何修改。
- **确认：**
  1. 删除 `draft.htmlFile` 对应的 HTML 文件
  2. 从 `manifest.drafts[]` 中移除该 entry
  3. 写回 `manifest.json`
  4. 输出：「设计稿 `<id>` 已删除。」
