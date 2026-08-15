# fetch-paper 实施计划

**目标：** 新增 `fetch-paper` skill——给定论文标题/DOI/arXiv ID/引用，联网核实论文真实存在，仅通过合法开放获取渠道尝试下载全文 PDF，按 A/B/C/D 四态汇报结果，并维护可复用的免费资源站点清单。

**架构：** 纯 Prompt 型 skill（无脚本、无可单测代码），与 `learn-paper` 同级放在 `skills/research/` 下。落地形式是一份完整的 `SKILL.md`，遵循 `docs/superpowers/specs/2026-08-15-fetch-paper-design.md` 定义的流程。

**技术栈：** SKILL.md（YAML frontmatter + Markdown 指令）、WebSearch/WebFetch、Crossref/Unpaywall/Semantic Scholar/arXiv/PMC 公开 API、`skills-index.json` 注册。

**说明（适配本仓库实际情况）：** 本仓库对纯指令型 skill（如 `learn-paper`）不写单元测试，"验证"手段是：(1) `docs/reference/skill-spec.md` 定义的格式校验（F1–F8/R1–R4，`npm test` 会跑到），(2) 手动 dry-run 一次真实场景。因此下面任务的"测试"步骤替换为格式校验 + 手动 dry-run，而非 pytest 风格的失败测试先行。

---

### Task 1: 扩展动词词表，加入 `fetch`

**背景：** `skill-spec.md` 的命名规范要求目录名为 `<动词>-<名词>`，动词必须在规范词表中。现有词表（`extract/learn/forge/draw/manage/migrate/scout/build/sync/publish/archive/contribute/analyze/clean/release/validate/init/dispatch/close/setup/capture/clip/runby/dedup`）里没有能准确表达"联网找到并下载文件到本地"的动词，`fetch` 是最贴切的选择（且与仓库里已有的 `WebFetch` 工具命名呼应）。规范允许"确有必要时可扩展，须同步更新此表"——两处词表（`skill-spec.md` 是权威源，`publish-skill/SKILL.md` 内嵌一份供其自身校验用）都要加，否则 `publish-skill` 后续校验会因词表不含 `fetch` 而拒绝 `fetch-paper`。

**文件：**
- 修改: `docs/reference/skill-spec.md`
- 修改: `skills/mint/publish-skill/SKILL.md`

- [ ] **Step 1: 在 `skill-spec.md` 的动词词表加入 `fetch`**

在 `docs/reference/skill-spec.md` 的动词词表（Markdown 表格，`| 动词 | 含义 |` 下方）里，在 `| `extract` | ... |` 这一行之前插入新行：

```markdown
| `fetch` | 联网检索并获取资源到本地 |
```

- [ ] **Step 2: 在 `publish-skill/SKILL.md` 的内嵌词表加入 `fetch`**

在 `skills/mint/publish-skill/SKILL.md` 的 F7 检测方法代码块里（当前内容为）：

```
extract  learn    forge    draw     manage   migrate  scout
build    sync     publish  archive  contribute  analyze  clean
release  validate init     dispatch close    setup    capture
runby    probe    dedup    fix      survey
```

改为（末尾追加 `fetch`）：

```
extract  learn    forge    draw     manage   migrate  scout
build    sync     publish  archive  contribute  analyze  clean
release  validate init     dispatch close    setup    capture
runby    probe    dedup    fix      survey   fetch
```

- [ ] **Step 3: 验证两处都已包含 `fetch`**

运行:
```bash
grep -n "fetch" /Users/harveyzhang96/Projects/harveyz-skill/docs/reference/skill-spec.md
grep -n "fetch" /Users/harveyzhang96/Projects/harveyz-skill/skills/mint/publish-skill/SKILL.md
```
预期: 两条命令都至少各输出一行匹配。

- [ ] **Step 4: 提交**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git checkout -b feature/fetch-paper
git add docs/reference/skill-spec.md skills/mint/publish-skill/SKILL.md
git commit -m "docs(skill-spec): 动词词表加入 fetch，为 fetch-paper 铺路"
```

---

### Task 2: 编写 `fetch-paper` SKILL.md

**文件：**
- 创建: `skills/research/fetch-paper/SKILL.md`

- [ ] **Step 1: 创建目录并用 Write 工具写入完整 SKILL.md**

```bash
mkdir -p /Users/harveyzhang96/Projects/harveyz-skill/skills/research/fetch-paper
```

写入 `skills/research/fetch-paper/SKILL.md`，完整内容如下（不得删减任何 Step，不得用"参考设计文档"代替具体指令）：

```markdown
---
name: fetch-paper
description: "Locate and download a single academic paper's full text via legitimate open-access channels (arXiv, Unpaywall, Semantic Scholar, PMC, publisher OA pages). Verifies the paper's bibliographic record (DOI/arXiv ID) before searching, disambiguates when multiple candidates match, and reports one of four outcomes: auto-downloaded, free-but-manual, paid/registration-required, or not found. Maintains a growing list of free sources ranked by success rate. Triggers: 'find and download this paper', 'get me the PDF of <title>', 'download this paper', '下载这篇论文', '帮我找这篇论文全文', 'fetch paper <title/DOI>'."
user_invocable: true
version: "0.1.0"
---

# fetch-paper

联网核实论文真实存在，仅通过合法开放获取渠道下载全文 PDF；找不到免费全文时，报告手动/付费入口而非代为绕过付费墙。

底层设计说明见 `docs/superpowers/specs/2026-08-15-fetch-paper-design.md`。

---

## 路径变量

```
ConfigPath: ~/.hskill/fetch-paper/config.json
SourcesPath: ~/.hskill/fetch-paper/sources.json
```

---

## 执行流程

### Step 0：初始化配置与清单

用 Read 工具读取 `~/.hskill/fetch-paper/config.json`。

若文件不存在，询问用户：

```
论文下载到哪个目录？（直接回车使用默认：~/Documents/paper-downloads）
```

用户回复后，用 Bash 工具写入配置（路径必须用 `$HOME` 展开，不可写字面量 `~`）：

```bash
mkdir -p "$HOME/.hskill/fetch-paper"
download_dir="${用户指定路径/#\~/$HOME}"
echo "{\"download_dir\": \"$download_dir\"}" > "$HOME/.hskill/fetch-paper/config.json"
```

若文件已存在，解析 JSON 取出 `download_dir` 字段，展开残留的 `~`：

```bash
download_dir=$(python3 -c "import json,os; d=json.load(open('$HOME/.hskill/fetch-paper/config.json')); print(d['download_dir'].replace('~', os.environ['HOME'], 1))")
```

用 Read 工具读取 `~/.hskill/fetch-paper/sources.json`。若不存在，用 Bash 工具写入种子清单：

```bash
cat > "$HOME/.hskill/fetch-paper/sources.json" <<'EOF'
{
  "sources": [
    { "name": "arXiv", "type": "api", "auto": true, "success_count": 0 },
    { "name": "Unpaywall", "type": "api", "auto": true, "success_count": 0 },
    { "name": "Semantic Scholar", "type": "api", "auto": true, "success_count": 0 },
    { "name": "PMC", "type": "api", "auto": true, "success_count": 0 }
  ]
}
EOF
```

---

### Step 1：解析输入

从用户消息中提取论文线索：标题 / DOI / arXiv ID / 完整引用字符串。

判断输入是否已含：
- DOI（形如 `10.xxxx/...`）
- arXiv ID（形如 `2401.12345` 或 `hep-th/9901001`）

若已含，跳过检索的模糊匹配部分，直接用于 Step 2 的精确查询。

---

### Step 2：检索候选

**若输入已含 DOI：**

```
WebFetch(url="https://api.crossref.org/works/<DOI>")
```

**若输入已含 arXiv ID：**

```
WebFetch(url="http://export.arxiv.org/api/query?id_list=<arXiv ID>")
```

**否则（只有标题/引用字符串）：**

同时执行：

```
WebSearch("<标题>")
WebFetch(url="https://api.crossref.org/works?query.bibliographic=<urlencode(标题)>&rows=5")
```

从返回结果中，对每个候选提取：标题、作者、年份、期刊/会议、DOI、arXiv ID（若有）。

---

### Step 3：核验与消歧

- **唯一命中**（用 DOI/arXiv ID 精确查询命中，或标题/作者/年份高度吻合且只有一个候选）→ 直接确认，进入 Step 4。
- **多个相似候选** → 停下来，向用户列出候选表格，等待用户确认后再继续：

```
找到多个相似标题的论文，请确认目标：

1. {标题A} — {作者} ({年份})，DOI: {doi或"无"}
2. {标题B} — {作者} ({年份})，DOI: {doi或"无"}

请回复序号，或提供更精确的信息（如 DOI）。
```

- **零命中** → 归为「D」，跳到 Step 5 的 D 分支，不再继续后续步骤。

---

### Step 4：按优先级尝试免费渠道

读取 `~/.hskill/fetch-paper/sources.json`，把 `auto: true` 的站点按 `success_count` 降序排序，依次尝试（命中一个立即停止，不再尝试后面的）：

1. **arXiv** — 若已确认 arXiv ID，PDF 直链为 `https://arxiv.org/pdf/<arXiv ID>`
2. **Unpaywall** — 若已确认 DOI，`WebFetch(url="https://api.unpaywall.org/v2/<DOI>?email=fetch-paper@localhost")`，取响应中 `best_oa_location.url_for_pdf`
3. **Semantic Scholar** — `WebFetch(url="https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=openAccessPdf")`，取 `openAccessPdf.url`
4. **PMC** — 若论文属生物医学领域，`WebFetch(url="https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<DOI>&format=json")` 换取 PMC ID，PDF 直链为 `https://www.ncbi.nlm.nih.gov/pmc/articles/<PMC ID>/pdf/`
5. **期刊官网 OA 页面** — 若 Crossref 元数据里 `license` 字段显示开放许可（如 CC-BY），尝试该页面上的 PDF 链接
6. **作者/机构仓库自存版** — `WebSearch("\"<标题>\" filetype:pdf")`，人工判断结果是否为作者自存版（个人主页、机构仓库域名，而非镜像站）

对每个候选 URL：
- 用 WebFetch 请求
- **校验返回内容确为 PDF**：检查响应 `Content-Type` 是否为 `application/pdf`，或内容开头是否为 `%PDF-`。若是登录页/验证码页/HTML 错误页伪装的 200 响应，判定该渠道失败——记入「B 手动候选」列表，继续尝试下一个渠道，不重试同一渠道
- 若该渠道明确需要人工点击/验证码/交互式操作才能拿到文件本身（例如落地页只有"Request full text"按钮）→ 直接记入「B 手动候选」列表，不算失败也不算成功，继续尝试下一个渠道

若全部 auto 渠道都试完仍未拿到文件：
- 若「B 手动候选」列表非空 → 进入 Step 5 的 B 分支
- 若「B 手动候选」列表为空，但通过 Step 2/Step 3 已知官方页面（期刊官网、ResearchGate 请求作者、机构登录等）→ 进入 Step 5 的 C 分支
- 若连官方页面都没有 → 进入 Step 5 的 D 分支

---

### Step 5：产出结果

先用 Bash 生成 paper slug（标题转小写、空格与特殊字符替换为 `-`、汉字保留）：

```bash
slug=$(echo "<论文标题>" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9一-鿿]/-/g' | sed -E 's/-+/-/g' | sed 's/^-//;s/-$//')
```

**A. 自动下载成功**（Step 4 拿到了合法 PDF）：

```bash
mkdir -p "<download_dir>/$slug"
```

将下载到的 PDF 内容用 Write 工具写入 `<download_dir>/$slug/paper.pdf`。

用 Write 工具写入 `<download_dir>/$slug/metadata.md`：

```markdown
# {论文标题}

**作者**: {作者}
**年份**: {年份}
**期刊/会议**: {期刊}
**DOI**: {DOI或"无"}
**arXiv ID**: {arXiv ID或"无"}
**核验日期**: {YYYY-MM-DD}
**结果**: A 自动下载成功

## 获取渠道

- [自动] {站点名}：{URL}
```

用 Bash 更新 `~/.hskill/fetch-paper/sources.json`，命中站点的 `success_count` 加 1（用 python3 读写 JSON，保留其余字段不变）。

**B. 免费全文存在，但需手动下载**（有手动候选，但没有 auto 渠道成功）：

不写 PDF。用 Write 工具写入 `<download_dir>/$slug/metadata.md`（同上结构），获取渠道行改为：

```markdown
- [手动下载] {站点名}：{URL} —— {具体操作，如"打开链接，点击 Download PDF 按钮"}
```

**C. 无免费全文，但有收费/需注册渠道**：

用 Write 工具写入 `<download_dir>/$slug/metadata.md`，获取渠道行改为：

```markdown
- [付费/需注册] {站点名}：{URL} —— {购买 / 向作者请求全文 / 机构登录}
```

**D. 完全找不到任何获取渠道**：不创建目录、不写任何文件。直接在对话中回复：

```
未找到「{用户输入}」对应的可靠论文记录（或该论文没有任何已知获取渠道）。
{若 Step 2/3 已核验到部分元数据，在此列出}
```

---

### Step 6：汇报结果

无论哪一态，最后都用明确标签总结，不能含糊表述"已尝试下载"：

```
结果：[A 自动下载成功 / B 免费需手动 / C 付费或需注册 / D 完全找不到]

{论文标题}
{对应 metadata.md 完整路径，若有产出}
```

---

## 边界

- **不做**：不集成、不自动访问任何绕过付费墙的镜像站/影子图书馆（如 Sci-Hub 一类）
- **不做**：不代下载付费论文，不代填注册表单
- **不做**：不批量处理多篇论文（每次只处理一个）
- **不做**：下载后不自动调用 `learn-paper` 精读（用户需另行触发）
- **不做**：不深度校验全文内容与标题/摘要的一致性（核验只到"元数据记录真实存在"这一层）

---

## 依赖

- WebSearch（检索候选）
- WebFetch（调用 Crossref / Unpaywall / Semantic Scholar / arXiv / PMC 等公开 API，下载 PDF）
```

- [ ] **Step 2: 验证 frontmatter 格式（F1–F5）**

运行:
```bash
awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' /Users/harveyzhang96/Projects/harveyz-skill/skills/research/fetch-paper/SKILL.md
```
预期: 输出 4 行，分别为 `name: fetch-paper`、`description: "..."`（英文，长度 ≥ 10）、`user_invocable: true`、`version: "0.1.0"`。

- [ ] **Step 3: 验证目录命名（F7）**

确认目录名 `fetch-paper` 恰好 2 段、动词 `fetch` 已在 Task 1 加入词表、名词 `paper` 非工具/平台专名。手动核对即可，无需命令。

- [ ] **Step 4: 提交**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add skills/research/fetch-paper/SKILL.md
git commit -m "feat(skill): 新增 fetch-paper skill"
```

---

### Task 3: 注册到 `skills-index.json`

**文件：**
- 修改: `skills-index.json`

- [ ] **Step 1: 在 `skills[]` 数组中新增条目**

在 `skills-index.json` 的 `skills` 数组里，紧跟在 `research/learn-paper` 条目之后插入：

```json
{ "path": "research/fetch-paper", "bundle": "research", "installScope": "project" }
```

（`installScope: project` 与同批新增的 `learn-paper`/`probe-session`/`clip-url` 保持一致，不写 `contentHash`/`contentVersion`——首次注册时由 `publish-skill` 或下次发布流程补齐。）

- [ ] **Step 2: 更新 `bundleMeta.research` 描述**

把:
```json
"research": "研究工具（extract-url + learn-video + extract-vision + survey-skillrepo + learn-paper + extract-cognition + probe-session + clip-url）"
```
改为:
```json
"research": "研究工具（extract-url + learn-video + extract-vision + survey-skillrepo + learn-paper + extract-cognition + probe-session + clip-url + fetch-paper）"
```

- [ ] **Step 3: 重新生成 npmignore**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
node scripts/generate-npmignore.js
```
预期: 命令无报错退出。若 `.npmignore` 有变化，一并加入下一步的 commit。

- [ ] **Step 4: 验证注册**

```bash
node -e "
const idx = JSON.parse(require('fs').readFileSync('/Users/harveyzhang96/Projects/harveyz-skill/skills-index.json','utf8'));
const found = idx.skills.find(s => s.path === 'research/fetch-paper');
if (!found) { console.error('FAIL: not registered'); process.exit(1); }
if (!idx.bundleMeta[found.bundle]) { console.error('FAIL: bundle not declared'); process.exit(1); }
console.log('OK:', JSON.stringify(found));
"
```
预期: 输出 `OK: {"path":"research/fetch-paper","bundle":"research","installScope":"project"}`。

- [ ] **Step 5: 提交**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add skills-index.json .npmignore
git commit -m "chore(index): 注册 fetch-paper 到 skills-index.json"
```

---

### Task 4: 跑仓库测试套件

**文件：** 无新增/修改，仅验证。

- [ ] **Step 1: 运行 `npm test`**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
npm test
```
预期: 全部测试通过（含 hskill CLI 行为测试 + 所有 skill 的 SKILL.md 格式校验）。若失败，定位是 `fetch-paper` 的 SKILL.md 格式问题还是 `skills-index.json` 注册问题，回到 Task 2/Task 3 修正。

- [ ] **Step 2:（若因修正产生改动）提交**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill
git add -A
git commit -m "fix(fetch-paper): 修正测试暴露的格式问题"
```

（若 Step 1 一次通过、无需修正，跳过本步。）

---

### Task 5: 手动 dry-run 验证

**背景：** `fetch-paper` 是纯 Prompt 型 skill，真正的行为正确性无法用脚本断言，必须手动跑一次真实场景，确认四态分类、渠道优先级、`sources.json` 累加、`metadata.md` 内容都符合设计。

- [ ] **Step 1: 用已知开放获取论文触发一次（预期结果 A）**

在新对话中运行（示例用一篇确定在 arXiv 上的论文）：
```
/fetch-paper Attention Is All You Need
```
预期:
- 走到 Step 3 唯一命中（该标题在 Crossref/arXiv 上应无歧义）
- Step 4 命中 arXiv 渠道，PDF 校验通过
- 产出 `<download_dir>/attention-is-all-you-need/paper.pdf` 和 `metadata.md`
- 对话结尾明确标注「结果：A 自动下载成功」
- `~/.hskill/fetch-paper/sources.json` 中 `arXiv` 的 `success_count` 从 0 变为 1

- [ ] **Step 2: 用一个只有付费渠道的论文触发一次（预期结果 C 或 D）**

选一篇非开放获取、大概率无 OA 版本的期刊论文标题触发 `/fetch-paper`，确认：
- 没有产出 `paper.pdf`
- `metadata.md`（若有）中的获取渠道明确标为 `[付费/需注册]`，不是伪装成功
- 对话结尾标签为 C 或 D，且文字里没有出现任何绕过付费墙的建议

- [ ] **Step 3: 用一个模糊标题触发歧义分支**

用一个能匹配多篇论文的模糊短标题触发，确认 Step 3 真的停下来列出候选表格等用户选择，而不是自己挑一个继续跑。

若 Step 1–3 任一环节行为与设计不符，记录具体偏差，回到 Task 2 修正 SKILL.md 对应 Step 后重新提交（复用 Task 2 Step 4 的 commit 流程，message 换成 `fix(fetch-paper): ...`）。
