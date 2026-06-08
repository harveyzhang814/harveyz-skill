# PDFMathTranslate 架构分析笔记

> 基于源码分析，2026-04-26

---

## 一、项目概述

**PDFMathTranslate** 是一个保留布局的科技论文翻译工具，核心目标是：在翻译 PDF 文本内容的同时，保持公式、图表、表格、目录等元素的原始位置和格式。

- **GitHub**: https://github.com/PDFMathTranslate/PDFMathTranslate
- **PyPI 包名**: `pdf2zh`
- **发表**: EMNLP 2025 System Demonstrations

---

## 二、整体架构

```
输入 PDF
    │
    ▼
┌─────────────────────────────────────┐
│         1. 页面渲染 (PyMuPDF)         │
│    PDF 页面 → 渲染为图像 (RGB)        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│    2. 布局检测 (DocLayout-YOLO)      │
│    图像 → 2D 像素级类别图             │
│    类别: 文本/公式/表格/图表/标题等    │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      3. 字符解析 (pdfminer.six)      │
│    PDF 内容流 → LTChar 序列           │
│    每个字符: 文本+坐标+字体+字号        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│         4. 元素分类与分离             │
│    坐标对齐 + 字体规则 → 判定类型       │
│    分离为: 文本栈 + 公式栈 + 图片栈    │
└─────────────────┬───────────────────┘
                  │
        ┌────────┴────────┐
        ▼                 ▼
┌───────────────┐  ┌─────────────────┐
│   5a. 文本翻译  │  │ 5b. 公式/图片  │
│   LLM 翻译     │  │   原样保留      │
└───────┬───────┘  └─────────────────┘
        │
        ▼
┌─────────────────────────────────────┐
│         6. 排版重建 (PyMuPDF)        │
│    按原坐标绘制翻译后的文本             │
│    公式/图片 插入原位                  │
└─────────────────┬───────────────────┘
                  │
                  ▼
         输出: mono.pdf (译版)
               dual.pdf (双语)
```

---

## 三、核心模块详解

### 3.1 布局检测 — `doclayout.py`

**模型**: DocLayout-YOLO (ONNX)

**核心类**: `YoloDocLayout`

**输入**: 渲染后的 PDF 页面图像 (RGB, 1024×1024)

**输出**: `YoloResult`，包含一个 `layout_map`，shape 为 `(H, W)`，每个像素是一个类别 ID

**类别定义**:
```python
vcls = ["abandon", "figure", "table", "isolate_formula", "formula_caption"]
# 0=弃用区, 1=图表, 2=表格, 3=独立公式, 4=公式标题
```

**关键代码**:
```python
def predict(self, image, imgsz=1024, **kwargs):
    # 预处理: resize + 归一化
    # ONNX 推理
    # 后处理: 找到每个像素的类别 → layout_map
    return YoloResult(layout_map=class_map)
```

**为什么用像素级而不是边界框**:
- 科技论文排版密集，公式和文本相互嵌套，边界框会有大量重叠
- 像素级分割可以精确标注每个像素属于哪个类别
- 后续通过坐标映射，直接查表判定每个字符的类别

---

### 3.2 字符解析 — `pdfminer.six`

**库**: `pdfminer.six` (PDF 解析) + `PyMuPDF` (页面渲染)

**核心流程**:
```python
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTPage, LTChar, LTFigure

for page in extract_pages("paper.pdf"):
    for child in page:
        if isinstance(child, LTChar):
            # LTChar 包含:
            # - text: 字符文本
            # - x0, y0, x1, y1: 坐标
            # - fontname: 字体名 (用于判断公式)
            # - size: 字号
            # - matrix: 变换矩阵
```

**PDF 内容流示例**:
```
BT                           # Begin Text
/F2 12 Tf                    # 选择字体，字号
100 700 Td                   # 移动到坐标
(Hello) Tj                   # 绘制文字
ET                           # End Text
```

pdfminer 解析这些操作符和操作数，输出 LTChar 对象序列。

---

### 3.3 公式识别规则

仅靠 YOLO 的类别不够（类别只有粗粒度的 5 种），还需要额外规则：

```python
# 规则 1: YOLO 类别为 "isolate_formula"
cls == 3

# 规则 2: LaTeX 字体名检测
vflag = lambda fontname: any(p in fontname for p in [
    "CM*", "MS.M", "MT", "TeX*", "EU*",  # Computer Modern
    "TimesNewRomanPS", "Symbol", "ZapfDingbats"
])

# 规则 3: Unicode 数学符号范围
def is_math_char(ch):
    cat = unicodedata.category(ch)
    return cat in ("Sm", "Mn") or ("Ͱ" <= ch <= "Ͽ")  # Greek

# 规则 4: 垂直字体 (matrix[0]==0 and matrix[3]==0)
# 公式内的字符通常是垂直排列的
```

**最终判定**:
```python
is_formula = (
    cls == 3 or                           # YOLO 独立公式
    (cls == 0 and vflag(fontname)) or     # YOLO 文本区但字体是 LaTeX
    (cls == 0 and is_math_char(text))     # YOLO 文本区但字符是数学符号
)
```

---

### 3.4 元素分离

```python
# 遍历每个 LTChar
# 按 YOLO 类别 + 字体规则 分类

text_segments = []   # 文字片段
formula_segments = [] # 公式片段
image_regions = []   # 图表区域 (LTFigure)

# 公式占位符
# 原文: "The equation E=mc² is shown"
# 变成: "The equation {v0} is shown"
# 缓存: {v0}: "E=mc²"
```

---

### 3.5 翻译 — `translator.py`

**支持服务**:
| 服务 | 命令 | API Key |
|------|------|---------|
| Google (默认) | `-s google` | 无 |
| DeepL | `-s deepl` | DEEPL_AUTH_KEY |
| OpenAI | `-s openai` | OPENAI_API_KEY |
| Ollama (本地) | `-s ollama` | 无 (需本地部署) |
| DeepSeek | `-s deepseek` | DEEPSEEK_API_KEY |
| MiniMax | `-s minimax` | MINIMAX_API_KEY |
| Zhipu | `-s zhipu` | ZHIPU_API_KEY |
| 硅基流动 | `-s silicon` | SILICON_API_KEY |

**Ollama 本地模型**:
```bash
# 安装
ollama pull translategemma:12b   # 专用翻译模型，~12GB
ollama pull translategemma:4b     # 轻量版，~3.3GB
ollama pull qwen2.5:7b           # 通用模型，~4.7GB
```

---

### 3.6 排版重建 — `converter.py`

**核心思想**: 保持所有坐标、字体、字号不变，只替换文字内容。

```python
# 使用 PyMuPDF 重建
doc = fitz.open("original.pdf")
page = doc[0]

for char in translated_chars:
    # char.x, char.y 来自原文
    # char.translated_text 是翻译后的内容
    page.insert_text(
        (char.x, char.y),           # 原坐标
        char.translated_text,
        fontname=char.original_font, # 原字体
        fontsize=char.size          # 原字号
    )

doc.save("translated.pdf")
```

**公式回填**:
```python
# 占位符 {v0} → 原始公式内容
# 位置和字体完全不变
```

---

## 四、CJK 文字处理

**问题**: 翻译到中文时，原始 PDF 的西文字体无法正确渲染中文。

**方案**: 使用思源字体 (Source Han Serif) 替换：

```python
# 检测到目标语言为 CJK 时
# 使用 Noto Serif SC (思源宋体) 绘制中文
# 配合原始字体大小和位置
```

**字体缓存**: 下载到 `~/.cache/babeldoc/fonts/`

---

## 五、输出格式

| 文件 | 内容 |
|------|------|
| `*-mono.pdf` | 纯翻译版 |
| `*-dual.pdf` | 双语对照版（原文+译文并排） |

---

## 六、YOLO 与 pdfminer 的互补设计

```
YOLO (DocLayout-YOLO)          pdfminer.six
─────────────────────          ────────────
像素级区域分类                  精确字符内容提取
粗粒度 (5 类)                 字符级 (每个字符)
不知道具体文字                  读出具体文本
不知道字体/字号                 知道字体、字号、坐标

         坐标对齐后结合
              ↓
    每个字符 → 类别(来自YOLO) + 内容(来自pdfminer)
```

---

## 七、已知限制

| 限制 | 说明 |
|------|------|
| **扫描件 PDF** | 无文字层，只能靠 OCR（不支持） |
| **图片内文字** | YOLO 能检测"这里有图片"，但读不出图片里的文字 |
| **手写内容** | 同上 |
| **复杂表格** | 表格结构识别依赖 LTRect/LTLine，嵌套复杂的可能偏差 |
| **内嵌字体** | 部分 PDF 使用自定义字体，提取可能有问题 |
| **内存占用** | Ollama 12B 模型需要 ~12GB 内存，4B 需要 ~4GB |

---

## 八、可改进方向

1. **图片内文字 OCR**: 在 YOLO 检测到 figure 后，用 OCR 提取图片内文字 → 翻译 → 写回
2. **图片导出功能**: 将 figure 区域提取为独立图片文件（PNG/JPEG）
3. **扫描件支持**: 集成 PaddleOCR 等做前端 OCR
4. **更精确的表格处理**: 目前的表格线检测依赖简单规则，复杂表格效果有限
5. **多栏文档优化**: 处理跨栏公式和脚注时容易出错

---

## 九、文件结构

```
pdf2zh/
├── __init__.py
├── converter.py       # 核心转换逻辑
├── doclayout.py       # YOLO 布局检测
├── pdfinterp.py       # PDF 解释器
├── high_level.py      # 高层 API (pdf2zh 命令行入口)
├── translator.py      # 各翻译服务适配器
├── cache.py           # 翻译缓存
├── config.py          # 配置管理
└── constants.py       # 常量定义
```
