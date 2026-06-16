---
name: extract-vision
description: "Use when extracting specific information from images (screenshots, photos, receipts, menus) via PaddleOCR + subagent filtering."
version: 1.0.0
user_invocable: true
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [OCR, image, text-extraction, screenshots, vision, subagent]
    related_skills: [ocr-and-documents]
---

# Image Text Extraction: PaddleOCR + Subagent Filtering

## When to Use

- User shares a screenshot, photo, or image and wants to extract **specific information** (not just "all text")
- User provides natural language requirements (e.g., "提取金额和日期", "找出总价", "列出所有菜单项及价格")
- Works for any image format: PNG, JPG, WEBP, BMP, TIFF, PDF pages, etc.

## How It Works

Two-step pipeline:

1. **Step 1 — PaddleOCR**: Extract ALL text from the image (raw, unfiltered)
2. **Step 2 — Subagent**: Filter the OCR text based on the user's exact requirements and return only what they asked for

## Step 1 — Run PaddleOCR

**IMPORTANT**: This skill uses PaddleOCR v3.x. The API differs significantly from v2.x. Do NOT use `show_log`, `use_angle_cls`, or `cls` parameters — they are invalid or deprecated.

```python
from paddleocr import PaddleOCR

def ocr_full_text(image_path, lang='en'):
    """Extract all text from an image using PaddleOCR v3.x."""
    ocr = PaddleOCR(lang=lang)  # v3: no show_log, no use_angle_cls
    result = ocr.ocr(image_path)
    if not result:
        return ''
    page = result[0]
    rec_texts = page.get('rec_texts', [])
    dt_polys = page.get('dt_polys', [])
    rec_scores = page.get('rec_scores', [])
    lines = []
    for poly, text, score in zip(dt_polys, rec_texts, rec_scores):
        lines.append(f'{text} | conf={score:.2f}')
    return '\n'.join(lines)

text = ocr_full_text('/path/to/image.png')
```

> **API differences from v2**: v3 returns `{'rec_texts': [...], 'dt_polys': [...], 'rec_scores': [...]}` per page instead of `[(bbox, (text, score)), ...]`. Do not use `result[0][0][1][0]` — it will raise `KeyError`.

### Language options

| lang | Language |
|------|----------|
| `en` | English |
| `ch` | Chinese only |
| `ch+en` | Chinese + English mixed |
| `fr` | French |
| `de` | German |
| `ja` | Japanese |
| `ko` | Korean |

### Large images

Downscale if >4000px to improve speed and accuracy:

```python
from PIL import Image
img = Image.open('large.png')
img = img.resize((2000, int(2000 * img.height / img.width)))
img.save('resized.png')
```

## Step 2 — Subagent Filtering

After getting the full OCR text, spawn a subagent to extract **only what the user wants**:

```python
delegate_task(
    goal=f"""Here is the raw OCR text extracted from an image:

--- OCR RESULT START ---
{ocr_text}
--- OCR RESULT END ---

User wants: <natural language requirement>
Extract from the OCR result above only the information the user requested.
If the user asks for specific fields (e.g. "日期" or "total amount"), return those fields as a JSON object.
If the user asks to list items, return a structured list.
Return ONLY the filtered result, do not summarize the image or describe what it is.""",
    toolsets=["terminal"]
)
```

**Important**: The subagent uses `toolsets=["terminal"]` — it only sees the OCR text, not the image.

## Full Example: Receipt Data Extraction

```python
from paddleocr import PaddleOCR

# Step 1: OCR
ocr = PaddleOCR(lang='en')
result = ocr.ocr('/path/to/receipt.png')
page = result[0]
rec_texts = page.get('rec_texts', [])
dt_polys = page.get('dt_polys', [])
rec_scores = page.get('rec_scores', [])
ocr_text = '\n'.join(
    f'{text} | conf={score:.2f}'
    for text, score in zip(rec_texts, rec_scores)
)

# Step 2: Subagent filters
delegate_task(
    goal=f"""OCR text from a receipt:
--- START ---
{ocr_text}
--- END ---

Extract:
- vendor_name: the store or company name
- date: the transaction date
- total_amount: the total amount paid (just the number)
- items: list of items purchased as {{"item": "...", "price": "..."}}

Return as JSON.""",
    toolsets=["terminal"]
)
```

## Common Pitfalls

1. **Wrong API (PaddleOCR v3)** — `use_angle_cls`, `show_log`, `cls=True`, and tuple-unpacking `line[1][0]` are all wrong for v3. Use `PaddleOCR(lang=lang)` with no extra params, then access `result[0].get('rec_texts', [])`.
2. **First-run slow** — PaddleOCR downloads inference models (~300MB) on first OCR call. Models are cached in `~/.paddlex/`.
3. **Low confidence on small text** — Text below ~10px in the image will have poor accuracy. For menu bar icons / very small UI elements, use the vision subagent instead.
4. **Subagent receives empty text** — If PaddleOCR returns empty, fall back to a vision subagent directly on the image.
5. **Chinese + English** — Use `lang='ch+en'` for mixed content.

## Verification Checklist

- [ ] `python3 -c "from paddleocr import PaddleOCR; print('OK')"` runs without import error
- [ ] OCR returns non-empty `rec_texts` list for a test image
- [ ] Subagent goal contains the full OCR text (not just a path or summary)
- [ ] Subagent returns only filtered results per the user's requirement

---

