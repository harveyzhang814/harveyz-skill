# extract-cognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已完成的"认知签名抽取"研究（docs/inbox 四份文档）编译落地为一个可执行的 skill：`skills/experiment/extract-cognition/`。

**Architecture:** 不从零设计。④ cognitive-signature-framework.md 作 SKILL.md 母本（7 阶段确定性管线 + schema + runbook 原样保留），仅做"落地适配"——补上配置/输入/slug/`--pass`，并把每阶段"产出签名卡"改为写入三个分阶段文件。① article-analysis-methods.md 作 `references/`。②③ 移入 `docs/reference/cognitive-signature/` 作人读背景。

**Tech Stack:** Markdown（SKILL.md + references）；skills-index.json（JSON 登记）；bats（`npm test` → tests/skills.bats 结构校验）；git。

## Global Constraints

- 命名：skill 目录名与 frontmatter `name` 必须**完全一致** = `extract-cognition`（tests/skills.bats 校验 7）。
- frontmatter 必需字段：`name`、`description`、`version`（semver `X.Y.Z`）；本 skill 加 `user_invocable: true`，`version: "0.1.0"`。
- bundle = `experiment`（已在 skills-index.json 的 bundleMeta 中，勿改 bundleMeta）。
- installScope = `project`（与同组 learn-paper/probe-session 一致）。
- 全程产出中文。
- ASCII art 不用 Unicode 制表符；mermaid 在 md 中可渲染（仓库写作约定）。
- 配置路径写入用 `$HOME` 展开，**不可写字面量 `~`**。
- 分支：在 `feature/extract-reasoning` 分支上累积所有改动（同一功能一个分支），不为每次 commit 新建分支。

---

## File Structure

| 文件 | 责任 |
|---|---|
| `skills/experiment/extract-cognition/SKILL.md` | 可执行管线主体（编译自 ④ + 落地适配） |
| `skills/experiment/extract-cognition/references/article-analysis-methods.md` | Layer 1 方法工具箱（移自 ① ，阶段2 判型查表） |
| `docs/reference/cognitive-signature/cognitive-signature-methodology-v2.md` | 管线 v2 人读说明（移自 ②） |
| `docs/reference/cognitive-signature/methodology-academic-grounding.md` | 学术根基（移自 ③） |
| `docs/reference/cognitive-signature/cognitive-signature-framework.md` | ④ 原文留底（人读对照） |
| `skills-index.json` | 新增 extract-cognition 登记条目 |

---

## Task 1: 把四份研究文档移出 inbox 并搭好目录

**Files:**
- Create dir: `skills/experiment/extract-cognition/references/`
- Create dir: `docs/reference/cognitive-signature/`
- Move: `docs/inbox/article-analysis-methods.md` → `skills/experiment/extract-cognition/references/article-analysis-methods.md`
- Move: `docs/inbox/cognitive-signature-methodology-v2.md` → `docs/reference/cognitive-signature/`
- Move: `docs/inbox/methodology-academic-grounding.md` → `docs/reference/cognitive-signature/`
- Move: `docs/inbox/cognitive-signature-framework.md` → `docs/reference/cognitive-signature/`

**Interfaces:**
- Produces: `skills/experiment/extract-cognition/references/article-analysis-methods.md`（Task 2 在 SKILL.md 阶段2 引用此相对路径）；`docs/reference/cognitive-signature/cognitive-signature-framework.md`（Task 2 以其内容为 SKILL.md 母本）。

- [ ] **Step 1: 建目录**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
mkdir -p skills/experiment/extract-cognition/references
mkdir -p docs/reference/cognitive-signature
```

- [ ] **Step 2: 移动文件（docs/inbox 现为 untracked，用普通 mv）**

```bash
mv docs/inbox/article-analysis-methods.md skills/experiment/extract-cognition/references/article-analysis-methods.md
mv docs/inbox/cognitive-signature-methodology-v2.md docs/reference/cognitive-signature/
mv docs/inbox/methodology-academic-grounding.md docs/reference/cognitive-signature/
mv docs/inbox/cognitive-signature-framework.md docs/reference/cognitive-signature/
```

- [ ] **Step 3: 验证 inbox 清空、文件到位**

```bash
ls docs/inbox/ 2>/dev/null || echo "inbox gone"
rmdir docs/inbox 2>/dev/null || true
ls skills/experiment/extract-cognition/references/article-analysis-methods.md
ls docs/reference/cognitive-signature/
```
Expected: references/article-analysis-methods.md 存在；docs/reference/cognitive-signature/ 下有 3 个 md；docs/inbox 为空或已删。

- [ ] **Step 4: Commit**

```bash
git add -A skills/experiment/extract-cognition/references docs/reference/cognitive-signature docs/inbox
git commit -m "docs(extract-cognition): relocate research docs from inbox into skill references and docs/reference

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 编译 SKILL.md 并登记 skills-index.json

把母本 `docs/reference/cognitive-signature/cognitive-signature-framework.md` 的内容作为 SKILL.md 主体，应用下列**精确改动**后写入 `skills/experiment/extract-cognition/SKILL.md`。母本中未点名改动的部分（操作信条、模式判定表、第 2 节管线总览 mermaid、阶段1–7 的动作/标准、第 5 节失败模式、第 6 节签名卡 schema、第 7 节停机降级、第 8 节最小工作示例、第 9 节 runbook）**原样保留**。

**Files:**
- Create: `skills/experiment/extract-cognition/SKILL.md`
- Modify: `skills-index.json`（skills 数组追加一条）
- Read (母本): `docs/reference/cognitive-signature/cognitive-signature-framework.md`

**Interfaces:**
- Consumes: Task 1 产出的母本文件与 references 路径。
- Produces: 注册名 `extract-cognition`（tests/skills.bats 据 index 校验）。

- [ ] **Step 1: 用此 frontmatter 替换母本的 frontmatter**

母本原 frontmatter 是 `name: cognitive-signature-extraction` + 多行 description（无 version/user_invocable）。替换为：

```yaml
---
name: extract-cognition
description: "Extract an author's cognitive signature — characteristic thinking patterns, reasoning modes, conceptual framings, and unstated assumptions — from a SINGLE local article, as calibrated, evidence-anchored hypotheses about the implied author. Use when the user wants to analyze HOW an author thinks rather than what they say: reverse-engineering an article's reasoning, surfacing hidden premises, profiling mental models or cognitive style, mapping argumentative habits. Triggers: 'analyze the logic/thinking behind this piece', 'what are the author's hidden assumptions', 'reverse-engineer how this was reasoned', 'what's this author's intellectual style'. Single-article focus; not cross-corpus profiling."
user_invocable: true
version: "0.1.0"
---
```

- [ ] **Step 2: 在 frontmatter 之后、正文 `# 认知签名抽取` 标题之后，插入"路径变量 + 初始化"节**

紧接母本第 1 节（输入契约）之前插入下面整节（适配自 learn-paper 的配置/净化/slug/`--pass` 模式）：

````markdown
## 路径变量

```
ConfigPath: ~/.hskill/extract-cognition/config.json
```

### Step 0：初始化配置

用 Read 读取 `~/.hskill/extract-cognition/config.json`。

若不存在，询问用户：

```
认知签名分析保存到哪个目录？（直接回车使用默认：~/Documents/cognition）
```

用户回复后，用 Bash 写入配置（路径用 `$HOME` 展开，不可写字面量 `~`）：

```bash
mkdir -p "$HOME/.hskill/extract-cognition"
output_dir="${用户指定路径/#\~/$HOME}"
[ -z "$output_dir" ] && output_dir="$HOME/Documents/cognition"
echo "{\"output_dir\": \"$output_dir\"}" > "$HOME/.hskill/extract-cognition/config.json"
```

若已存在，解析 JSON 取 `output_dir`，把其中残留的 `~` 展开为 `$HOME`：

```bash
output_dir=$(python3 -c "import json,os; d=json.load(open('$HOME/.hskill/extract-cognition/config.json')); print(d['output_dir'].replace('~', os.environ['HOME'], 1))")
```

### Step 1：提取文章路径，准备输出目录

从用户消息提取主文章路径。**安全净化（Bash）：**

```bash
article_path=$(echo "<用户提供路径>" | tr -d '\000-\037\177' | xargs)
article_path="${article_path/#\~/$HOME}"
test -f "$article_path" || { echo "ERROR: 文件不存在: $article_path"; exit 1; }
```

**生成 slug**（去扩展名、转小写、非字母数字/汉字替换为 `-`）：

```bash
filename=$(basename "$article_path"); filename="${filename%.*}"
slug=$(echo "$filename" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9一-鿿]/-/g' | sed -E 's/-+/-/g' | sed 's/^-//;s/-$//')
mkdir -p "<output_dir>/$slug"
```

**解析 `--pass` 参数：**

| 参数 | 行为 | 依赖 |
|------|------|------|
| `--pass 1` | 只跑阶段 1–3 → `1-evidence.md` | 无 |
| `--pass 2` | 只跑阶段 4 → `2-descriptive.md` | `1-evidence.md` 已存在 |
| `--pass 3` | 只跑阶段 5–7 → `3-attribution.md` | `2-descriptive.md` 已存在 + 模式 B + 基线 |
| 无参数 | 模式 A 跑到文件 2；模式 B 跑到文件 3 | — |

依赖检查（单遍模式）：

```bash
# --pass 2
test -f "<output_dir>/$slug/1-evidence.md" || { echo "请先运行 --pass 1"; exit 1; }
# --pass 3
test -f "<output_dir>/$slug/2-descriptive.md" || { echo "请先运行 --pass 2"; exit 1; }
```

**体裁基线（模式 B）：** 收集 2–3 个基线文件路径，逐个同样净化并 `test -f` 验证；任一不存在则报错或请用户更正。
````

- [ ] **Step 3: 在母本第 1 节"硬停机条件"处补一句输入限定**

在母本"硬停机条件"列表内补一条，明确仅本地文本：

```markdown
- 主文章须为本地 `.md` / `.txt` 文件；不抓取 URL、不解析 PDF。
```

- [ ] **Step 4: 在阶段 2 "判型"动作处补 reference 指针**

母本阶段 2 第 1 步是"判型:用四问…选拆解方法"。在其后补一句：

```markdown
   判型与选拆解法时查阅 `references/article-analysis-methods.md`（19 方法 / 7 家族 / 13 类文章选型对照 / 四问决策树）。
```

- [ ] **Step 5: 把各阶段"产出"改写为写入三个分阶段文件**

按下表改写母本各阶段末尾的"**产出:**"行，并在第 3 节"状态产物"之后插入"产出文件映射"说明。各文件用给定表头。

产出文件映射（插入到第 3 节之后）：

````markdown
## 产出文件映射

执行中各阶段产物落入 `<output_dir>/<slug>/` 下三个文件：

| 文件 | 阶段 | 内容 | 终止/依赖 |
|---|---|---|---|
| `1-evidence.md` | 1–3 | 残余日志 + 逻辑图谱(+补链日志) + 结构信号 | 两源就绪 |
| `2-descriptive.md` | 4(+6/7) | 描述层签名卡 + 描述画像 + 上限声明 + 自审 | **模式 A 到此交付** |
| `3-attribution.md` | 5–7 | 归因层签名卡 + 归因画像 + 自审 | 仅模式 B，依赖文件 2 + 基线 |

每个文件开头写元信息块：
```
# {文章标题} — {阶段名}
**来源文件**: <article_path>
**模式**: A 仅描述 / B 描述+归因
**分析日期**: YYYY-MM-DD
```
````

各阶段"产出"行改写：
- 阶段 1：`**产出:** RESIDUE_LOG，写入 1-evidence.md 的"残余日志"节。`
- 阶段 2：`**产出:** 逻辑图谱(mermaid) + WARRANT_LOG，追加写入 1-evidence.md。`
- 阶段 3：`**产出:** 结构信号清单，追加写入 1-evidence.md。写完告知:✓ 阶段1–3 完成 → <output_dir>/<slug>/1-evidence.md`
- 阶段 4：`**产出:** 一批描述层 SIGNATURE_CARD。组装+置信度(阶段6规则)+自审(阶段7清单)后写入 2-descriptive.md。**分支:** 模式 A → 告知 ✓ 完成并交付(到此为止,零作者断言);模式 B → 进入阶段 5。`
- 阶段 5：`**产出:** 通过全部闸门的归因层签名(暂存,待阶段6组装)。`
- 阶段 6/7：在阶段 7 末尾补 `把归因层签名卡 + 归因画像 + 自审结果写入 3-attribution.md;告知 ✓ 完成 → <output_dir>/<slug>/3-attribution.md。最后输出三文件树。`

- [ ] **Step 6: 在 skills-index.json 的 skills 数组追加条目**

在 `skills` 数组末尾（最后一个元素后，注意补逗号）加入：

```json
    {
      "path": "experiment/extract-cognition",
      "bundle": "experiment",
      "installScope": "project",
      "contentVersion": "0.1.0"
    }
```

- [ ] **Step 7: 校验 JSON 合法**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
python3 -c "import json; d=json.load(open('skills-index.json')); print([s['path'] for s in d['skills'] if 'extract-cognition' in s['path']])"
```
Expected: `['experiment/extract-cognition']`

- [ ] **Step 8: 跑结构校验（tests/skills.bats）**

```bash
bats tests/skills.bats
```
Expected: 全部 PASS（含 "frontmatter name matches directory name"、"version is valid semver"、"bundle is defined in bundleMeta"）。若 name 不等于 `extract-cognition` 或 version 非 `0.1.0` 格式会在此失败 → 返工对应 frontmatter。

- [ ] **Step 9: 跑完整测试套件**

```bash
npm test
```
Expected: bats tests/ 全绿；custom skill tests 无新增（"no custom skill tests" 或既有全过）。

- [ ] **Step 10: Commit**

```bash
git add skills/experiment/extract-cognition/SKILL.md skills-index.json
git commit -m "feat(extract-cognition): compile cognitive-signature framework into executable skill

Mode A/B pipeline, three-file stage output with --pass, references the Layer 1
article-analysis-methods toolbox. Registered in skills-index (experiment bundle).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 对照 spec 验收并收尾

**Files:**
- Read: `docs/superpowers/specs/2026-06-22-extract-cognition-design.md`、`skills/experiment/extract-cognition/SKILL.md`
- Modify: `TODO.md`（标记需求完成）

**Interfaces:**
- Consumes: Task 2 产出的 SKILL.md。

- [ ] **Step 1: 逐条对照 spec 验收（人读 SKILL.md）**

逐项确认下列要点在 SKILL.md 中存在且无矛盾：
```
□ frontmatter: name=extract-cognition, version="0.1.0", user_invocable: true
□ 操作信条三条（假设非事实 / 默认怀疑 / 少声称）保留
□ 模式判定表 + 红线"无基线禁止归因"保留
□ 配置/slug/--pass 节存在，output_dir 默认 ~/Documents/cognition
□ 输入限定为本地 .md/.txt
□ 7 阶段齐全；阶段2 指向 references/article-analysis-methods.md
□ 三文件映射(1-evidence / 2-descriptive / 3-attribution)正确，模式A 终止于文件2
□ 闸门流水线(Patternicity→Agenticity→对立解释→对抗pass→留出验证)保留
□ 签名卡 schema 两层完整；上限声明保留
□ 失败模式 F1–F5、停机/降级、最小工作示例、runbook 保留
```
若有缺失/矛盾，返回 Task 2 对应 Step 修正后重跑 Step 8–10。

- [ ] **Step 2: 确认 reference 相对路径可达**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
grep -n "references/article-analysis-methods.md" skills/experiment/extract-cognition/SKILL.md
ls skills/experiment/extract-cognition/references/article-analysis-methods.md
```
Expected: SKILL.md 中有引用行；文件存在。

- [ ] **Step 3: 标记 TODO 完成**

在 `TODO.md` 中"推理模式提取前置 skill"小节标题处加完成标记，并补一行指向落地结果：

```markdown
### [x] 开发两阶段引导式推理模式提取 skill（元框架前置层）
**已落地为** `skills/experiment/extract-cognition`（认知签名抽取方法论，取代原两阶段锚点设计）。设计见 docs/superpowers/specs/2026-06-22-extract-cognition-design.md。
```

- [ ] **Step 4: 最终全量测试 + 提交**

```bash
npm test
git add TODO.md
git commit -m "chore(extract-cognition): mark TODO done and finalize skill

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: npm test 全绿。

---

## Self-Review 记录

- **Spec 覆盖**：第1节定位→Task2 frontmatter+正文；第2节输入/配置→Task2 Step2/3；第3节模式判定→母本保留(Task2 校验);第4节--pass→Task2 Step2;第5节7阶段→母本保留+Step5 文件映射;第6节schema→母本保留;第7节停机→母本保留;第8节文件落地动作→Task1 + Task2 Step6;第9节YAGNI→无违反(未加URL/PDF/跨语料/自动基线)。
- **占位符**：无 TBD/TODO 式占位；所有写入内容均给出实际文本块。
- **类型/命名一致**：目录名、frontmatter name、index path 末段三处均为 `extract-cognition`；文件名 1-evidence/2-descriptive/3-attribution 在 spec、产出映射表、阶段产出行、Task3 校验项中一致。
