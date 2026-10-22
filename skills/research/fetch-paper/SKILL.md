---
name: fetch-paper
description: "Locate and download a single academic paper's full text via legitimate open-access channels (arXiv, Unpaywall, Semantic Scholar, PMC, publisher OA pages). Verifies the paper's bibliographic record (DOI/arXiv ID) before searching, disambiguates when multiple candidates match, and reports one of four outcomes: auto-downloaded, free-but-manual, paid/registration-required, or not found. Maintains a growing list of free sources ranked by success rate. Triggers: 'find and download this paper', 'get me the PDF of <title>', 'download this paper', 'fetch paper <title/DOI>'."
user_invocable: true
version: "0.2.3"
---

# fetch-paper

联网核实论文真实存在，仅通过合法开放获取渠道下载全文 PDF；找不到免费全文时，报告手动/付费入口而非代为绕过付费墙。

---

## 路径变量

```
ConfigPath: ~/.hskill/fetch-paper/config.json
SourcesPath: ~/.hskill/fetch-paper/sources.json
```

**宿主能力：** 下文的读取、文本写入、结构化请求（调用 Crossref / Unpaywall / Semantic Scholar / arXiv / PMC 等公开 API）、检索、下载（下载 PDF 并返回或创建临时文件），都指宿主提供的对应能力；shell 片段只是示例写法。写进配置的路径一律用 `$HOME` 展开，不写字面量 `~`。

---

## 执行流程

### Step 0：初始化配置与清单

读取 `~/.hskill/fetch-paper/config.json`。

若文件不存在，询问用户：

```
论文下载到哪个目录？（直接回车使用默认：~/Documents/paper-downloads）
```

用户回复后写入配置：

```bash
mkdir -p "$HOME/.hskill/fetch-paper"
download_dir="${用户指定路径/#\~/$HOME}"
echo "{\"download_dir\": \"$download_dir\"}" > "$HOME/.hskill/fetch-paper/config.json"
```

若文件已存在，解析 JSON 取出 `download_dir` 字段，展开残留的 `~`：

```bash
download_dir=$(python3 -c "import json,os; d=json.load(open('$HOME/.hskill/fetch-paper/config.json')); print(d['download_dir'].replace('~', os.environ['HOME'], 1))")
```

读取 `~/.hskill/fetch-paper/sources.json`。若不存在，创建种子清单：

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

请求：

```
https://api.crossref.org/works/<DOI>
```

**若输入已含 arXiv ID：**

请求：

```
http://export.arxiv.org/api/query?id_list=<arXiv ID>
```

**否则（只有标题/引用字符串）：**

同时检索 `<标题>`，并请求：

```
https://api.crossref.org/works?query.bibliographic=<urlencode(标题)>&rows=5
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

读取 `~/.hskill/fetch-paper/sources.json`，先把 `auto: true` 的站点按 `success_count` 降序依次尝试（下列 1–4 是各站点的请求方法，编号不代表顺序）；都未命中，再依次尝试 5、6。命中一个即停：

1. **arXiv** — 若已确认 arXiv ID，PDF 直链为 `https://arxiv.org/pdf/<arXiv ID>`
2. **Unpaywall** — 若已确认 DOI，请求 `https://api.unpaywall.org/v2/<DOI>?email=fetch-paper@localhost`，取响应中 `best_oa_location.url_for_pdf`
3. **Semantic Scholar** — 请求 `https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=openAccessPdf`，取 `openAccessPdf.url`
4. **PMC** — 仅限生物医学论文。请求 `https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<DOI>&format=json` 换取 PMC ID（301 跳转后再请求一次，ID 在 `records[0].pmcid`）。PMC 的 PDF 直链要浏览器完成 JS 挑战，普通请求一定失败：直接把落地页记入「B 手动候选」，不尝试下载
5. **期刊官网 OA 页面** — Crossref 的 `license` 显示开放许可（如 CC-BY）时，尝试页面上的 PDF 链接。主流出版商普遍拦截自动化请求，遇到 403 或非 PDF 响应即判失败，记入「B 手动候选」，不重试同一出版商
6. **作者/机构仓库自存版** — 检索 `"<标题>" filetype:pdf`，人工判断结果是否为作者自存版（个人主页、机构仓库域名，而非镜像站）

对每个候选 URL：
- 使用宿主的**下载能力**请求二进制内容。下载能力必须返回或创建一个**临时文件**，并报告其路径；**记下这个临时文件路径**，Step 5 A 写盘时要用它。若宿主的下载能力不能保存二进制内容，才可用 `curl -L --fail --output <临时文件路径> <URL>` 创建临时文件，再继续校验；不得把 PDF 二进制字节交给仅接受文本的写入能力。
- **校验返回内容确为 PDF**：检查响应 `Content-Type` 是否为 `application/pdf`，或内容开头是否为 `%PDF-`。若是登录页/验证码页/HTML 错误页伪装的 200 响应，判定该渠道失败——记入「B 手动候选」列表，继续尝试下一个渠道，不重试同一渠道
- 若该渠道明确需要人工点击/验证码/交互式操作才能拿到文件本身（例如落地页只有"Request full text"按钮）→ 直接记入「B 手动候选」列表，不算失败也不算成功，继续尝试下一个渠道

若全部 auto 渠道都试完仍未拿到文件：
- 若「B 手动候选」列表非空 → 进入 Step 5 的 B 分支
- 若「B 手动候选」列表为空，但通过 Step 2/Step 3 已知官方页面（期刊官网、ResearchGate 请求作者、机构登录等）→ 进入 Step 5 的 C 分支
- 若连官方页面都没有 → 进入 Step 5 的 D 分支

---

### Step 5：产出结果

生成 paper slug（标题转小写、空格与特殊字符替换为 `-`、汉字保留）：

```bash
slug=$(echo "<论文标题>" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9一-鿿]/-/g' | sed -E 's/-+/-/g' | sed 's/^-//;s/-$//')
```

**A. 自动下载成功**（Step 4 拿到了合法 PDF）：

创建目标目录：

```bash
mkdir -p "<download_dir>/$slug"
```

把 Step 4 中下载能力返回的临时文件路径复制到目标位置（PDF 是二进制内容，不能用仅支持文本的写入能力写入，二进制字节会被破坏）：

```bash
cp "<下载能力返回的临时文件路径>" "<download_dir>/$slug/paper.pdf"
```

写入 `<download_dir>/$slug/metadata.md`：

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

更新 `~/.hskill/fetch-paper/sources.json`：命中站点的 `success_count` 加 1（使用 JSON 解析与写入，保留其余字段不变）。

**B. 免费全文存在，但需手动下载**（有手动候选，但没有 auto 渠道成功）：

不写 PDF。写入 `<download_dir>/$slug/metadata.md`（同上结构），获取渠道行改为：

```markdown
- [手动下载] {站点名}：{URL} —— {具体操作，如"打开链接，点击 Download PDF 按钮"}
```

**C. 无免费全文，但有收费/需注册渠道**：

写入 `<download_dir>/$slug/metadata.md`，获取渠道行改为：

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

