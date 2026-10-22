# simplify-skill 扫描：writing / design bundle

扫描日期 2026-10-22，基线为 `staging`（9af95ab）。标准取自 `.claude/skills/simplify-skill/SKILL.md`「拟定建议」7 条，下文按编号引用（R1–R7）。只做到拟定建议这一步，没有改动任何文件。

**主线：** 这 7 个 skill 最大的问题不是篇幅，是**过时的路径、名称和阈值**——design bundle 的 skill 从 `skills/writing/` 搬到 `skills/design/` 之后，路径没跟着改；draw-diagram 的配色体系换成按图类型分区的主题文件之后，旧的 Roland Berger 色板说明也没删。按 R7 把这些对齐，比单纯删字省得多，也更要紧。

**把握度标注：** 【读到】是直接读到原文或文件内容；【推出】是根据读到的内容推断，没有运行验证；【未查】是没核对过的。拿不准、需要用户决定的地方标「未确认」，末尾汇总。

**统计口径：** 规模只算指令文本，即 SKILL.md 加上 references/ 等被引用的 .md。forge-doc 的 scripts/assets 和 draw-diagram 的 themes/*.json 是代码或数据，不计入。

---

# 第一部分：writing bundle

## 1. 总览

| skill | 当前规模（行） | 优化潜力 | 预估可减 | 主要问题 |
|---|---|---|---|---|
| forge-doc | 202（无 references） | 中 | 30–35% | DOCX / PDF 两节命令对称重复，三种内置样式切换各写一遍 |
| draw-diagram | 736（SKILL 259 + references 477） | 高 | SKILL 约 30%，整体 15–20%（如确认 color-templates.md 废弃，整体约 25%） | SKILL §3 的主题文件体系与 §6、references 里的旧 RB 色板互相矛盾；检查清单写「12 项」实际 14 项；深色阈值有两套 |
| manage-dir | 407（SKILL 113 + references 294） | 低 | 5–10% | 基本紧凑，只有一处过时引用和两张重复的表 |
| migrate-spec | 184 | 中 | 约 20% | 末尾「常用命令」重复 Step 1，而且给出另一种扫描方法；标题和 skill 名不一致 |

## 2. draw-diagram（潜力：高）

### 问题归类

**R2 重复**
- §6「快速参考卡」整节（`skills/writing/draw-diagram/SKILL.md:207-259`）在别处都已有：图类型→场景 = §1 速查（`:37-48`）；禁用字符替换 = §4 表（`:154-162`）；矩阵模板 = `references/flowchart.md:14-29`。【读到】
- 禁用字符出现了三遍：§4 表（`:154-162`）、检查清单 4–7 项（`:190-193`）、§6（`:242-251`）。【读到】
- `references/sequence.md:105-113` 的禁止事项重复了 SKILL `:174-176`。【读到】
- §1 的「按语义选型」表（`:24-35`）和「图类型速查」（`:39-48`）有一半重叠；表里的「错误选择」列影响判断，速查里额外只有「LR 仅当内容天然横向」这一条。【读到】

**R5 / R7 含糊或互相矛盾**
- 检查清单开头写「以下 12 项」（`:184`），实际列了 14 项（`:187-200`）。【读到】
- 深色节点阈值有两套：`:113` 用主题文件里的 `rules.dark_text_threshold`（bain/bcg/rolandberger.json 里都是 `#808080`，见 `themes/bain.json:107`）；`:198` 和 `references/color-templates.md:34` 写死 `#4A4A4A`，这个值只出现在旧的 `themes/rb.json:42`。【读到】
- 品牌表把 Roland Berger 指向 `themes/rb.json`（`:86`）。但 rb.json 是旧格式，顶层只有一个 `init`，没有 `flowchart.*` 这类按图类型的分区（`themes/rb.json:1-20`）；同目录的 `themes/rolandberger.json` 才是 build-style 生成的新格式。§3 的机制表要读 `flowchart.*` 路径，用 rb.json 读不到。【读到 + 推出】
- §3 规定「配色从品牌主题文件读，不在图中硬编码，默认 Bain」（`:80, :88`）。可是 §6「配色速查」给的是 RB 深蓝色板，还写着「RB 默认速查」（`:224-238`）；路由行（`:11`）让画 flowchart 时加载 `references/color-templates.md`，这份文件整份都是 RB 深蓝色板，第 4 条还说「sequenceDiagram / gantt / timeline 不着色」（`color-templates.md:37`），和 SKILL `:98-100` 用 `%%{init}%%` 给这三类图着色的规定正好相反。`references/flowchart.md:76-87` 和 `references/statediagram.md:32-34` 的示例也用 RB 色。【读到】
- `:74`「见 `references/flowchart.md 或对应图类型文件`」：反引号位置错了，「或对应图类型文件」指的是哪个文件也不明确。【读到】

**R4 渐进式披露**：已经按图类型拆进 references（`:10-16`），没有新的拆分空间。

### 代表性修改

**① 删掉 §6 快速参考卡**
- 修改前：`:207-259` 整节（52 行），含「图类型→场景」「配色速查（RB）」「禁用字符替换」「矩阵布局模板」四块。
- 修改后：整节删除；只把「产业链 → 3 个 subgraph + UP→MID→DOWN 箭头」并进 §1 速查 `flowchart TD` 那一行，因为这条别处没有。
- 理由：R2，其余内容都在 §1、§4、flowchart.md 里有；RB 配色速查和 §3「不硬编码、默认 Bain」冲突（R5）。

**② 检查清单的数量和阈值**
- 修改前：`每张图创建完毕后，**逐项检查**以下 12 项，全部通过才能输出：` …… `□ 12. 所有深色节点（fill 深于 #4A4A4A）已设 color:#fff`
- 修改后：`每张图输出前逐项检查以下各项，全部通过才输出：` …… `□ 12. fill 深于主题 rules.dark_text_threshold 的节点已设 color:#fff`
- 理由：R7，去掉错误的计数，阈值与 `:113` 统一。**未确认**：Bain 主题下这会让 fill 在 `#4A4A4A` 到 `#808080` 之间的节点也改用白字，属于行为差异，要用户确认以哪个阈值为准。

**③ 路由指向**
- 修改前：`> 矩阵布局 \`---\` 配对技法、subgraph 间箭头写法见 \`references/flowchart.md 或对应图类型文件\`。`
- 修改后：`> \`---\` 矩阵配对、subgraph 间箭头写法见 \`references/flowchart.md\`。`
- 理由：R5，这两项技法只在 flowchart.md 里有。【读到】

### 必须保留
- description 的触发词，以及 `:10-16` 的按需读取路由表。
- 选型矩阵里的「错误选择 / 理由」两列。
- flowchart **禁用** `%%{init}%%`；`%%{init}%%` 只允许用于 sequence / gantt / timeline。
- 主题文件的键路径 `flowchart.*`、`stateDiagram.classDef.*`、`<type>.init`、`semantic.*`、`rules.dark_text_threshold`。这些是**跨 skill 接口**：build-style Step 6.7 按这个结构生成主题文件（`skills/design/build-style/SKILL.md:346-415`）。
- 用户没指定品牌时默认用 Bain。
- 禁用字符清单：`scripts/check_mermaid.py` 的 `RISKY_CHARS` 和它对应（`check_mermaid.py:13-19`）【读到】；改清单时两边要一起对。
- 检查清单本身逐项列出的形式，不要合并成一句「无禁用字符」。

### 未确认
- Roland Berger 应该指向 `rb.json` 还是 `rolandberger.json`。我推断应改成后者，但这属于修 bug，不在精简范围内，建议单独处理。
- `references/color-templates.md` 是否已经被主题文件体系取代。若是，整份文件（75 行）可以删掉，同时去掉路由 `:11` 里对它的引用，再把 flowchart.md 和 statediagram.md 的示例颜色换成主题文件取色。
- 阈值以 `#808080` 还是 `#4A4A4A` 为准（见②）。

## 3. forge-doc（潜力：中）

### 问题归类
- **R2**：Step 0 和 Step 1 两次写「若当前 host 提供提问机制，则使用该机制；若该机制不可用，则在对话中询问」（`skills/writing/forge-doc/SKILL.md:14, :35`）。【读到】
- **R2**：「DOCX 转换」（`:88-111`）和「PDF 转换」（`:115-140`）各有 4 个对称的命令块；「切换内置风格」把 Bain / BCG / 论文各写一遍，每种 DOCX + PDF 两条命令（`:167-198`，32 行），和 `:78-84` 的内置样式表是同一组信息。【读到】
- **R2**：`SKILL_DIR` 的定义在 `:8` 和 `:202` 各出现一次。【读到】
- **R5**：图片路径的规则拆成了两处，`:54` 写什么时候用 `--base-dir`，`:66` 写最佳实践，可以并成一条。【读到】
- **R6**：「支持的元素」表（`:144-157`）是对脚本能力的说明，不影响执行时的判断；里面只有「Mermaid 需要 playwright」一条和依赖有关，已在 `:111` 写过。【推出】

### 代表性修改

**① 内置样式合并成一张表加一条命令模板**
- 修改前：`:78-84` 的样式表，加上 `:167-198` 三组共 6 条命令。
- 修改后：
  ```
  内置样式（--style 传入；DOCX 用 json，PDF 用 css）：
  | 样式 | 适用场景 | DOCX | PDF |
  | Bain | Bain 正式输出 | assets/bain-style.json | assets/bain.css |
  | BCG | BCG 正式输出 | assets/bcg-style.json | assets/bcg.css |
  | 中文学术论文 | 硕博论文、学术报告 | assets/thesis-style.json | assets/thesis.css |
  python3 SKILL_DIR/scripts/md_to_docx.py input.md --style SKILL_DIR/assets/<样式>-style.json
  python3 SKILL_DIR/scripts/md_to_pdf.py  input.md --style SKILL_DIR/assets/<样式>.css
  ```
- 理由：R2，约 45 行压到 12 行左右，文件名和参数一个不少。

**② 提问方式只写一次**
- 修改前：`:14` 和 `:35` 各写一遍 host 提问机制的处理方式。
- 修改后：在「执行前必做」标题下写一次：`Step 0、Step 1 的提问：host 有提问机制就用，没有就在对话中问。` Step 0 保留它自己的条件「若用户未显式指定样式」。
- 理由：R2；保留 Step 0 独有的条件，不扩大到 Step 1（原因见「未确认」）。

**③ 合并图片路径规则**
- 修改前：`:52-66`（含两个示例命令块和一条「最佳实践」）。
- 修改后：`转换已有 MD 文件时传绝对路径。MD 不在图片原目录时（如写到 /tmp 的临时稿），加 --base-dir <图片根目录>；DOCX、PDF 两个脚本都支持。` 再保留一个示例命令。
- 理由：R5，一条规则不拆成两段。

### 必须保留
- 顺序 Step 0 预览 → Step 1 选样式 → 转换，以及「不得跳过此步骤，不得默认使用某一样式」。
- 预览脚本路径 `scripts/generate_style_preview.py` 和预览产物路径 `preview/style-preview.html`。
- 参数 `--style`、`--base-dir`、`--dump-style`，以及「默认输出到同目录」。
- 依赖说明（python-docx、markdown、playwright），以及离线 Mermaid 用 `npm install mermaid`。
- `style.json` 的键 `page / body / headings / code_block / blockquote / table`（`:163`）。这是**跨 skill 接口**，build-style Step 3 按这些键生成 `assets/<brand>-style.json`。

### 未确认
- Step 1 的选项里没有 Roland Berger，可是 `assets/rolandberger.css`、`assets/rolandberger-style.json` 都存在，预览脚本也会渲染它（`scripts/generate_style_preview.py:23`）【读到】。是漏了，还是故意不在菜单里提供？这不属于精简，建议单独确认。
- 用户已显式指定样式时，Step 1 是否还要问一次？原文只在 Step 0 写了这个条件，Step 1 又写着「不得跳过」，两种读法都说得通。
- 「支持的元素」表是直接删掉，还是移到 `references/`。

## 4. migrate-spec（潜力：中）

### 问题归类
- **R7**：标题是 `# migrate-specs`（`skills/writing/migrate-spec/SKILL.md:8`），和 `name: migrate-spec` 不一致。【读到】
- **R2 / R5**：「常用命令」（`:171-184`）重复了 Step 1 的 `find`（`:19`），`:184` 也重复了 `:26-28` 的判定条件。另外 `:178` 用 `grep -rL "^migrated:"` 扫描，Step 1（`:24`）却是「逐个读头部约 15 行」，同一件事给了两种做法。grep 还会把正文里以 `migrated:` 开头的行也算进去。【读到 + 推出】
- **R2**：Step 3 开头的说明（`:42`）重复了 `:10` 的核心原则；标题已经写了「不可跳过」，又补一句「这是最重要的一步」。【读到】
- **R5**：Step 1 写「通常在 docs/ 下，但先用搜索确认……找到后记住这个路径，不再重复搜索」（`:16-22`），可以压成一句。【读到】
- **R5**：3a 说「最新通常是日期更晚的 spec」（`:56`），没写日期从哪里取（文件名前缀？frontmatter？）。【读到】

### 代表性修改

**① Step 1 定位**
- 修改前：`首先找到 \`superpowers/specs/\` 目录，通常在 \`docs/\` 下，但先用搜索确认：` + 命令块 + `找到后记住这个路径，本次 session 后续所有步骤都用它，不再重复搜索。`
- 修改后：`用 \`find . -type d -name specs | grep superpowers\` 定位 specs 目录；后续步骤复用这个路径。`
- 理由：R5。

**② 删掉「常用命令」节**
- 修改前：`:171-184`。
- 修改后：删除。`find skills/ -type d -name "<feature-name>"` 并进 3b 的检查项；Step 1 只留一种扫描方法（建议保留读 frontmatter，因为它能区分「没有 frontmatter」和「frontmatter 里没有 migrated」两种情况）。
- 理由：R2 和 R5。**未确认**：要不要把 grep 留作快捷方式。

**③ 删掉 Step 3 开头说明**
- 修改前：`这是最重要的一步。spec 之间经常重叠——两个 spec 可能覆盖同一主题，较新的那个会覆盖较旧的。逐个迁移会产生冗余或矛盾的文档。`
- 修改后：删除，标题里的「（不可跳过）」保留。
- 理由：R2，`:10` 已经交代了原因。

### 必须保留
- 未处理的判定：没有 frontmatter，或 frontmatter 里没有 `migrated:`。
- Step 1「报告后再继续；全部已迁移就停止」；Step 2「全部读完再分析」。
- 3a–3c，尤其是「不要只依赖 spec 自己的状态字段」，这条会影响判断。
- 4a 按内容块逐段分类，**只用 how-to / explanation / reference 三类**，以及 explanation 的信号词。
- 4b 的新建 / 更新判断，Step 5 更新 `docs/INDEX.md`。
- Step 6 的 frontmatter 字段 `migrated / docs / superseded_by / implemented_in` 及各自的设置条件。这是写回文件的**输出契约**。
- `**状态：** 待实现` 的更新规则，以及「仅标注模式」跳过哪几步。

### 未确认
- 3b 和 Step 6 的示例都假设仓库里有 `skills/` 目录（`:61-63, :151`），也就是 harveyz-skill 自己的结构，但这个 skill 的 installScope 是 project（`skills-index.json`）。它是否只给本仓库用，没有查证。
- 4b 的新建 / 更新规则和 INDEX 描述那句话，与 manage-dir 的说法几乎一字不差（`manage-dir/SKILL.md:65-68, :94`）。可以考虑改成调用 manage-dir，但那会改变行为，不在本次范围内，只记一笔。

## 5. 潜力低 / 无

- **manage-dir（低）**：结构已经紧凑。可改的地方：`:10` 引用的 `diataxis-docs` 已改名为 manage-docs 并归档（`skills/archived/manage-docs`）【读到】，建议删掉这半句；「内置方法论」和「参考文件」两张表（`:98-113`）互相重复，也重复了 `:22-23`，可以合并；`references/methodology-spec.md:62`「四个基础分类」是 Diátaxis 的说法混进了通用规范。`DIR_METHOD.md` 文件名、INDEX.md frontmatter 的 `methodology` 字段，以及 `classification / naming / categories.includes / excludes` 这些字段是**跨 skill 接口**（dedup-skill 会查 `DIR_METHOD.md`，见 `skills/mint/dedup-skill/SKILL.md:101`），不要动。

---

# 第二部分：design bundle

## 1. 总览

| skill | 当前规模（行） | 优化潜力 | 预估可减 | 主要问题 |
|---|---|---|---|---|
| scout-brand | 805（SKILL 387 + TEMPLATE 418） | 中 | 10–15%（不动 JS 脚本的前提下） | TEMPLATE 路径写成 `skills/writing/`（实际在 `skills/design/`）；TEMPLATE 里还用旧 skill 名；`toHex` 函数重复 9 次 |
| build-style | 683（SKILL 452 + FORMAT-MAPPING 231） | 高 | SKILL 约 30%，整体 20–25% | FORMAT-MAPPING 路径错了 7 处；写给 forge-doc / draw-diagram 的输出路径前后两种写法；6.1 规则写了推导又说固定值；深色阈值三套 |
| sync-design | 1117（SKILL 478 + references 639） | 高 | 常驻部分减 35–40%，整体约 10% | 读取上下文的清单重复 4 次；初始化、导入、迁移、删除这些低频流程常驻在 SKILL.md；反模式表基本是复述 |

## 2. build-style（潜力：高）

### 问题归类

**R7 路径与名称**
- `skills/writing/build-style/references/FORMAT-MAPPING.md` 出现在 `skills/design/build-style/SKILL.md:14, :52, :153, :203, :231, :239, :422`，而 skill 实际在 `skills/design/build-style/`【读到】。这个路径无论在仓库里还是装机副本里都找不到文件。【推出】
- 输出路径有两种写法，而且都是**跨 skill 接口**：
  - forge-doc：`:17-18, :432-433` 写 `doc-forge/<brand>-style.json`、`doc-forge/<brand>.css`；`:151, :201` 写 `skills/writing/forge-doc/assets/...`。【读到】
  - draw-diagram：`:434` 写 `mermaid-diagram/themes/<brand>.json`；`:241` 写 `skills/writing/draw-diagram/themes/<brand>.json`。【读到】
  - 两个消费方实际读的是 `skills/writing/forge-doc/assets/` 和 `skills/writing/draw-diagram/themes/`。【读到】
- 旧名：`references/FORMAT-MAPPING.md:4` 写「`/design-derive` skill 读取本文件」；`:352` 输出的 `"_derived_by": "design-derive v1.5.0"`。description 里的 `doc-forge` 属于触发词，不动。【读到】
- 变量名对不上：`:450` 写 `TABLE_ACCENT_COLOR`、`TABLE_ROW_SEP_COLOR`，Step 2 里定义的是 `TABLE_ACCENT`、`TABLE_ROW_LINE`（`:85, :84`）。【读到】
- 引用了模板里没有的 token：`color.text.primary`（`:275`）、`color.text.secondary`（`:331`）。scout-brand 模板的文字色只有 heading / subheading / body / muted / link / inverse（`scout-brand/references/TEMPLATE.md:72-77`）【读到】，所以实际执行时总会落到后面的默认值 `#555555`、`#666666`。【推出】

**R5 含糊或互相矛盾**
- 6.1 subgraph（`:247-263`）先写「以 H1_COLOR 为基准，按 80:20 混合推算」，接着「简化规则：无论品牌色如何，固定使用 `#E8→#F0→#F5`」，深色品牌那段又写「直接用固定浅灰」。三段读下来，实际效果是固定值。【读到】
- 深色阈值有三套：`:411` 的 `dark_text_threshold` 是 `#808080`；`:440` 的核查项写 `#4A4A4A`；`:448` 用「RGB 三通道之和 < 200」判断近黑。而 scout-brand 定义的 `[视觉近黑]` 是 < 150（`scout-brand/SKILL.md:356`）。【读到】
- Mermaid 键名来源冲突：`:239` 说 themeVariables 键名查 FORMAT-MAPPING 第七节，第七节给的是旧的扁平结构（`primaryColor / mainBkg / clusterBkg …`，`FORMAT-MAPPING.md:182-194`）；6.3–6.5 和 6.7 用的却是按图类型分区的键（`actorBkg`、`taskBkgColor`、`cScale*`）。【读到】
- Step 1（`:33`）写「若未指定，默认推导 DOCX + PDF」，紧接着又给出格式选项让用户选，没说清楚是先问还是直接用默认。【读到】

**R2 重复**
- 注意事项 `:451-452`（字体中文名、颜色格式）重复 Step 3/4 的编码规则（`:155, :158, :208`）和 FORMAT-MAPPING §一、§三。【读到】
- Step 8 核查项 1（`:437`）重复 Step 4 的对比检查（`:223-225`）。【读到】

### 代表性修改

**① FORMAT-MAPPING 路径（7 处）**
- 修改前：`**映射规则参考 \`skills/writing/build-style/references/FORMAT-MAPPING.md\`：**`（`:153` 等 7 处）
- 修改后：在概述里定义一次 `映射标准：references/FORMAT-MAPPING.md（下称 FORMAT-MAPPING），推导以它为准。`，后面统一写 `FORMAT-MAPPING §二` 这样的形式。
- 理由：R7 修正失效路径；R3 用简称代替 7 次长路径。

**② 6.1 subgraph 改成固定值表**
- 修改前：`:247-263`，即「以 H1_COLOR 为基准推算……80:20 混合后再向灰偏移……简化规则：无论品牌色如何……深色品牌基准同上……」
- 修改后：
  ```
  flowchart.subgraph 固定为浅灰三层，不随品牌色变化：
  | 字段 | fill | stroke | text |
  | layer1 | #E8E8E8 | #C8C8C8 | #212427 |
  | layer2 | #F0F0F0 | #D0D0D0 | #212427 |
  | layer3 | #F5F5F5 | #D8D8D8 | #212427 |
  ```
- 理由：R5，原文三段规则最后都落到固定值；stroke 取 6.7 里的具体值（`:356-358`），不再写「× 0.85」。**未确认**：按 `× 0.85` 算，stroke 应为 `#C5C5C5 / #CCCCCC / #D0D0D0`，6.7 写的却是 `#C8C8C8 / #D0D0D0 / #D8D8D8`，两处本来就对不上【推出：手算】；现有 bain.json 用的是 6.7 的值【读到】，所以建议以 6.7 为准，但要用户确认。

**③ Step 8 摘要里的路径**
- 修改前：`> \`doc-forge/<brand>-style.json\` 已生成` / `> \`doc-forge/<brand>.css\` 已生成` / `> \`mermaid-diagram/themes/<brand>.json\` 已生成（若包含 Step 6）`
- 修改后：`> \`skills/writing/forge-doc/assets/<brand>-style.json\`、\`<brand>.css\` 已生成` / `> \`skills/writing/draw-diagram/themes/<brand>.json\` 已生成（若包含 Step 6）`；概述 `:17-18` 同步修改。
- 理由：R7，与 Step 3/4/6 的实际写入路径一致。

### 必须保留
- 输入路径 `knowledge/design/<brand>-style.md`。这是**跨 skill 接口**，由 scout-brand 产出。
- 读取方式：按 scout-brand TEMPLATE 的章节号（2.1/2.2/2.3/3.2/3.3/4.2/4.3/5.1/5.2）和 token 名读取；token 引用链的解析规则；旧格式直接写 hex 时的兼容处理（`:65`）。
- Step 2b 的触发条件、换算算法、安全检查和 BCG 示例。
- Step 3 JSON 骨架的字段名（forge-doc 的 style.json 格式）和 Step 4 CSS 文件头格式。
- Step 6.7 主题文件的顶层结构 `flowchart / stateDiagram / sequenceDiagram / gantt / timeline / semantic / edge / rules`。这是**跨 skill 接口**，draw-diagram §3 按它读取。
- 6.6 各 semantic 色无值时的默认色；`rb` 表格模式才填的两个字段；`待补充` 字段用默认值并注明。
- 「装饰线必须用动作色」这条检查；HTML / PPT 打印到对话、不写文件；结尾提示可以接着用 `/forge-doc`、`/draw-diagram`。

### 未确认
- 输出路径都是仓库相对路径，意味着只有在 harveyz-skill 仓库里运行才写得到消费方目录。这是不是本意？（installScope 为 project，`skills-index.json`）
- 深色阈值三套里以哪一套为准；建议和 draw-diagram 一起定。
- Mermaid 键名以 FORMAT-MAPPING §七（扁平）还是 SKILL 6.3–6.7（分区）为准。我推断分区结构是现行的，因为现有的 bain/bcg/rolandberger.json 都是分区结构【读到】；若确认，FORMAT-MAPPING §七要改写或删除。
- `_derived_by` 的值要不要改成 `build-style`。全仓 grep 没找到读取这个字段的地方【读到】，但它是输出内容的一部分。
- `color.text.primary` / `color.text.secondary` 是直接改成模板里已有的 token，还是删掉、只留默认值。
- Step 1 的格式选择：先问再默认，还是不问直接默认。

## 3. sync-design（潜力：高）

### 问题归类

**R2 重复**
- 「读取上下文」清单写了 4 次：设计模式情况 A（`skills/design/sync-design/SKILL.md:72-76`）、情况 B 无完成稿（`:110-115`）、同步更新队列（`:196-203`）、同步新建队列（`:243-251`）。前 5 项相同，每处只多一两项。【读到】
- draft entry 的 JSON 写了 2 次（`:92-102`、`:118-128`），只有 `uiStates / description / linkedEntryId` 的取值不同。【读到】
- 屏幕名 / UI 状态 / 描述这三个问题出现 2 次（`:106-109`、`:237-239`），导入流程里还有一个变体（`:426-428`）。【读到】
- 回填 linkedEntryId 写了 2 次（`:212-214`、`:271-273`）。【读到】
- 「按本次模式路由」这句出现 4 次（`:49, :411, :431, :451`）。【读到】
- 反模式表（`:467-478`）8 行里，7 行在正文中已有对应规则（`:471` 对应初始化，`:472` 对应 `:282`，`:473` 对应 `:303-304`，`:476` 对应 `:315-331`，`:477` 对应 `:13-14`，`:478` 对应 `:318`，`:474` 对应 `:293-294`）。只有 `:475`「不要手动编辑 manifest」是正文没有的。【读到】

**R4 渐进式披露**
- 首次初始化（`:347-411`）、已有 HTML 导入（`:415-431`）、旧路径迁移（`:435-451`）只在初始化检查命中时执行；设计稿删除（`:308-343`）只在特定触发时执行。四段合计约 130 行，现在每次调用都会加载。【推出】

**R5 含糊**
- 阶段 4 写了「用户选『确认』」「用户选『取消』」（`:292, :303`），但没写要先问用户。【读到】
- 旧路径迁移选「是」的分支没有写迁移后去哪里，只有选「否」写了按模式路由（`:443-451`）。【读到】
- `styleStrategy` 的空值：`:201` 写「若为 `null` 则从源文件自行判断」，取值表（`:371`）和 `references/stack-react.md:5` 用的是 `unknown`。【读到】

### 代表性修改

**① 读取上下文只定义一次**
- 修改前：4 处各自列出 4–7 项。
- 修改后：在「设计阶段」之前加一节：
  ```
  ## 标准上下文（后读覆盖先读）
  1. manifest.config.designSpec（若有）
  2. 所属平台的 designSystemFile（若有）
  3. 所属平台 stackRef 指向的 reference 中，与 styleStrategy 匹配的那一节（styleStrategy 为 unknown 时从源文件判断）
  4. 所属平台 notes（优先于 reference）
  ```
  4 处各改成一行，例如更新队列写 `读标准上下文，再读 <entry.htmlFile>（不存在则改为全量生成：读全部 sourceFiles）`；新建队列写 `读标准上下文，再读源文件全文及 notes / reference 指定的关联文件，再选一个 outputDir 下同平台 HTML 作风格参考`。
- 理由：R2；各处多出来的项原样保留。**未确认**：null 和 unknown 是否等价。

**② 反模式表改成一句**
- 修改前：`:467-478` 的 8 行表。
- 修改后：删掉表格，只留 `不手动编辑 manifest.json；entries 与文件的一致性靠本流程维护。`；把 `:474` 的理由「否则下次 diff 基准错误、漏同步」并进阶段 4 第 2 步。
- 理由：R2，其余 6 行正文都已规定；R6 只留影响决策的解释。

**③ 低频流程移到 references**
- 修改前：`:308-343`、`:347-451` 常驻 SKILL.md。
- 修改后：新建 `references/init.md`（首次初始化、已有 HTML 导入、旧路径迁移）和 `references/draft-delete.md`。SKILL.md 的「初始化」节保留 4 个判断条件，各自写明命中后读哪份文件、读完回到下一个检查；「设计稿删除」节保留触发方式，并写明「三个检查点全部通过并经用户确认才删除，细节见 draft-delete.md」。
- 理由：R4，常驻部分约减 130 行；同时补上迁移「是」分支缺的去向（R5）。

### 必须保留
- 开头的 `Announce at start` 那句话。
- 模式检测的触发词和歧义时的判断规则。设计模式是**跨 skill 接口**：init-spec 会调用 sync-design 的设计模式（`skills/superpowers-rewrite/init-spec/SKILL.md:87`）。
- `.hskill/sync-design/manifest.json` 与 `.hskill/sync-design/html/` 两个路径。这是**跨 skill 接口**：init-project 会检查这两个路径（`skills/coding/init-project/SKILL.md:146`、`assets/skeleton/gitignore-code:5`）。
- manifest 全部字段名和 `version: 4` 的升级规则。
- 文件命名 `<screenName>-<platform>-design.html`；设计稿放 `drafts/`，完成稿放 `outputDir/`，两者分开。
- 阶段 1–4 的 STRICT 顺序和两条 `git diff` 命令；设计系统文件变动时询问是否全量重生成。
- HTML 生成质量要求 6 条（完成标准里也引用了「6 条」）。
- 阶段 4 确认后写 `lastSyncCommit`、取消时不写 manifest；commit message 模板。
- 设计稿删除的三个检查点及各自的阻止文案；`styleStrategy` 的取值枚举。

### 未确认
- `styleStrategy` 的 null 和 unknown 是否等价。
- 把删除流程挪出 SKILL.md 后，靠用户口令触发删除（`:312-313`）时，agent 会不会可靠地去读 references。我推断只要入口行写明「先读 draft-delete.md」就够，但没有测过。
- 4 份 stack reference 开头的「使用方式」提示（`stack-electron.md:5` 等）和 SKILL `:201-202` 重复，能省约 4 行。收益小，列为可选。

## 4. scout-brand（潜力：中）

### 问题归类
- **R7 路径**：`skills/writing/scout-brand/references/TEMPLATE.md`（`skills/design/scout-brand/SKILL.md:16, :332`），实际在 `skills/design/`。【读到】
- **R7 旧名**：TEMPLATE 里 `/design-derive`（`references/TEMPLATE.md:3, :25, :122, :321`）、`/style-scout`（`:4`）、`doc-forge`（`:335, :349`）都是旧名，现在分别是 build-style、scout-brand、forge-doc。【读到】
- **R2**：`toHex` 函数逐字重复 9 次（`SKILL.md:63, :73, :90, :171, :181, :198, :221, :276, :295`）。每次 `$B js` 都是单独执行，不能跨调用复用，除非挂到 `window` 上；页面一跳转 `window` 就会重置。【读到 + 推出】
- **R2**：Step 8a（`:160-175`）就是 Step 3 第一段脚本，只是选择器少了 hero/nav，取前 8 条而不是前 10 条。【读到】
- **R2**：注意事项里「先关弹窗再截图」（`:383`）重复 Step 2、Step 7；「深色 ≠ 有色」（`:385`）重复 `:356` 和 TEMPLATE `:68`。【读到】

### 代表性修改

**① TEMPLATE 路径**
- 修改前：`输出文档遵循 \`skills/writing/scout-brand/references/TEMPLATE.md\` 的完整结构`（`:16`；`:332` 同样）
- 修改后：`输出文档遵循 \`references/TEMPLATE.md\` 的完整结构`
- 理由：R7，原路径找不到文件。

**② Step 8a 改为引用 Step 3**
- 修改前：`:162-175` 的整段脚本。
- 修改后：`在报告页重跑 Step 3 第一段脚本，从选择器里去掉 \`[class*=hero] *\` 和 \`nav *\`，取前 8 条。`
- 理由：R2，约省 13 行。**未确认**：把精确脚本换成文字描述，agent 要自己改选择器，执行起来不如直接复制脚本稳。这里是篇幅和执行稳定性之间的取舍。

**③ 注意事项去重**
- 修改前：`:382-387` 共 6 条。
- 修改后：保留 4 条：`不下载 PDF，只分析 HTML 页面`；`CSS bundle 色值稀少时说明站点用 CSS 变量，改用渲染层 API 补充`；`主页与报告页动作色冲突时以主页 Hero CTA 为准，并在文档中注明`；`报告页没有表格或引用块时另找一篇，仍找不到就填「待补充」`。
- 理由：R2，去掉「先关弹窗」「深色 ≠ 有色」两条，这两条在步骤里已有。

### 必须保留
- 输出路径 `knowledge/design/<brand>-style.md`（description 里也写着），以及「只调查、不生成配置」。这是**跨 skill 接口**，由 build-style 读取。
- 依赖 `/browse` 提供的 `$B`。
- 两阶段顺序（主页 → 报告页）以及数据来源优先级表。
- `color.interactive.primary` 必须取主页 CTA 按钮色；`[视觉近黑]` 的定义（RGB 三通道和 < 150）。
- `待补充` 占位：build-style 的注意事项会读这个标记（`build-style/SKILL.md:449`）。
- 表格模式 `grid / mckinsey / rb`：build-style 用它填 `TABLE_MODE`。
- 写完后给用户的核查提示和 `/build-style` 提示：init-skill 的写作指南引用了这段（`skills/mint/init-skill/references/skill-authoring-guide.md:140`）。
- TEMPLATE 的**章节号和 token 名**：build-style Step 2 按章节号读取（`build-style/SKILL.md:93-113`），改编号就会断。

### 未确认
- TEMPLATE 里的旧名替换：这段文字会被抄进生成的品牌文档，所以替换后生成文档的措辞也会变。我认为应该换，但这算动了输出内容，要用户点头。
- TEMPLATE §9「各格式推导指南」（`TEMPLATE.md:319-418`，约 100 行）和 build-style 的 FORMAT-MAPPING 重复；build-style 声明以 FORMAT-MAPPING 为权威（`build-style/SKILL.md:14`），而且 §9 的 Mermaid 段是旧的扁平结构。删掉它整体能再省约 12%，但会改变产出文档的结构（输出契约），本次不建议，只列出来请用户决定。
- 9 处 `toHex` 有两个精简方案：(a) 在 Step 2 和 Step 7 加载页面后各注入一次 `window.__toHex`；(b) 把脚本移到 `scripts/*.js`，用 `$B eval <file>` 执行。方案 (b) 有前提：browse 要求文件路径在 /tmp 或 cwd 下（browse SKILL.md 中 `eval` 一行）【读到】，所以得先复制到 /tmp。两种方案都会改变执行步骤，都没验证过。

---

# 附：跨 skill 接口汇总（精简时不能动）

| 生产方 → 消费方 | 接口 |
|---|---|
| scout-brand → build-style | `knowledge/design/<brand>-style.md`；TEMPLATE 章节号和 token 名；`待补充`；`[视觉近黑]`；表格模式 `grid / mckinsey / rb` |
| build-style → forge-doc | `skills/writing/forge-doc/assets/<brand>-style.json`、`<brand>.css`；style.json 键 `page / body / headings / code_block / blockquote / table` |
| build-style → draw-diagram | `skills/writing/draw-diagram/themes/<brand>.json`；分区结构与 `rules.dark_text_threshold` |
| draw-diagram 内部 | 禁用字符清单 ↔ `scripts/check_mermaid.py` 的 `RISKY_CHARS` |
| sync-design ↔ init-project / init-spec | `.hskill/sync-design/manifest.json`、`.hskill/sync-design/html/`；设计模式触发 |
| manage-dir ↔ dedup-skill | `DIR_METHOD.md`；INDEX.md frontmatter 的 `methodology` 字段 |
| migrate-spec 输出 | spec frontmatter 字段 `migrated / docs / superseded_by / implemented_in` |

# 附：未确认汇总

1. draw-diagram：RB 主题应指向 `rb.json` 还是 `rolandberger.json`；`color-templates.md` 是否废弃。
2. draw-diagram + build-style：深色阈值以 `#808080`、`#4A4A4A`、RGB 和 < 200 中的哪一个为准（scout-brand 的 < 150 是另一个概念，用于判断「视觉近黑」）。
3. build-style：Mermaid 键名以 FORMAT-MAPPING §七还是 SKILL 6.3–6.7 为准；`_derived_by` 改不改；`color.text.primary / secondary` 怎么处理；Step 1 先问还是直接默认；输出路径是否只在本仓库内有效。
4. build-style 6.1：stroke 以 `× 0.85` 的计算值为准，还是以 6.7 的具体值为准（两者不一致）。
5. forge-doc：Step 1 菜单缺 Roland Berger；用户指定样式后 Step 1 是否跳过；「支持的元素」表删除还是移走。
6. migrate-spec：是否只用于本仓库；grep 快捷方式留不留；「最新」按什么日期判断。
7. sync-design：`styleStrategy` 的 null 和 unknown 是否等价；删除流程移出后，由口令触发时能否可靠加载 references。
8. scout-brand：TEMPLATE 旧名替换（会改生成文档的措辞）；TEMPLATE §9 去留（会改输出结构）；`toHex` 去重方案；Step 8a 改为文字描述后执行是否稳定。
