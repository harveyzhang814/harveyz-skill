# fetch-paper Skill 设计文档

**日期**: 2026-08-15
**分类**: research
**路径**: `skills/research/fetch-paper/`

---

## 概述

`fetch-paper` 是一个供 Agent 定位并下载单篇学术论文全文的 skill。输入论文标题（或 DOI / arXiv ID / 完整引用），联网核实论文确实存在，然后**仅通过合法开放获取渠道**尝试拿到全文 PDF，下载到本地。过程中维护一份免费资源站点清单，成功的站点会被记录，供后续调用优先尝试。

与 `learn-paper`（精读已有本地 PDF）互补：`fetch-paper` 负责"找到并拿到手"，`learn-paper` 负责"读懂"。两者不合并、不互相调用，各自独立触发。

---

## 边界：仅合法开放获取渠道

**不做的事**：不集成、不自动访问任何绕过付费墙的镜像站/影子图书馆（如 Sci-Hub 一类）。这类站点在多数地区涉嫌版权问题，不写入内置种子清单，也不在流程中自动尝试。

**做的事**：只走公开、合法的开放获取（OA）渠道——arXiv、bioRxiv/medRxiv、PMC、期刊官网的开放获取页面、作者/机构自存版、以及通过 Unpaywall、Semantic Scholar 等聚合服务查到的合法 OA 链接。

找不到免费全文时，如实告知用户，不代为寻找灰色渠道。

---

## 输入

```
/fetch-paper <论文标题 | DOI | arXiv ID | 完整引用字符串>
```

接受自由文本，Agent 自行判断输入类型（是否已含 DOI/arXiv ID）。

---

## 核心流程

```
步骤 0：初始化配置
  → 读取 ~/.hskill/fetch-paper/config.json
  → 若不存在：询问下载目录（默认建议 ~/Documents/paper-downloads），写入配置
  → 读取 ~/.hskill/fetch-paper/sources.json
  → 若不存在：写入内置种子清单（见"资源站点清单"节）

步骤 1：检索候选
  → 用 WebSearch + Crossref API（api.crossref.org/works）/ Semantic Scholar API
    按标题或 DOI/arXiv ID 检索
  → 取回候选的 标题/作者/年份/期刊/DOI/arXiv ID

步骤 2：核验与消歧
  → 唯一命中 → 直接确认，进入步骤 3
  → 多个相似候选 → 列出候选（标题/作者/年份/DOI）请用户选择目标
  → 零命中 → 归为「D. 完全找不到」，报告并结束

步骤 3：按优先级尝试免费渠道
  → 按 sources.json 中「auto:true 站点」的成功次数降序排列，依次尝试：
    arXiv → Unpaywall（按 DOI）→ Semantic Scholar openAccessPdf
    → PMC → 期刊官网 OA 页面 → 作者/机构仓库自存版
  → 命中一个可直接抓取的 PDF 链接 → 用 WebFetch 下载，校验文件确为 PDF
    （非登录页/错误页伪装的 200 响应）→ 成功则跳到步骤 4a
  → 若某个 auto:true 渠道返回的其实是需要人工点击/验证码/交互式页面
    （无法程序化取得文件本身）→ 记为该来源「B. 手需手动」候选，继续试下一个
  → 全部 auto 渠道试完仍未拿到文件，但收集到了至少一个「手动可免费」入口
    → 步骤 4b
  → 一个可用的免费入口（自动或手动）都没有，但找到了官方付费页 /
    ResearchGate 请求作者全文 / 需机构登录等渠道 → 步骤 4c
  → 连付费/注册渠道都没查到 → 步骤 4d

步骤 4：产出结果（四态之一）
  4a. 自动下载成功
      → PDF 存到 <下载目录>/<slug>/paper.pdf
      → 写 <下载目录>/<slug>/metadata.md（标题/作者/DOI/来源URL/下载日期/命中渠道）
      → sources.json 对应站点 success_count += 1

  4b. 免费全文存在，但需手动下载
      → 不写 PDF，写 <下载目录>/<slug>/metadata.md，标注：
        「[手动下载] <站点名>：<URL> —— <需要做什么，如"打开链接点击 Download PDF"> 」

  4c. 无免费全文，但有收费/需注册渠道
      → 写 metadata.md，标注：
        「[付费/需注册] <站点名>：<URL> —— <购买 / 请求作者 / 机构登录>」

  4d. 完全找不到任何获取渠道
      → 不写文件，直接在对话中报告已核验到的论文元数据（若有）+ 说明未找到
        任何来源
```

对话结尾必须清楚打出该次结果属于 A/B/C/D 哪一态，不能含糊表述"已尝试下载"。

---

## 输出结构

```
{下载目录}/{paper-slug}/
├── paper.pdf       ← 仅 4a 情况下产出
└── metadata.md     ← 4a/4b/4c 情况下产出，4d 不落盘
```

`paper-slug` 生成规则复用 `learn-paper` 的方式：标题转小写、空格与特殊字符替换为 `-`、汉字保留。

### metadata.md 结构

```markdown
# {论文标题}

**作者**: ...
**年份**: ...
**期刊/会议**: ...
**DOI**: ...
**arXiv ID**: ...（若有）
**核验日期**: YYYY-MM-DD
**结果**: A 自动下载成功 / B 免费需手动 / C 付费或需注册

## 获取渠道

- [渠道类型] 站点名：URL —— 说明
```

---

## 配置

`~/.hskill/fetch-paper/config.json`：

```json
{
  "download_dir": "~/Documents/paper-downloads"
}
```

- 首次运行若无配置，询问用户目录并写入（同 `read-paper` 模式）

---

## 资源站点清单

`~/.hskill/fetch-paper/sources.json`，内置种子 + 运行期自动增量更新：

```json
{
  "sources": [
    { "name": "arXiv", "type": "api", "auto": true, "success_count": 0 },
    { "name": "Unpaywall", "type": "api", "auto": true, "success_count": 0 },
    { "name": "Semantic Scholar", "type": "api", "auto": true, "success_count": 0 },
    { "name": "PMC", "type": "api", "auto": true, "success_count": 0 }
  ]
}
```

- 每次成功下载后，对应站点 `success_count += 1`
- 步骤 3 尝试顺序按 `success_count` 降序，同分保持清单原始顺序
- 新发现的可用免费站点（无论 auto 与否）追加进清单，`success_count` 从 0 起
- 清单只增不删；同名站点重复命中直接累加计数，不新建条目

---

## 依赖关系

- WebSearch / WebFetch（检索候选、调用 Crossref / Unpaywall / Semantic Scholar 等公开 API、下载 PDF）
- 无需登录态、无需代理绕过类工具

---

## 错误处理

- Crossref/Unpaywall/Semantic Scholar 请求超时或限流 → 该渠道视为失败，跳到下一个渠道，不做重试等待
- 下载得到的文件不是合法 PDF（如登录页、验证码页伪装成 200） → 视为该渠道失败，归入「B 手动」候选或跳过
- 用户输入的标题检索不到任何候选 → 归入「D 完全找不到」，不虚构 DOI 或元数据

---

## 不在范围内

- 绕过付费墙的镜像/影子图书馆站点（见"边界"节）
- 批量下载多篇论文
- 下载后自动调用 `learn-paper` 精读（用户需另行触发）
- 论文全文内容与标题/摘要的深度一致性校验（核验只到"这篇论文的元数据记录真实存在"这一层）
