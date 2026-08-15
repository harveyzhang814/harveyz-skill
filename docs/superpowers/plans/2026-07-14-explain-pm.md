# explain-pm 实施计划

**目标：** 新增一个单文件会话内 skill `coding/explain-pm`，手动调用时把最近一段技术性表述从 PM 视角复述（转译 + 视情况提出关注点）。

**架构：** 纯 prompt/说明型 skill（无脚本、无 references），风格参照 `skills/coding/rephrase/SKILL.md`。注册进 `skills-index.json` 的 `coding` bundle，跑一遍 `publish-skill` 校验并写入 `contentHash`。

**技术栈：** Markdown + YAML frontmatter；`node scripts/generate-npmignore.js`；bats（`npm test`，仅作回归检查，不直接测本 skill 内容）。

**已知偏差（已与用户确认，无需再问）：** 目录名 `explain-pm` 的动词 `explain` 不在 `docs/reference/skill-spec.md` 的规范动词词表中，F7 检查会不通过。用户已明确选择保留这个名字（与现有的 `rephrase` 同样不合规，属于已接受的先例），执行时**不要**因为 F7 而建议改名或自动重命名。

---

### Task 1: 创建 SKILL.md

**文件：**
- 创建: `skills/coding/explain-pm/SKILL.md`

- [ ] **Step 1: 写入 SKILL.md**

写入以下完整内容（无占位符）：

```markdown
---
name: explain-pm
description: "Restate a recent technical explanation in product-manager language: translate jargon into user/business impact, and flag product-perspective concerns like scope, over-engineering, priority, or drift from user need. Triggers: '/explain-pm', '/explain-pm <topic or file>', 'explain this like a PM', 'restate from a PM perspective'."
user_invocable: true
version: "1.0.0"
---

# explain-pm — PM 视角复述

把一段技术性表述从 PM 视角复述：先转译成产品/业务语言，再视情况指出值得从产品角度重新考虑的地方。

## 触发

仅手动调用：`/explain-pm` 或 `/explain-pm <主题或文件路径>`。不自动检测触发，不主动插话。

## 执行

1. **取材料**：带参数用参数指定的主题或文件；无参数则取调用前的最后一条 assistant 消息。
2. **转译**：把技术语言换成产品/业务语言——这段话讲给 PM 听，PM 听到的是什么（用户能得到什么、解决了什么问题、有什么代价）。
3. **提出关注点（视情况）**：判断原表述从 PM 角度是否有值得重新审视的地方，比如是否偏离用户实际需求、范围是否合理、是否过度工程化、优先级是否搞错了。如果原表述本身已经很贴近产品目标，挑不出问题，就只做转译，不硬造关注点。
4. **输出**：在对话中直接回复，简短（几句话量级）。默认不写文件；仅当用户明确要求存档时，才把这段评论写入用户指定的文件。

## 不做

多轮追问式澄清、自动检测技术语言并主动触发、默认生成或保存文档、固定的输出小标题模板。
```

- [ ] **Step 2: 校验 frontmatter 格式（F1–F6）**

运行：

```bash
f="skills/coding/explain-pm/SKILL.md"
awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' "$f"
```

预期输出恰好三行：`name: explain-pm`、`description: "..."`（英文，长度 ≥ 10）、`user_invocable: true`、`version: "1.0.0"`（共四行，semver 格式）。

再运行：

```bash
tail -n +7 "$f" | grep -q '[一-鿿]' && echo "F6 pass (正文含中文)"
```

预期输出：`F6 pass (正文含中文)`

---

### Task 2: 注册到 skills-index.json

**文件：**
- 修改: `skills-index.json`

- [ ] **Step 1: 更新 bundleMeta.coding 描述**

在 `skills-index.json` 顶部 `bundleMeta.coding` 字段中，把：

```json
"coding": "程序工具（init-workflow + setup-debug + init-goal + question-me + capture-vocab + rephrase）",
```

改为：

```json
"coding": "程序工具（init-workflow + setup-debug + init-goal + question-me + capture-vocab + rephrase + explain-pm）",
```

- [ ] **Step 2: 在 skills[] 中追加条目**

找到 `coding/rephrase` 条目（在 `skills[]` 数组中）：

```json
    {
      "path": "coding/rephrase",
      "bundle": "coding",
      "installScope": "global",
      "contentHash": "cc5a948ce0e80a53",
      "contentVersion": "1.0.1"
    },
```

在其后追加新条目（不写 `contentHash`/`contentVersion` — 首次初始化，由 Task 3 的 publish-skill 校验负责写入）：

```json
    {
      "path": "coding/explain-pm",
      "bundle": "coding",
      "installScope": "global"
    },
```

- [ ] **Step 3: 重新生成 package.json / .npmignore**

运行：

```bash
node scripts/generate-npmignore.js
```

预期输出包含类似 `Updated package.json files: N entries`，且 N 比之前多 1；命令不报错（若报错 "references skill ... but directory does not exist"，说明 Task 1 的文件路径写错了，需回去检查）。

---

### Task 3: 校验、回归测试与提交

- [ ] **Step 1: 用 publish-skill 校验新 skill**

调用 `publish-skill` skill（Skill 工具，`args: "coding/explain-pm"`），只检查这一个 skill。

预期：F1–F6、F8（首次初始化）、R1–R3 全部通过；F7 会报告 `explain-pm` 不合规（动词 `explain` 不在词表）——这是已知且已确认接受的偏差，**不要**接受重命名建议，直接确认保留现有名字。publish-skill 会把计算出的 `contentHash`/`contentVersion` 写回 `skills-index.json` 并 `git add` 暂存。

- [ ] **Step 2: 跑一遍 npm test 做回归检查**

运行：

```bash
npm test
```

预期：全部现有测试仍然通过（本次改动不涉及 CLI 安装逻辑，属于纯回归确认，不应有新失败）。

- [ ] **Step 3: 创建 feature 分支**

当前在 `staging` 分支上不能直接提交。运行：

```bash
git checkout -b feature/explain-pm
```

- [ ] **Step 4: 提交**

```bash
git add skills/coding/explain-pm/SKILL.md skills-index.json package.json .npmignore
git commit -m "feat(skill): add explain-pm — PM-perspective restatement of technical output"
```

（若 Task 3 Step 1 的 publish-skill 已经 `git add` 了 `skills-index.json`，这里的 `git add` 是幂等的，正常执行即可。）

---

## 执行完成后

分支 `feature/explain-pm` 已包含全部改动。按仓库约定，只有用户明确说"合并"或"完成"时才合并回 `staging`（见 CLAUDE.md 的 Git 工作流规范）——这一步不在本计划范围内，等待用户指示。
