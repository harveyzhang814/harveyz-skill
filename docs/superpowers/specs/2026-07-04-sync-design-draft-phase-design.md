---
title: sync-design 设计阶段扩展
date: 2026-07-04
status: approved
---

# sync-design 设计阶段扩展

## 背景

`sync-design` 现有功能：开发完成后，检测 UI 源文件变动（via git diff），同步更新高保真 HTML 完成稿。

本次扩展：新增设计阶段支持。在开发前，用户可以在 skill 框架内创建或修改设计稿 HTML；开发完成后照常同步完成稿；设计稿在完成稿验证通过后删除。

两个阶段使用同一 skill，存储上区分设计稿与完成稿。

---

## 模式检测与触发

### 设计模式触发
- 触发词：「设计」、「create design」、「做个设计稿」、「帮我设计 X 页面」
- 上下文信号：用户描述功能需求或界面改动，无代码变动信号

### 同步模式触发（现有，不变）
- 触发词：「sync design」、「同步」、「update HTML preview」、「design changed」

### 歧义处理
当触发词不明确时，检查辅助信号：
- `drafts[]` 非空且无未同步代码变动 → 倾向设计模式
- git diff 检测到 UI 文件变动 → 倾向同步模式
- 仍不确定 → 询问：「你是想更新设计稿，还是同步代码变动到 HTML？」

### 受影响页面推断
进入设计模式后，从用户描述和上下文推断涉及页面，输出确认：
「我理解以下页面需要更新：\<列表\>，是否正确？」等待确认后操作。

---

## 设计阶段流程

### A. 修改现有设计稿

1. 读取用户描述，定位受影响页面
2. 读取 `outputDir/drafts/<screenName>-<platform>-design.html`
3. 读取上下文（designSpec、设计系统文件、platform notes）
4. 根据描述确定修改范围（哪些 UI 状态或区块）
5. 增量修改 HTML，只替换受影响区块
6. 写回文件，`uiStates` 有新增则追加到 draft entry
7. 输出摘要：哪些页面做了什么改动

### B. 创建新设计稿

1. 询问用户（最少必要信息）：
   - 屏幕/组件名（kebab-case）
   - 需要覆盖的 UI 状态
   - 一句话功能描述
2. **检查 `entries[]` 中是否已有相同 id 的完成稿：**
   - **有完成稿 →** 直接复制完成稿 HTML 到 `outputDir/drafts/<screenName>-<platform>-design.html` 作为基底，读取上下文（designSpec、designSystem、notes），根据用户描述增量修改（与「修改现有设计稿」路径相同）。`linkedEntryId` 在创建时直接写入，无需等 sync 阶段回填。
   - **无完成稿 →** 读取上下文（designSpec、设计系统文件、已有同平台 HTML 作风格参考、源文件完整内容），生成完整高保真 HTML。`linkedEntryId` 设为 `null`，等待 sync 阶段创建 final entry 后回填。
3. 追加 entry 到 `drafts[]`，写回 manifest

### HTML 质量要求
与现有 sync 阶段完全相同（token 来源、CSS 变量命名、UI 状态完整性、离线可用、风格对齐、高保真）。区别仅在于输入来源是用户描述而非 git diff。

---

## Manifest 结构变更

version 从 3 升至 4，新增 `drafts[]` 数组：

```json
{
  "version": 4,
  "baseBranch": "...",
  "config": { ... },
  "entries": [...],
  "drafts": [
    {
      "id": "<screenName>-<platform>",
      "platform": "<platform>",
      "htmlFile": "<outputDir>/drafts/<screenName>-<platform>-design.html",
      "uiStates": ["idle", "loading", "error"],
      "description": "<功能描述>",
      "linkedEntryId": "<screenName>-<platform> 或 null>"
    }
  ],
  "ignoredFiles": [...]
}
```

**字段说明：**
- `linkedEntryId`：对应完成稿 entry id。开发完成 sync 写回时自动填入；删除检查时用于定位对比目标。开发前为 `null`。
- `sourceFiles` 不在 draft entry 中：设计阶段不绑定源文件，由 final entry 维护。

**向后兼容：** 读取 version 3 manifest 时，`drafts` 视为空数组正常继续；写回时自动升级为 version 4。

**目录结构：**
```
.hskill/sync-design/
  manifest.json
  html/                    ← 完成稿（outputDir）
    task-list-mobile-design.html
  html/drafts/             ← 设计稿
    task-list-mobile-design.html
```

---

## 设计稿生命周期与删除

### 删除触发方式（多种）
- 用户显式：「设计稿可以删了」、「design done」、「清理 X 页面的设计稿」
- Sync 流程完成后：若更新的 entry 有对应 draft（`linkedEntryId` 匹配），自动提示「X 页面完成稿已同步，是否检查并删除设计稿？」
- 上下文含「合并」「删除草稿」等信号

### 删除检查点（必须通过，无论触发方式）

1. 通过 `linkedEntryId` 定位 final entry
   - 为 null → 阻止，提示「完成稿尚未生成，无法验证」
2. 对比 draft `uiStates` 与 final `uiStates`
   - Draft 有、final 无的状态 → 列出缺口，阻止删除，建议先 sync 补全
3. 读取两份 HTML，确认 draft 设计意图在完成稿中有对应实现
   - 发现明显缺失 → 列出具体差异，建议先运行 sync
4. 全部通过 → 输出确认摘要，等待用户最终确认
5. 用户确认 → 删除文件，从 `drafts[]` 移除 entry，写回 manifest

### `linkedEntryId` 写入时机
Sync 阶段 4（确认写回）时，检查被更新 entry id 是否在 `drafts[]` 有匹配项，若有则写入对应 draft 的 `linkedEntryId`。对现有 sync 流程透明，仅多一步写回操作。

---

## 不在本次范围内

- 设计稿的版本历史（每次修改不保留历史快照）
- 多人协作冲突处理
- 从设计稿自动生成代码骨架
